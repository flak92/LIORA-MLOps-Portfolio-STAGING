"""Optuna TPE per asset, sequential and seeded, over the frozen search space. The objective is the CAGR of
the chained validation path at the threshold the one selection rule would pick — the quantity the coordinate
search selects on, so the parameters are tuned on it. The final holdout is never touched here.

The stage is a function of X, Y and the frozen constants alone: it draws no point to start from, so the
parameters file it writes is a function of the raw store and this code, never of what it wrote last.

Inside a coordinate search the study is also a coordinate: one candidate per beam member, drawn on that
member's own X and Y, and pruned by one explicit gate. It cannot answer worse than the member it ran on,
because a candidate has to beat it — the guarantee is the gate's, not a point the study was handed.

That gate is the state gate's own condition, read one fold at a time: after each fold, the thresholds at
which **every** fold so far clears the trade floor and beats the champion's Calmar. The set only shrinks as
folds are added, and the child the search would keep needs one threshold inside it over all three, so a trial
whose set has gone empty cannot produce one and stops. Nothing admissible is discarded by it.

What stood here before was a bound — the best a fold could reach over the whole grid — on two measures, read
fold by fold and never jointly. Two bounds, each true of some threshold, say nothing about one threshold
admissible on every fold, and one threshold is what the state gate needs; this set is that quantity. Optuna's
own median pruner is not a gate here either: it
compares a trial's best value over all its steps with the median of other trials at one step, and with folds
as calendar years that comparison is not of like with like.

Every point the search drew is left in the asset's trial ledger, where the parameters file keeps only the
one it chose. The ledger is JSON Lines appended a line at a time — the technique the coordinate search's own
ledger uses, written by `dataset.append_jsonl` and by nothing else."""

from __future__ import annotations

import numpy as np
import optuna

from . import config, dataset, model, strategy, train, validation


def log_trials(ticker: str, study: optuna.Study, origin: str, round_number: int | None) -> None:
    """Every point a study drew, one line each, appended to the asset's ledger and never rewritten.

    A study's place in the ledger is read off the ledger: every study opens with its own trial 1, so the
    lines carrying that number are the studies before this one. One read per study and no state kept outside
    the file, which is why two fanned-out processes need nothing from each other — they write different
    assets' files.

    Nothing here is written differently by a second run: no run id, no timestamp, no host name. Two studies
    over an empty store therefore leave the same bytes, and the ledger stops being a note about the search
    and becomes a thing the search can be proved against. The ledger only grows; a hand clears it."""
    ledger = config.hyperparameter_search_trials_jsonl(ticker)
    search_index = 1 + sum(row["trial_index"] == 1 for row in dataset.load_jsonl(ledger)) if ledger.exists() else 1
    for trial in study.trials:
        dataset.append_jsonl(ledger, trial_row(trial, origin, round_number, search_index))


# the key the chosen point's value is published under, and the name one trial's value carries in the
# ledger — each named for what it measures
OBJECTIVE_KEY = "best_cagr_validation_path"
TRIAL_METRIC_KEY = "cagr_validation_path"


def admissible_thresholds(sweeps: dict[int, dict], champion_by_fold: dict[int, dict] | None,
                          fold_ids: tuple[int, ...]) -> list[float]:
    """The thresholds at which every fold evaluated so far clears the trade floor and — when there is a
    champion to beat — beats its Calmar there. One list, shrinking as folds are added.

    This is the state gate's own condition read one fold at a time. That gate keeps a child only where a
    **single** threshold makes every validation fold better than the parent, so its threshold must lie in
    this set over all three folds; a trial whose set has gone empty cannot produce one however the remaining
    folds land, because adding a fold can only remove thresholds. Nothing admissible is discarded.

    What it replaces was a bound, not a condition: the best a fold could reach on a measure over the whole
    grid, fold by fold and never jointly. Two bounds, each true of some threshold, say nothing about one
    threshold admissible on every fold — and one threshold is what the state gate needs. This set is that
    quantity, so the gate stops a trial exactly when the trial can no longer produce a child the search would
    keep, and stops it at the first fold that settles it rather than the first fold on which some bound
    happens to fail."""
    return [threshold for threshold in config.ENTRY_EDGE_THRESHOLD_GRID
            if all(sweeps[fold_id][threshold]["trade_count"] >= config.MINIMUM_TRADES_PER_VALIDATION_FOLD
                   and (champion_by_fold is None
                        or sweeps[fold_id][threshold]["calmar"] > champion_by_fold[fold_id]["calmar"])
                   for fold_id in fold_ids)]


