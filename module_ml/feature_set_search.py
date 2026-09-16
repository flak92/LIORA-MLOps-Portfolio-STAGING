"""Stepwise feature-set search on the validation folds under the asset's frozen hyper-parameters, selecting on the
model's own validation objective: a forward move adds the column that raises the relative log-loss skill of every
validation fold, a backward move drops a column at no worse skill on every fold, until a pass accepts nothing. A
trial's strategy numbers are reported beside it and never selected on. Every scored trial, recorded in
`<TICKER>_feature_set_search.json`, is the state, written after each, so an interrupted run resumes without a refit and
a finished run is read, not rewritten.
Promotes nothing: the proposals are read by a hand and copied by feature_set_promote."""

from __future__ import annotations

import numpy as np

from . import config, dataset, model, strategy, train


# the helpers take the hierarchy from the asset's contract (xy["timeframes"]) — the ML layer holds no register of its own
def columns_added(columns_by_timeframe: dict, active: dict, timeframes: tuple[str, ...]) -> dict:
    return {timeframe: [name for name in columns_by_timeframe[timeframe] if name not in active[timeframe]]
            for timeframe in timeframes}


def columns_removed(columns_by_timeframe: dict, active: dict, timeframes: tuple[str, ...]) -> dict:
    return columns_added(active, columns_by_timeframe, timeframes)


def column_count(columns_by_timeframe: dict, timeframes: tuple[str, ...]) -> int:
    return sum(len(columns_by_timeframe[timeframe]) for timeframe in timeframes)


def with_column(columns_by_timeframe: dict, timeframe: str, name: str, catalogue_columns: list[str]) -> dict:
    """The set with one definition added on one timeframe, kept in catalogue order — the order the contract lists."""
    kept = set(columns_by_timeframe[timeframe]) | {name}
    return {**columns_by_timeframe,
            timeframe: tuple(column for column in catalogue_columns if column in kept)}


def without_column(columns_by_timeframe: dict, timeframe: str, name: str) -> dict:
    return {**columns_by_timeframe,
            timeframe: tuple(column for column in columns_by_timeframe[timeframe] if column != name)}


def to_tuples(columns_by_timeframe: dict, timeframes: tuple[str, ...]) -> dict:
    return {timeframe: tuple(columns_by_timeframe[timeframe]) for timeframe in timeframes}


def set_key(columns_by_timeframe: dict, timeframes: tuple[str, ...]) -> tuple:
    """A set as the scored-trial index keys it: timeframe-major, independent of how a dict was built or read back."""
    return tuple((timeframe, tuple(columns_by_timeframe[timeframe])) for timeframe in timeframes)


def fold_skills(row: dict) -> list[float]:
    return [row["validation"][f"fold_{fold_id}"]["relative_logloss_skill"] for fold_id in config.VALIDATION_FOLD_IDS]


def is_skill_raised_on_every_fold(row: dict, champion: dict) -> bool:
    return all(skill > champion_skill for skill, champion_skill in zip(fold_skills(row), fold_skills(champion)))


def is_skill_no_worse_on_every_fold(row: dict, champion: dict) -> bool:
    return all(skill >= champion_skill for skill, champion_skill in zip(fold_skills(row), fold_skills(champion)))


def trial_result(xy: dict, y_cls: np.ndarray, best: dict, bars_1m: dict[str, np.ndarray], columns_by_timeframe: dict) -> dict:
    """Score one set: three boosters fitted as train.py fits them, their skill per fold, and — reported, never
    selected on — the strategy's threshold selection on their predictions."""
    x, feature_columns = dataset.build_x(xy["catalogue_values"], columns_by_timeframe, xy["timeframes"])
    xy_candidate = {**xy, "x": x, "feature_columns": feature_columns}
    prediction_records, skill_by_fold = [], {}
    for fold_id in config.VALIDATION_FOLD_IDS:
        metrics, _, rows, _ = train.fold_evaluation(xy_candidate, y_cls, best, fold_id)
        skill_by_fold[fold_id] = metrics["relative_logloss_skill"]
        prediction_records.extend(rows)
    # the predictions as strategy.load_oos_predictions returns them: fold-major, by decision, the probabilities widened
    # to float64 exactly as the parquet round trip widens them
    oos_predictions = {
        "decision_ts": np.array([row[0] for row in prediction_records], dtype=np.int64),
        "oos_fold_id": np.array([row[1] for row in prediction_records], dtype=np.int8),
        "p_short": np.array([row[2] for row in prediction_records], dtype=np.float64),
        "p_neutral": np.array([row[3] for row in prediction_records], dtype=np.float64),
        "p_long": np.array([row[4] for row in prediction_records], dtype=np.float64),
    }
    selection = strategy.entry_edge_threshold_selection(strategy.build_simulation_inputs(xy_candidate, bars_1m, oos_predictions))
    by_fold = selection["validation_by_fold"]
    return {
        "columns_by_timeframe": columns_by_timeframe,
        "validation": {f"fold_{fold_id}": {"relative_logloss_skill": skill_by_fold[fold_id],
                                           "sharpe": by_fold[fold_id]["sharpe"],
                                           "trade_count": by_fold[fold_id]["trade_count"]}
                       for fold_id in config.VALIDATION_FOLD_IDS},
        "mean_relative_logloss_skill": float(np.mean([skill_by_fold[fold_id] for fold_id in config.VALIDATION_FOLD_IDS])),
        "entry_edge_threshold": selection["entry_edge_threshold"],
        "entry_edge_threshold_constraint_met": selection["entry_edge_threshold_constraint_met"],
        "selection_score_mean_sharpe": selection["selection_score_mean_sharpe"],
    }


