"""Coordinate search on the validation folds under the asset's profile, selecting on the model's own
validation objective: a move is kept only where it is better than the state it came from on **every**
validation fold — strictly for a move that grows the state, at no worse for one that shrinks it.

A **round** applies each loop the profile names, once, in the frozen order of COORDINATE_SEARCH_ROUND_LOOPS.
A loop's **pass** expands the beam one **family** at a time, each family seeded by the beam the family
before it left — which is what makes one forward move and one backward move a single pass. A round that
keeps nothing is convergence, and the state it stopped at is coordinate-wise locally optimal, never a
global optimum.

Every scored state, recorded in `<TICKER>_coordinate_search.json`, is the stage's own state, written after
each, so an interrupted run resumes at the top of its round without a refit and a finished run is read,
not rewritten. Promotes nothing: the proposals are read by a hand and copied by coordinate_search_promote."""

from __future__ import annotations

import numpy as np

from . import config, dataset, feature_set_search, model, strategy, train

# one module per coordinate — the token a profile's `loops` names, the module that knows its moves and the
# families it expands them in
LOOP_MODULES = {config.COORDINATE_SEARCH_LOOP_FEATURE_SET: feature_set_search}


def state_key(state: dict, timeframes: tuple[str, ...]) -> tuple:
    """A state as the scored-trial index keys it: the set timeframe-major, the barrier geometry in the
    order the register names it, and the hyper-parameter point in the space's own — independent of how a
    dict was built or read back. Every grid value is a whole number or a multiple of a quarter, so the
    equality is exact and asks for no tolerance."""
    return (feature_set_search.set_key(state["columns_by_timeframe"], timeframes),
            tuple((name, state[name]) for name in config.BARRIER_COORDINATE_NAMES),
            tuple((name, state["best_params"][name]) for name in config.HYPERPARAMETER_SEARCH_SPACE))


def to_state(row: dict, timeframes: tuple[str, ...]) -> dict:
    """The state a trial recorded, as a generator takes one: a JSON round trip leaves lists where the key
    wants tuples, so it is the to_tuples of a whole state."""
    return {"columns_by_timeframe": feature_set_search.to_tuples(row["columns_by_timeframe"], timeframes),
            "best_params": row["best_params"],
            **{name: row[name] for name in config.BARRIER_COORDINATE_NAMES}}


def trial_result(asset: dict, state: dict) -> dict:
    """Score one state: three boosters fitted as train.py fits them, their objective per fold, and the
    strategy's threshold selection on their predictions. The row carries the whole state, so the gate, the
    ranking, the beam and the cache never ask which coordinate moved."""
    xy = asset["xy"]
    x, feature_columns = dataset.build_x(xy["catalogue_values"], state["columns_by_timeframe"], asset["timeframes"])
    xy_candidate = {**xy, "x": x, "feature_columns": feature_columns,
                    "barriers": dataset.barriers_from({name: state[name] for name in config.BARRIER_COORDINATE_NAMES})}
    prediction_records, skill_by_fold = [], {}
    for fold_id in config.VALIDATION_FOLD_IDS:
        metrics, _, rows, _ = train.fold_evaluation(xy_candidate, asset["y_cls"], state["best_params"], fold_id)
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
    selection = strategy.entry_edge_threshold_selection(
        strategy.build_simulation_inputs(xy_candidate, asset["bars_1m"], oos_predictions))
    by_fold = selection["validation_by_fold"]
    return {
        "columns_by_timeframe": state["columns_by_timeframe"],
        "best_params": state["best_params"],
        **{name: state[name] for name in config.BARRIER_COORDINATE_NAMES},
        "validation": {f"fold_{fold_id}": {"relative_logloss_skill": skill_by_fold[fold_id],
                                           "sharpe": by_fold[fold_id]["sharpe"],
                                           "trade_count": by_fold[fold_id]["trade_count"]}
                       for fold_id in config.VALIDATION_FOLD_IDS},
        "mean_relative_logloss_skill": float(np.mean([skill_by_fold[fold_id] for fold_id in config.VALIDATION_FOLD_IDS])),
        "entry_edge_threshold": selection["entry_edge_threshold"],
        "entry_edge_threshold_constraint_met": selection["entry_edge_threshold_constraint_met"],
        "selection_score_mean_sharpe": selection["selection_score_mean_sharpe"],
    }