def sweep_selection(sweeps: dict[int, dict]) -> tuple[float, float]:
    """The threshold the one selection rule would pick over these folds, and the chained path's growth rate
    there — the trial's own value. Ties keep the smaller threshold, as the rule takes them.

    The rule reads the trade floor and nothing else, never the champion: a trial's value is what it is worth,
    not what it is worth against something. A trial with no threshold clearing the floor in every fold never
    reaches here — the fold loop stops it — because the grid floor it would otherwise be scored at is a
    fallback for a *report*, a number to show when nothing qualified, and handing it to a sampler let a trial
    that never qualified compete, and win, on the numbers of a threshold nothing qualified for."""
    cleared = admissible_thresholds(sweeps, None, config.VALIDATION_FOLD_IDS)
    value, negated = max((strategy.validation_path_cagr(
        {fold_id: sweeps[fold_id][threshold]["final_equity"] for fold_id in config.VALIDATION_FOLD_IDS}),
        -threshold) for threshold in cleared)
    return -negated, value


def build_objective(xy: dict[str, np.ndarray], bars_1m: dict[str, np.ndarray],
                    champion_by_fold: dict[int, dict] | None = None):
    """The objective one trial is scored by, and the gates that stop it early when it cannot win.

    One sweep of the threshold grid per fold, kept for the trial's life: the two gates read the best that
    fold could still reach off it, and the trial's own value is read off the same three sweeps. Nothing is
    replayed, because nothing has to be — a sweep is a deterministic function of the fold's predictions."""
    y_cls = model.to_class(xy["y"])

    def objective(trial: optuna.Trial) -> float:
        params = model.suggest_params(trial)
        prediction_records, sweeps = [], {}
        floor_count_by_fold, admissible_count_by_fold = [], []
        for fold_id in config.VALIDATION_FOLD_IDS:
            _, _, rows, _ = train.fold_evaluation(xy, y_cls, params, fold_id)
            prediction_records.extend(rows)
            simulation_inputs = strategy.build_simulation_inputs(
                xy, bars_1m, train.to_oos_predictions(prediction_records))
            sweeps[fold_id] = strategy.results_by_threshold(
                simulation_inputs, strategy.signals_for_fold(simulation_inputs, fold_id),
                *validation.fold_bounds(fold_id))
            evaluated = config.VALIDATION_FOLD_IDS[:len(sweeps)]
            # two counts, two questions. The floor is the trial's own admissibility — a strategy at all —
            # and is asked in both modes. Admissibility against a champion is the state gate's question and
            # exists only where there is a champion; one key holding both would answer a different question
            # depending on who ran the study, which is the kind of key a register cannot define
            floor = admissible_thresholds(sweeps, None, evaluated)
            floor_count_by_fold.append(len(floor))
            trial.set_user_attr("floor_clearing_threshold_count_by_fold", list(floor_count_by_fold))
            admissible = None
            if champion_by_fold is not None:
                admissible = admissible_thresholds(sweeps, champion_by_fold, evaluated)
                admissible_count_by_fold.append(len(admissible))
                trial.set_user_attr("admissible_threshold_count_by_fold", list(admissible_count_by_fold))
            if not floor or (admissible is not None and not admissible):
                raise optuna.TrialPruned()
        threshold, value = sweep_selection(sweeps)
        # whether the threshold the rule chose for this trial is one at which every fold beats the champion —
        # the state gate's own question about this trial's own tau, answered where the sweeps already are so
        # the loop need not refit to ask it. Not "the set is non-empty": a non-empty set the chosen threshold
        # does not belong to is a child the state gate still refuses
        trial.set_user_attr("admissible", None if admissible is None else threshold in admissible)
        return value

    return objective


def trial_row(trial: optuna.trial.FrozenTrial, origin: str, round_number: int | None,
              search_index: int) -> dict:
    """One trial as one line: where it was drawn and in which round, its place in the study and the study's
    in the ledger, the point the sampler drew, and what the trial left.

    Every key stands on every line, `null` where it does not apply, so the file reads as one table and not
    as two, and a reader counting lines does not have to know which is which first.

    The state is read from `trial.state` and never inferred from `trial.value`. Optuna records the last
    reported intermediate value as a pruned trial's value, so a trial stopped by a gate after reporting one
    carried a value like a completed trial's — and a ledger that asked `value is None` called every pruned
    trial complete. That is how a gate pruning three quarters of its points was measured as pruning none."""
    pruned = trial.state == optuna.trial.TrialState.PRUNED
    floor_counts = trial.user_attrs["floor_clearing_threshold_count_by_fold"]
    admissible_counts = trial.user_attrs.get("admissible_threshold_count_by_fold")
    admissible = trial.user_attrs["admissible"] if not pruned else None
    return {"origin": origin, "round": round_number, "search_index": search_index,
            "trial_index": trial.number + 1, "state": "pruned" if pruned else "complete",
            "params": trial.params,
            "floor_clearing_threshold_count_by_fold": floor_counts,
            "admissible_threshold_count_by_fold": admissible_counts,
            "admissible": None if admissible is None else bool(admissible),
            "pruned_at_fold": config.VALIDATION_FOLD_IDS[len(floor_counts) - 1] if pruned else None,
            TRIAL_METRIC_KEY: None if pruned else trial.value}


