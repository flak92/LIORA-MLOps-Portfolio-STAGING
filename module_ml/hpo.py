"""Optuna TPE per asset, sequential and seeded, over the frozen search space. The objective is the CAGR of
the chained validation path at the threshold the one selection rule would pick — the quantity the coordinate
search selects on, so the parameters are tuned on it. The final holdout is never touched here.

The stage is a function of X, Y and the frozen constants alone: it draws no point to start from, so the
parameters file it writes is a function of the raw store and this code, never of what it wrote last.

Inside a coordinate search the study is also a coordinate, and there a point to start from is proper: one
candidate, warm-started at the point the state already holds — an input the search records in `inputs` — so
it can never answer worse than where it began, and pruned by two explicit gates.
After each fold a trial reports what it reached, then stops if the best that fold could still do — over the
whole threshold grid, among the points clearing the trade floor — cannot beat the champion's own on that
fold, on the Calmar ratio or on the growth rate. The bound is an upper bound, so a gate that prunes on it
can never discard a trial the search would have kept; and because the bound is a fold's own, the gate fires
on the first fold that settles the question. Optuna's own median pruner is not one of these gates and is
not used: it compares a trial's best value over all its steps with the median of other trials at one step,
and with folds as calendar years that comparison is not of like with like.

Every point the search drew is left in the asset's trial ledger, where the parameters file keeps only the
one it chose; the ledger is this module's mlflow boundary."""

from __future__ import annotations

import mlflow
import numpy as np
import optuna

from . import config, dataset, model, strategy, train, validation


def log_trials(ticker: str, trials: list[dict]) -> None:
    """Every trial of the search: one mlflow run per trial, named `hpo_<n>` — its place in that search, counting from
    one — in the asset's own ledger, so two fanned-out processes share no path and no experiment id. The experiment
    is the ticker and is reused, so a rerun appends a search of its own, `hpo_1` again; the ledger only grows. mlflow's
    own vocabulary, its run id among it, begins and ends inside this call."""
    ledger = config.trials_sqlite(ticker)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{ledger}")
    mlflow.set_experiment(ticker)
    for index, trial in enumerate(trials, start=1):
        with mlflow.start_run(run_name=f"hpo_{index}"):
            mlflow.log_params(trial["params"])
            mlflow.log_metrics(trial["metrics"])


# the key the chosen point's value is published under, and the name one trial's value carries in the
# ledger — each named for what it measures
OBJECTIVE_KEY = "best_cagr_validation_path"
TRIAL_METRIC_KEY = "cagr_validation_path"


def fold_pruning_bound(sweep: dict[float, dict], measure: str) -> float:
    """The highest one fold can reach on a measure over the whole threshold grid, among the points clearing
    the trade floor — an upper bound on what a trial can still realise there, and -inf when no threshold
    clears it, which is a fold on which the trial has no admissible strategy at all."""
    return max((result[measure] for result in sweep.values()
                if result["trade_count"] >= config.MINIMUM_TRADES_PER_VALIDATION_FOLD),
               default=-np.inf)


def sweep_value(sweeps: dict[int, dict]) -> float:
    """A trial's own value: the chained path's growth rate at the threshold the one selection rule would
    pick over these folds.

    A trial where no point of the grid clears the trade floor in every fold has no value, and is pruned
    rather than scored at the grid floor. The floor was the rule's fallback, and it is a fallback for a
    *report* — a number to show when nothing qualified. Handing it to a sampler as a value let a trial that
    never qualified compete, and win, on the numbers of a threshold nothing qualified for."""
    cleared = [threshold for threshold in config.ENTRY_EDGE_THRESHOLD_GRID
               if all(sweeps[fold_id][threshold]["trade_count"] >= config.MINIMUM_TRADES_PER_VALIDATION_FOLD
                      for fold_id in config.VALIDATION_FOLD_IDS)]
    if not cleared:
        raise optuna.TrialPruned()
    return max(strategy.validation_path_cagr(
        {fold_id: sweeps[fold_id][threshold]["final_equity"] for fold_id in config.VALIDATION_FOLD_IDS})
        for threshold in cleared)


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
        for step, fold_id in enumerate(config.VALIDATION_FOLD_IDS):
            _, _, rows, _ = train.fold_evaluation(xy, y_cls, params, fold_id)
            prediction_records.extend(rows)
            simulation_inputs = strategy.build_simulation_inputs(
                xy, bars_1m, train.to_oos_predictions(prediction_records))
            sweeps[fold_id] = strategy.results_by_threshold(
                simulation_inputs, strategy.signals_for_fold(simulation_inputs, fold_id),
                *validation.fold_bounds(fold_id))
            # report first, so a pruned trial still has a value the ledger can carry
            trial.report(fold_pruning_bound(sweeps[fold_id], "cagr"), step=step)
            if champion_by_fold is not None:
                fold = champion_by_fold[fold_id]
                if (fold_pruning_bound(sweeps[fold_id], "calmar") <= fold["calmar"]
                        or fold_pruning_bound(sweeps[fold_id], "cagr") <= fold["cagr"]):
                    raise optuna.TrialPruned()
        return sweep_value(sweeps)

    return objective