# ---- the one selection: the objective the experiment froze, read per fold and over a whole state -------

def fold_objective(row: dict) -> list[float]:
    """What the gate compares fold by fold — the frozen objective, in the fold table's order."""
    return [row["validation"][f"fold_{fold_id}"][config.SELECTION_OBJECTIVE]
            for fold_id in config.VALIDATION_FOLD_IDS]


def state_objective(row: dict) -> float:
    """What the ranking maximises over a whole state."""
    return row["mean_relative_logloss_skill"]


def is_gate_cleared(row: dict, parent: dict, move: str) -> bool:
    """Whether a child may be kept at all: better than the state it came from on every validation fold, or,
    for a move that shrinks the state, no worse on any of them."""
    if move == config.COORDINATE_SEARCH_MOVE_BACKWARD:
        return all(child >= own for child, own in zip(fold_objective(row), fold_objective(parent)))
    return all(child > own for child, own in zip(fold_objective(row), fold_objective(parent)))


def ranking_key(trials: list[dict], index: int, timeframes: tuple[str, ...]) -> tuple:
    """The one order the beam and the proposals take: the objective down, then the smaller set, then the
    earlier trial."""
    row = trials[index - 1]
    return (-state_objective(row),
            feature_set_search.column_count(row["columns_by_timeframe"], timeframes), index)


def top_beam(children: list[int], trials: list[dict], timeframes: tuple[str, ...]) -> list[int]:
    """The beam a family leaves: the best distinct children by the ranking key, at most the width. Two
    parents can reach one state and the cache hands back one trial for both, so the indices are made
    distinct before the width is applied — a beam of three is three states, not one state three times."""
    ranked = sorted(dict.fromkeys(children), key=lambda index: ranking_key(trials, index, timeframes))
    return ranked[:config.COORDINATE_SEARCH_BEAM_WIDTH]


# ---- the state file ------------------------------------------------------------------------------------

def path_entry(state_file: dict, loop: str, family: str, beam: list[int]) -> dict:
    """One accepted expansion of the research path: which loop and family moved the search, where it landed
    and what the beam held after it."""
    row = state_file["trials"][beam[0] - 1]
    return {"round": state_file["round_count"] + 1, "loop": loop, "family": family,
            "trial": beam[0], "beam": list(beam), "move": row["move"],
            "mean_relative_logloss_skill": row["mean_relative_logloss_skill"]}


def proposals_block(trials: list[dict], active_state: dict, champion_trial: int,
                    timeframes: tuple[str, ...]) -> list[dict]:
    """The states a hand may promote: the champion the search accepted first, then the trials no validation
    fold scores below the state the search started from, by the ranking key. A state worse on any fold is
    never proposed."""
    active_key = state_key(active_state, timeframes)
    qualifiers = [(index, row) for index, row in enumerate(trials, start=1)
                  if state_key(row, timeframes) != active_key
                  and all(child >= own for child, own in zip(fold_objective(row), fold_objective(trials[0])))]
    # the champion first — the state the search itself accepted, move by move — then the rest by the key
    ranked = sorted(qualifiers, key=lambda item: (item[0] != champion_trial,
                                                  *ranking_key(trials, item[0], timeframes)))
    active = feature_set_search.to_tuples(active_state["columns_by_timeframe"], timeframes)
    return [{
        "proposal": rank,
        "trial": index,
        "loop": row["loop"],
        "columns_by_timeframe": row["columns_by_timeframe"],
        "added_columns_by_timeframe": feature_set_search.columns_added(row["columns_by_timeframe"], active, timeframes),
        "removed_columns_by_timeframe": feature_set_search.columns_removed(row["columns_by_timeframe"], active, timeframes),
        **{name: row[name] for name in config.BARRIER_COORDINATE_NAMES},
        "mean_relative_logloss_skill": row["mean_relative_logloss_skill"],
        "validation": row["validation"],
        "entry_edge_threshold": row["entry_edge_threshold"],
        "entry_edge_threshold_constraint_met": row["entry_edge_threshold_constraint_met"],
        "selection_score_mean_sharpe": row["selection_score_mean_sharpe"],
    } for rank, (index, row) in enumerate(ranked[:config.COORDINATE_SEARCH_PROPOSAL_COUNT], start=1)]