def search_hyperparameters(xy: dict, bars_1m: dict[str, np.ndarray],
                           champion_by_fold: dict[int, dict] | None = None) -> optuna.Study:
    """The asset's TPE search over the frozen space, sequential and seeded — the study itself, so a caller
    reads the point it chose, that point's value and every point it drew from one object.

    No point is drawn first. The loop used to hand the champion's own parameters to the study as its first trial, so it could never
    answer worse than where it began, and that trial is now stopped by the gate after its first fold —
    equality does not beat a strict inequality — so it was a fit spent on a point that could not be a
    candidate, and a pruned trial without an intermediate value tells the sampler nothing. The guarantee it
    carried lives in the gate instead: a candidate must beat the champion, so a study that finds nothing
    better offers nothing."""
    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=config.SEED,
                                           n_startup_trials=config.HYPERPARAMETER_SEARCH_STARTUP_TRIAL_COUNT),
    )
    study.optimize(build_objective(xy, bars_1m, champion_by_fold),
                   n_trials=config.HYPERPARAMETER_SEARCH_TRIAL_COUNT, n_jobs=1)
    return study


def moves(state: dict, asset: dict, profile: dict, family: str) -> tuple:
    """The hyper-parameter coordinate's one candidate: the best admissible point of a study run on this
    state's own X and Y. Nothing when no point beats the state — which is the same guarantee the study once
    carried by starting from the state's own parameters, now kept by the gate instead of by a fit.

    The candidate is the best **admissible** point, not the best point. A study's best trial by value may be
    one whose chosen threshold does not beat the champion on every fold; the state gate refuses such a child,
    and offering it meant the loop answered nothing while holding, further down its own list, a point the
    gate would have kept. The trials are read by value, descending, and the first that is admissible and
    beats the champion's own path is offered. When none is, the loop keeps nothing — which is an answer.

    The study's points are fits the search pays for and the ledger never sees, because only the one the study
    chose becomes a state: the count goes back under `asset["trial_count_drawn"]` — every point the sampler drew,
    pruned and completed alike, and every one of them a point the study chose to try."""
    del profile, family
    study = search_hyperparameters(asset["xy_for"](state), asset["bars_1m"], asset.get("champion_by_fold"))
    asset["trial_count_drawn"] = len(study.trials)
    log_trials(asset["ticker"], study, "coordinate_search", asset["round"])
    completed = study.get_trials(deepcopy=False, states=(optuna.trial.TrialState.COMPLETE,))
    admissible = sorted((trial for trial in completed
                         if trial.user_attrs.get("admissible")
                         and trial.value > asset["champion_objective"]),
                        key=lambda trial: (-trial.value, trial.number))
    if not admissible or admissible[0].params == state["best_params"]:
        return ()
    return ((config.COORDINATE_SEARCH_MOVE_FORWARD, "hpo",
             {**state, "best_params": admissible[0].params}, config.REBUILD_FITS),)


def main() -> int:
    args = config.build_ticker_parser("Optuna TPE hyper-parameter search per asset").parse_args()
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    for ticker in config.parse_tickers(args.tickers):
        xy = dataset.load_xy(ticker)
        bars_1m = strategy.load_bars_1m(ticker)
        # the stage has no champion to beat and no point to start from: it is a function of X, Y and the
        # frozen constants, so <TICKER>_parameters.json is a function of the raw store and this code and
        # never of its own last value. A point to start from belongs to the search's hpo loop, where the
        # round's champion is an input the state file records
        study = search_hyperparameters(xy, bars_1m)
        if not study.get_trials(deepcopy=False, states=(optuna.trial.TrialState.COMPLETE,)):
            raise SystemExit(f"{ticker}: no admissible strategy on every validation fold at any threshold — "
                             f"every one of the {config.HYPERPARAMETER_SEARCH_TRIAL_COUNT} trials was pruned")
        payload = {
            "hyperparameter_search_result": {
                "best_params": study.best_trial.params,
                OBJECTIVE_KEY: study.best_value,
                "trial_count": config.HYPERPARAMETER_SEARCH_TRIAL_COUNT,
            },
        }
        out = config.parameters_json(ticker)
        dataset.write_json(out, payload)
        log_trials(ticker, study, "hpo", None)
        print(f"{ticker} {out.name}: {OBJECTIVE_KEY} {study.best_value:.6f} "
              f"(trial {study.best_trial.number})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