def proposals_block(trials: list[dict], active: dict, champion_trial: int, timeframes: tuple[str, ...]) -> list[dict]:
    """The sets a hand may promote: the champion the search accepted first, then the trials no validation fold
    scores below the active set, by mean skill. A set worse on any fold is never proposed."""
    active = to_tuples(active, timeframes)
    qualifiers = [(index, row) for index, row in enumerate(trials, start=1)
                  if row["columns_by_timeframe"] != active and is_skill_no_worse_on_every_fold(row, trials[0])]
    # the champion first — the set the search itself accepted, move by move — then the rest by mean skill,
    # ties to the smaller set and to the earlier trial
    ranked = sorted(qualifiers, key=lambda item: (item[0] != champion_trial,
                                                  -item[1]["mean_relative_logloss_skill"],
                                                  column_count(item[1]["columns_by_timeframe"], timeframes), item[0]))
    return [{
        "proposal": rank,
        "trial": index,
        "columns_by_timeframe": row["columns_by_timeframe"],
        "added_columns_by_timeframe": columns_added(row["columns_by_timeframe"], active, timeframes),
        "removed_columns_by_timeframe": columns_removed(row["columns_by_timeframe"], active, timeframes),
        "mean_relative_logloss_skill": row["mean_relative_logloss_skill"],
        "validation": row["validation"],
        "entry_edge_threshold": row["entry_edge_threshold"],
        "entry_edge_threshold_constraint_met": row["entry_edge_threshold_constraint_met"],
        "selection_score_mean_sharpe": row["selection_score_mean_sharpe"],
    } for rank, (index, row) in enumerate(ranked[:config.FEATURE_SET_PROPOSAL_COUNT], start=1)]


def write_state(ticker: str, state: dict, timeframes: tuple[str, ...]) -> None:
    state["proposals"] = proposals_block(state["trials"], state["inputs"]["active_columns_by_timeframe"],
                                         state["champion_trial"] or 1, timeframes)
    dataset.write_json(config.feature_set_search_json(ticker), state)


def build_search_inputs(best_params: dict, active_columns_by_timeframe: dict, cat: dict) -> dict:
    """What a search is conditioned on: the frozen window with its warm-up, the parameters it holds fixed, the
    catalogue it draws from and the set it starts at — recorded in the search's state file, compared by equality on a
    rerun, and compared again by status.py to say whether a recorded search still describes the asset."""
    return {
        "research_window": {"start_utc": config.RESEARCH_START_UTC, "end_utc": config.RESEARCH_END_UTC,
                            "seed": config.SEED, "warmup_top_timeframe_bars": cat["warmup_top_timeframe_bars"]},
        "best_params": best_params,
        "catalogue_columns_by_timeframe": {timeframe: tuple(cat["columns_by_timeframe"][timeframe])
                                           for timeframe in config.timeframes(cat)},
        "active_columns_by_timeframe": active_columns_by_timeframe,
    }


def progress_line(ticker: str, pass_number: int, move: str, column: str, champion: dict, row: dict) -> str:
    return (f"{ticker} pass {pass_number} {move} {column} skill {champion['mean_relative_logloss_skill']:+.4f} -> "
            f"{row['mean_relative_logloss_skill']:+.4f} folds {'/'.join(f'{skill:+.4f}' for skill in fold_skills(row))} "
            f"sharpe {row['selection_score_mean_sharpe']:+.2f}")