def write_state(ticker: str, state_file: dict, active_state: dict, timeframes: tuple[str, ...]) -> None:
    state_file["proposals"] = proposals_block(state_file["trials"], active_state,
                                              state_file["champion_trial"] or 1, timeframes)
    dataset.write_json(config.coordinate_search_json(ticker), state_file)


def build_search_inputs(best_params: dict, active_columns_by_timeframe: dict, active_barriers: dict,
                        cat: dict, profile: dict) -> dict:
    """What a search is conditioned on: the frozen window with its warm-up, the parameters and the barrier
    geometry it starts from, the catalogue it draws from, the profile a hand drafted and the selection the
    experiment froze — recorded in the state file, compared by equality on a rerun, and compared again by
    status.py to say whether a recorded search still describes the asset. The selection belongs here
    because flipping it is a different experiment, not a different mood: without it a rerun under the other
    objective would resume this one's trials instead of starting its own."""
    return {
        "research_window": {"start_utc": config.RESEARCH_START_UTC, "end_utc": config.RESEARCH_END_UTC,
                            "seed": config.SEED, "warmup_top_timeframe_bars": cat["warmup_top_timeframe_bars"]},
        "best_params": best_params,
        "catalogue_columns_by_timeframe": {timeframe: tuple(cat["columns_by_timeframe"][timeframe])
                                           for timeframe in config.timeframes(cat)},
        "active_columns_by_timeframe": active_columns_by_timeframe,
        "active_barriers": {name: active_barriers[name] for name in config.BARRIER_COORDINATE_NAMES},
        "profile": profile,
        "selection": {"objective": config.SELECTION_OBJECTIVE,
                      "beam_width": config.COORDINATE_SEARCH_BEAM_WIDTH},
    }


def start_state(profile: dict, active_columns_by_timeframe: dict, active_barriers: dict,
                best_params: dict, timeframes: tuple[str, ...]) -> dict:
    """The state a search starts from: the columns the profile names, else the asset's own set, with the
    asset's own barrier geometry and the parameters it holds fixed."""
    columns = profile["start_columns_by_timeframe"] or active_columns_by_timeframe
    return {"columns_by_timeframe": feature_set_search.to_tuples(columns, timeframes),
            "best_params": best_params,
            **{name: active_barriers[name] for name in config.BARRIER_COORDINATE_NAMES}}


def progress_line(ticker: str, state_file: dict, loop: str, label: str, parent: dict, row: dict) -> str:
    return (f"{ticker} round {state_file['round_count'] + 1} {loop} {label} "
            f"skill {parent['mean_relative_logloss_skill']:+.4f} -> {row['mean_relative_logloss_skill']:+.4f} "
            f"folds {'/'.join(f'{value:+.4f}' for value in fold_objective(row))} "
            f"sharpe {row['selection_score_mean_sharpe']:+.2f}")