def trial_metrics(trial: optuna.trial.FrozenTrial) -> dict[str, float]:
    """What a trial leaves in the ledger — and it is not the same quantity for a trial that finished and one
    a gate stopped. A completed trial has the chained path's growth rate at the threshold the selection rule
    chose. A pruned one has only `fold_pruning_bound` at the fold it died on: an **upper bound** on a number
    it never reached, over folds it never all ran. Logging both under one key made two populations read as
    one, and the ledger's own mean was then a mean of bounds and values together."""
    if trial.value is not None:
        return {TRIAL_METRIC_KEY: trial.value}
    return {"fold_cagr_bound_at_pruning": trial.intermediate_values[max(trial.intermediate_values)]}


def trial_params(trial: optuna.trial.FrozenTrial) -> dict:
    """The point the trial drew, and for a pruned one the fold it was stopped at — a bound says nothing
    without the fold it bounds."""
    if trial.value is not None:
        return trial.params
    return {**trial.params,
            "pruned_at_fold": config.VALIDATION_FOLD_IDS[max(trial.intermediate_values)]}


def search_hyperparameters(xy: dict, bars_1m: dict[str, np.ndarray],
                           enqueue: dict | None = None,
                           champion_by_fold: dict[int, dict] | None = None) -> optuna.Study:
    """The asset's TPE search over the frozen space, sequential and seeded — the study itself, so a caller
    reads the point it chose, that point's value and every point it drew from one object. A point to start
    from is drawn first, before the sampler's own."""
    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=config.SEED,
                                           n_startup_trials=config.HYPERPARAMETER_SEARCH_STARTUP_TRIAL_COUNT),
    )
    if enqueue is not None:
        study.enqueue_trial(enqueue)
    study.optimize(build_objective(xy, bars_1m, champion_by_fold),
                   n_trials=config.HYPERPARAMETER_SEARCH_TRIAL_COUNT, n_jobs=1)
    return study


def moves(state: dict, asset: dict, profile: dict, family: str) -> tuple:
    """The hyper-parameter coordinate's one candidate: the best point of a study run on this state's own X
    and Y, warm-started at the point the state holds, so the study can never answer worse than where it
    began. Nothing when the incumbent wins — the state is its own candidate and the loop keeps nothing.

    The study's points are fits the search pays for and the ledger never sees, because only the one the study
    chose becomes a state: the count goes back under `asset["trials_drawn"]` — every point the **sampler**
    drew, pruned and completed alike. The point the study was handed is not one of them: it is the state
    already in the ledger, and counting it would inflate the loop's exposure by one per study with a
    candidate that was never a candidate."""
    del profile, family
    study = search_hyperparameters(asset["xy_for"](state), asset["bars_1m"], state["best_params"],
                                  asset.get("champion_by_fold"))
    asset["trials_drawn"] = len(study.trials) - 1        # the enqueued start is the state, not a draw
    completed = study.get_trials(deepcopy=False, states=(optuna.trial.TrialState.COMPLETE,))
    if not completed:
        return ()
    best = study.best_trial.params
    if best == state["best_params"]:
        return ()
    return ((config.COORDINATE_SEARCH_MOVE_FORWARD, "hpo", {**state, "best_params": best},
             config.REBUILD_FITS),)


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
        log_trials(ticker, [{"params": trial_params(trial), "metrics": trial_metrics(trial)}
                            for trial in study.trials])
        print(f"{ticker} {out.name}: {OBJECTIVE_KEY} {study.best_value:.6f} "
              f"(trial {study.best_trial.number})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