def main() -> int:
    args = config.build_ticker_parser(
        "stepwise feature-set search on the validation folds under the frozen hyper-parameters; resumes"
    ).parse_args()

    for ticker in config.parse_tickers(args.tickers):
        best = dataset.load_json(config.parameters_json(ticker))["hyperparameter_search_result"]["best_params"]
        xy = dataset.load_xy(ticker)
        cat, timeframes = xy["catalogue"], xy["timeframes"]
        y_cls = model.to_class(xy["y"])
        bars_1m = strategy.load_bars_1m(ticker)
        active = dataset.load_feature_columns(ticker, cat)
        inputs = dataset.to_json_safe(build_search_inputs(best, active, cat))

        # the state: the recorded run when its inputs are the inputs of this one, else a fresh state
        path = config.feature_set_search_json(ticker)
        state = dataset.load_json(path) if path.exists() else None
        if state is None or state["inputs"] != inputs:
            state = {"inputs": inputs, "trials": [], "champion_trial": None, "pass_count": 0, "search_converged": False}
        trials = state["trials"]
        trial_index_by_set = {}
        for index, row in enumerate(trials, start=1):
            row["columns_by_timeframe"] = to_tuples(row["columns_by_timeframe"], timeframes)
            trial_index_by_set[set_key(row["columns_by_timeframe"], timeframes)] = index
        if state["search_converged"]:
            print(f"{ticker}: the search converged after {state['pass_count']} passes and {len(trials)} trials — "
                  f"{len(state['proposals'])} proposals in {path.name}", flush=True)
            continue

        def score(columns_by_timeframe: dict, move: str | None) -> int:
            """The trial index of a set: its earlier trial's when it was scored before, else a new trial scored now."""
            key = set_key(columns_by_timeframe, timeframes)
            if key in trial_index_by_set:
                return trial_index_by_set[key]
            row = trial_result(xy, y_cls, best, bars_1m, columns_by_timeframe)
            trials.append({**row, "pass": state["pass_count"] + 1 if move else 0, "move": move})
            trial_index_by_set[key] = len(trials)
            write_state(ticker, state, timeframes)
            return len(trials)

        if not trials:
            index = score(active, None)
            print(f"{ticker} active set skill {trials[index - 1]['mean_relative_logloss_skill']:+.4f} folds "
                  f"{'/'.join(f'{skill:+.4f}' for skill in fold_skills(trials[index - 1]))} "
                  f"sharpe {trials[index - 1]['selection_score_mean_sharpe']:+.2f}", flush=True)
        # trial 1 is the active set by construction — the champion until a pass accepts a move
        champion = state["champion_trial"] or 1
        state["champion_trial"] = champion

        while not state["search_converged"]:
            pass_number = state["pass_count"] + 1
            accepted = False

            # forward: every set with one more column; a candidate qualifies when it raises the skill of every
            # fold, and the highest mean skill among them is accepted, ties to the earlier candidate
            champion_row = trials[champion - 1]
            best_index = None
            for timeframe in timeframes:
                for name in cat["columns_by_timeframe"][timeframe]:
                    if name in champion_row["columns_by_timeframe"][timeframe]:
                        continue
                    index = score(with_column(champion_row["columns_by_timeframe"], timeframe, name,
                                              cat["columns_by_timeframe"][timeframe]),
                                  config.FEATURE_SET_SEARCH_MOVE_FORWARD)
                    row = trials[index - 1]
                    print(progress_line(ticker, pass_number, config.FEATURE_SET_SEARCH_MOVE_FORWARD,
                                        f"+{config.feature_id(name, timeframe)}", champion_row, row), flush=True)
                    if is_skill_raised_on_every_fold(row, champion_row) and (
                            best_index is None
                            or row["mean_relative_logloss_skill"] > trials[best_index - 1]["mean_relative_logloss_skill"]):
                        best_index = index
            if best_index is not None:
                champion, accepted = best_index, True

            # backward: every set with one column fewer, never the last column of the set; a candidate qualifies
            # at no worse skill on every fold, and the highest mean skill among them is accepted
            champion_row = trials[champion - 1]
            best_index = None
            if column_count(champion_row["columns_by_timeframe"], timeframes) > 1:
                for timeframe in timeframes:
                    for name in champion_row["columns_by_timeframe"][timeframe]:
                        index = score(without_column(champion_row["columns_by_timeframe"], timeframe, name),
                                      config.FEATURE_SET_SEARCH_MOVE_BACKWARD)
                        row = trials[index - 1]
                        print(progress_line(ticker, pass_number, config.FEATURE_SET_SEARCH_MOVE_BACKWARD,
                                            f"-{config.feature_id(name, timeframe)}", champion_row, row), flush=True)
                        if is_skill_no_worse_on_every_fold(row, champion_row) and (
                                best_index is None
                                or row["mean_relative_logloss_skill"] > trials[best_index - 1]["mean_relative_logloss_skill"]):
                            best_index = index
            if best_index is not None:
                champion, accepted = best_index, True

            state["champion_trial"] = champion
            state["pass_count"] = pass_number
            state["search_converged"] = not accepted
            write_state(ticker, state, timeframes)

        champion_row = trials[champion - 1]
        print(f"{ticker} {path.name}: converged after {state['pass_count']} passes and {len(trials)} trials, "
              f"champion skill {champion_row['mean_relative_logloss_skill']:+.4f} "
              f"({column_count(champion_row['columns_by_timeframe'], timeframes)} columns), {len(state['proposals'])} proposals", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