def main() -> int:
    args = config.build_ticker_parser(
        "coordinate search on the validation folds under the asset's profile and frozen parameters; resumes"
    ).parse_args()

    for ticker in config.parse_tickers(args.tickers):
        profile = dataset.load_json(config.coordinate_search_profile_json(ticker))
        best = dataset.load_json(config.parameters_json(ticker))["hyperparameter_search_result"]["best_params"]
        xy = dataset.load_xy(ticker)
        cat, timeframes = xy["catalogue"], xy["timeframes"]
        asset = {"xy": xy, "y_cls": model.to_class(xy["y"]), "bars_1m": strategy.load_bars_1m(ticker),
                 "catalogue": cat, "timeframes": timeframes}
        active_columns = dataset.load_feature_columns(ticker, cat)
        active_state = start_state({"start_columns_by_timeframe": None}, active_columns, xy["barriers"], best, timeframes)
        inputs = dataset.to_json_safe(build_search_inputs(best, active_columns, xy["barriers"], cat, profile))

        # the state: the recorded run when its inputs are the inputs of this one, else a fresh state
        path = config.coordinate_search_json(ticker)
        state_file = dataset.load_json(path) if path.exists() else None
        if state_file is None or state_file["inputs"] != inputs:
            state_file = {"inputs": inputs, "trials": [], "beam": [], "champion_trial": None,
                          "round_count": 0, "pass_count_by_loop": {}, "trial_count_by_loop": {},
                          "search_converged": False, "path": []}
        trials = state_file["trials"]
        trial_index_by_state = {}
        for index, row in enumerate(trials, start=1):
            row["columns_by_timeframe"] = feature_set_search.to_tuples(row["columns_by_timeframe"], timeframes)
            trial_index_by_state[state_key(row, timeframes)] = index
        if state_file["search_converged"]:
            print(f"{ticker}: the search converged after {state_file['round_count']} rounds and {len(trials)} "
                  f"trials — {len(state_file['proposals'])} proposals in {path.name}", flush=True)
            continue

        def score(child: dict, loop: str | None, family: str | None, move: str | None, parent: int | None) -> int:
            """The trial index of a state: its earlier trial's when it was scored before, else a new trial
            scored now. The counters advance at the end of a round, so a trial of the round in flight
            carries the number that round will take."""
            key = state_key(child, timeframes)
            if key in trial_index_by_state:
                return trial_index_by_state[key]
            row = trial_result(asset, child)
            trials.append({**row, "loop": loop, "family": family, "move": move,
                           "pass": state_file["round_count"] + 1 if move else 0,
                           "round": state_file["round_count"] + 1 if move else 0,
                           "parent_trial": parent})
            trial_index_by_state[key] = len(trials)
            if loop:
                state_file["trial_count_by_loop"][loop] = state_file["trial_count_by_loop"].get(loop, 0) + 1
            write_state(ticker, state_file, active_state, timeframes)
            return len(trials)

        if not trials:
            index = score(start_state(profile, active_columns, xy["barriers"], best, timeframes), None, None, None, None)
            print(f"{ticker} start state skill {trials[index - 1]['mean_relative_logloss_skill']:+.4f} folds "
                  f"{'/'.join(f'{value:+.4f}' for value in fold_objective(trials[index - 1]))} "
                  f"sharpe {trials[index - 1]['selection_score_mean_sharpe']:+.2f}", flush=True)
        # trial 1 is the state the search started from — the champion until a family keeps a move
        beam = state_file["beam"] or [state_file["champion_trial"] or 1]
        state_file["champion_trial"] = beam[0]

        while not state_file["search_converged"]:
            round_number = state_file["round_count"] + 1
            round_accepted = False
            for loop in profile["loops"]:
                for family in LOOP_MODULES[loop].FAMILIES:
                    children = []
                    for parent in beam:
                        parent_row = trials[parent - 1]
                        for move, label, child in LOOP_MODULES[loop].moves(
                                to_state(parent_row, timeframes), asset, profile, family):
                            index = score(child, loop, family, move, parent)
                            print(progress_line(ticker, state_file, loop, label, parent_row, trials[index - 1]), flush=True)
                            if is_gate_cleared(trials[index - 1], parent_row, move):
                                children.append(index)
                    if children:
                        beam = top_beam(children, trials, timeframes)
                        round_accepted = True
                        state_file["path"].append(path_entry(state_file, loop, family, beam))
                # the champion moves once per loop, after its families — the one the next loop starts from
                state_file["champion_trial"] = beam[0]
                state_file["pass_count_by_loop"][loop] = round_number
            state_file["beam"] = list(beam)
            state_file["round_count"] = round_number
            state_file["search_converged"] = not round_accepted
            write_state(ticker, state_file, active_state, timeframes)

        champion_row = trials[state_file["champion_trial"] - 1]
        print(f"{ticker} {path.name}: converged after {state_file['round_count']} rounds and {len(trials)} trials, "
              f"champion skill {champion_row['mean_relative_logloss_skill']:+.4f} "
              f"({feature_set_search.column_count(champion_row['columns_by_timeframe'], timeframes)} columns), "
              f"{len(state_file['proposals'])} proposals", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
