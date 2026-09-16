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

import math

import numpy as np

from . import barrier_search, config, dataset, feature_set_search, hpo, labels, model, strategy, train

# one module per coordinate — the token a profile's `loops` names, the module that knows its moves and the
# families it expands them in
LOOP_MODULES = {config.COORDINATE_SEARCH_LOOP_BARRIER: barrier_search,
                config.COORDINATE_SEARCH_LOOP_FEATURE_SET: feature_set_search,
                config.COORDINATE_SEARCH_LOOP_HPO: hpo}


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
            **barrier_search.to_barrier(row)}


def xy_for_state(asset: dict, state: dict) -> dict:
    """X and Y for one state: the asset's own Y when the label's geometry is still the asset's — only X is
    stacked again — else Y walked down the 1m path in process and the feature grids joined to the decisions
    the new horizon admits."""
    barriers = dataset.barriers_from({name: state[name] for name in config.BARRIER_COORDINATE_NAMES})
    if all(asset["xy"]["barriers"][name] == barriers[name] for name in config.BARRIER_COORDINATE_NAMES):
        x, feature_columns = dataset.build_x(asset["xy"]["catalogue_values"],
                                             state["columns_by_timeframe"], asset["timeframes"])
        return {**asset["xy"], "x": x, "feature_columns": feature_columns, "barriers": barriers}
    label_events = labels.label_events(asset["label_inputs"], asset["catalogue"], barriers)
    return dataset.build_xy(asset["catalogue"], asset["timeframes"], asset["catalogue_values"],
                            asset["decision_grids"], label_events, state["columns_by_timeframe"], barriers)


def state_material(asset: dict, state: dict, rebuild: str, inherited: dict | None) -> dict:
    """What a state is scored from — X and Y, the three boosters' out-of-fold predictions and their skill.

    A move of the trade's own exit inherits all of it: neither a fit nor a prediction depends on where a
    position leaves, so only the geometry the backtest reads is replaced. Anything else is three fits, and Y
    before them when the label's own geometry moved."""
    barriers = dataset.barriers_from({name: state[name] for name in config.BARRIER_COORDINATE_NAMES})
    if rebuild == config.REBUILD_BACKTEST:
        return {**inherited, "xy": {**inherited["xy"], "barriers": barriers}}
    xy = xy_for_state(asset, state)
    y_cls = model.to_class(xy["y"])
    prediction_records, skill_by_fold = [], {}
    for fold_id in config.VALIDATION_FOLD_IDS:
        metrics, _, rows, _ = train.fold_evaluation(xy, y_cls, state["best_params"], fold_id)
        skill_by_fold[fold_id] = metrics["relative_logloss_skill"]
        prediction_records.extend(rows)
    return {"xy": xy, "skill_by_fold": skill_by_fold,
            "oos_predictions": train.to_oos_predictions(prediction_records)}


def trial_result(asset: dict, state: dict, material: dict) -> dict:
    """Score one state: the strategy's threshold selection on the boosters' predictions, the folds it chose
    at, and the path those folds chain into. The row carries the whole state, so the gate, the ranking, the
    beam and the cache never ask which coordinate moved."""
    selection = strategy.entry_edge_threshold_selection(
        strategy.build_simulation_inputs(material["xy"], asset["bars_1m"], material["oos_predictions"]))
    by_fold, skill_by_fold = selection["validation_by_fold"], material["skill_by_fold"]
    return {
        "columns_by_timeframe": state["columns_by_timeframe"],
        "best_params": state["best_params"],
        **{name: state[name] for name in config.BARRIER_COORDINATE_NAMES},
        "validation": {f"fold_{fold_id}": {
            "relative_logloss_skill": skill_by_fold[fold_id],
            "sharpe": by_fold[fold_id]["sharpe"],
            "cagr": by_fold[fold_id]["cagr"],
            "max_drawdown": by_fold[fold_id]["max_drawdown"],
            "calmar": by_fold[fold_id]["calmar"],
            "profit_factor": by_fold[fold_id]["profit_factor"],
            "trade_count": by_fold[fold_id]["trade_count"]}
            for fold_id in config.VALIDATION_FOLD_IDS},
        "mean_relative_logloss_skill": float(np.mean([skill_by_fold[fold_id] for fold_id in config.VALIDATION_FOLD_IDS])),
        "validation_path": selection["validation_path"],
        "entry_edge_threshold": selection["entry_edge_threshold"],
        "entry_edge_threshold_constraint_met": selection["entry_edge_threshold_constraint_met"],
        strategy.selection_score_key(): selection[strategy.selection_score_key()],
    }


# ---- the one selection: the objective the experiment froze, read per fold and over a whole state -------

def fold_objective(row: dict) -> list[float]:
    """What the gate compares fold by fold — the frozen objective's own fold measure, in the fold table's
    order. The fold is the unit of robustness: a move has to be better on all three, not on average."""
    measure = config.SELECTION_FOLD_MEASURE[config.SELECTION_OBJECTIVE]
    return [row["validation"][f"fold_{fold_id}"][measure] for fold_id in config.VALIDATION_FOLD_IDS]


def state_objective(row: dict) -> tuple:
    """What the ranking maximises over a whole state, most significant first: under the model's own
    objective the mean skill; under the growth rate, the chained validation path's CAGR, then its Calmar
    ratio, then its profit factor. A path that never lost has no profit factor and is the best there is, so
    it sorts first."""
    if config.SELECTION_OBJECTIVE != config.SELECTION_OBJECTIVE_CAGR:
        return (row["mean_relative_logloss_skill"],)
    path = row["validation_path"]
    profit_factor = math.inf if path["profit_factor"] is None else path["profit_factor"]
    return (path["cagr"], path["calmar"], profit_factor)


def is_gate_cleared(row: dict, parent: dict, move: str) -> bool:
    """Whether a child may be kept at all: better than the state it came from on every validation fold, or,
    for a move that shrinks the state, no worse on any of them.

    Under the growth rate the fold measure is a strategy number, so a state whose threshold fell back to the
    grid floor — no point of the grid cleared the trade floor in every fold — is refused before it is
    compared: its numbers stand at a threshold nothing qualified for."""
    if (config.SELECTION_OBJECTIVE == config.SELECTION_OBJECTIVE_CAGR
            and not row["entry_edge_threshold_constraint_met"]):
        return False
    if move == config.COORDINATE_SEARCH_MOVE_BACKWARD:
        return all(child >= own for child, own in zip(fold_objective(row), fold_objective(parent)))
    return all(child > own for child, own in zip(fold_objective(row), fold_objective(parent)))


def ranking_key(trials: list[dict], index: int, timeframes: tuple[str, ...]) -> tuple:
    """The one order the beam and the proposals take: the objective down, then the smaller set, then the
    earlier trial."""
    row = trials[index - 1]
    return (*(-value for value in state_objective(row)),
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
            "mean_relative_logloss_skill": row["mean_relative_logloss_skill"],
            "validation_path": row["validation_path"]}


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
        "validation_path": row["validation_path"],
        "entry_edge_threshold": row["entry_edge_threshold"],
        "entry_edge_threshold_constraint_met": row["entry_edge_threshold_constraint_met"],
        strategy.selection_score_key(): row[strategy.selection_score_key()],
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


def objective_line(row: dict) -> str:
    """A state's objective and its folds, in the words of whichever objective is frozen."""
    measure = config.SELECTION_FOLD_MEASURE[config.SELECTION_OBJECTIVE]
    return (f"{config.SELECTION_OBJECTIVE} {state_objective(row)[0]:+.4f} "
            f"folds {measure} {'/'.join(f'{value:+.4f}' for value in fold_objective(row))} "
            f"trades {'/'.join(str(row['validation'][f'fold_{fold_id}']['trade_count']) for fold_id in config.VALIDATION_FOLD_IDS)}")


def progress_line(ticker: str, state_file: dict, loop: str, family: str, label: str,
                  parent: dict, row: dict) -> str:
    return (f"{ticker} round {state_file['round_count'] + 1} {loop}/{family} {label} "
            f"{config.SELECTION_OBJECTIVE} {state_objective(parent)[0]:+.4f} -> {state_objective(row)[0]:+.4f} "
            f"folds {'/'.join(f'{value:+.4f}' for value in fold_objective(row))}")


def main() -> int:
    args = config.build_ticker_parser(
        "coordinate search on the validation folds under the asset's profile and frozen parameters; resumes"
    ).parse_args()

    for ticker in config.parse_tickers(args.tickers):
        profile = dataset.load_json(config.coordinate_search_profile_json(ticker))
        best = dataset.load_json(config.parameters_json(ticker))["hyperparameter_search_result"]["best_params"]
        cat = dataset.load_catalogue(ticker)
        timeframes = config.timeframes(cat)
        catalogue_values, decision_grids = dataset.load_feature_material(ticker, cat, timeframes)
        active_columns = dataset.load_feature_columns(ticker, cat)
        active_barriers = dataset.load_barriers(ticker)
        xy = dataset.build_xy(cat, timeframes, catalogue_values, decision_grids,
                              dataset.load_label_events(ticker, cat), active_columns, active_barriers)
        asset = {"xy": xy, "catalogue": cat, "timeframes": timeframes,
                 "catalogue_values": catalogue_values, "decision_grids": decision_grids,
                 "label_inputs": labels.load_label_inputs(ticker, cat),
                 "bars_1m": strategy.load_bars_1m(ticker), "champion_by_fold": None}
        # how a state is materialised, handed to the coordinates that need it — the hyper-parameter loop
        # runs a study on one state's own X and Y, and knows nothing else about how they are built
        asset["xy_for"] = lambda state: xy_for_state(asset, state)

        active_state = start_state({"start_columns_by_timeframe": None}, active_columns, active_barriers, best, timeframes)
        inputs = dataset.to_json_safe(build_search_inputs(best, active_columns, active_barriers, cat, profile))

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
            row.update(barrier_search.to_barrier(row))
            trial_index_by_state[state_key(row, timeframes)] = index
        if state_file["search_converged"]:
            print(f"{ticker}: the search converged after {state_file['round_count']} rounds and {len(trials)} "
                  f"trials — {len(state_file['proposals'])} proposals in {path.name}", flush=True)
            continue

        def score(child: dict, loop: str | None, family: str | None, move: str | None,
                  parent: int | None, rebuild: str, inherited: dict | None) -> int:
            """The trial index of a state: its earlier trial's when it was scored before, else a new trial
            scored now. The counters advance at the end of a round, so a trial of the round in flight
            carries the number that round will take."""
            key = state_key(child, timeframes)
            if key in trial_index_by_state:
                return trial_index_by_state[key]
            row = trial_result(asset, child, state_material(asset, child, rebuild, inherited))
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
            start = start_state(profile, active_columns, active_barriers, best, timeframes)
            index = score(start, None, None, None, None, config.REBUILD_FITS, None)
            print(f"{ticker} start state {objective_line(trials[index - 1])}", flush=True)
        # trial 1 is the state the search started from — the champion until a family keeps a move. The beam
        # in flight is a local: what the file carries is the beam the last round ended on, because the round
        # is the unit of resume and a replay has to start its round where the interrupted one started it
        beam = state_file["beam"] or [state_file["champion_trial"] or 1]
        state_file["champion_trial"] = state_file["champion_trial"] or beam[0]

        while not state_file["search_converged"]:
            round_number = state_file["round_count"] + 1
            # what this round accepted, kept aside until it ends: a round replayed after an interrupt walks
            # its families again, and the file's path must hold each expansion once, not once per attempt
            round_accepted, round_path = False, []
            for loop in profile["loops"]:
                for family in LOOP_MODULES[loop].FAMILIES:
                    children = []
                    for parent in beam:
                        parent_row = trials[parent - 1]
                        parent_state = to_state(parent_row, timeframes)
                        # the champion a study inside this loop has to beat, fold by fold
                        asset["champion_by_fold"] = {fold_id: parent_row["validation"][f"fold_{fold_id}"]
                                                     for fold_id in config.VALIDATION_FOLD_IDS}
                        inherited = None      # the parent's own material, built only if a child inherits it
                        for move, label, child, rebuild in LOOP_MODULES[loop].moves(
                                parent_state, asset, profile, family):
                            if rebuild == config.REBUILD_BACKTEST and inherited is None:
                                inherited = state_material(asset, parent_state, config.REBUILD_FITS, None)
                            index = score(child, loop, family, move, parent, rebuild, inherited)
                            print(progress_line(ticker, state_file, loop, family, label,
                                                parent_row, trials[index - 1]), flush=True)
                            if is_gate_cleared(trials[index - 1], parent_row, move):
                                children.append(index)
                    if children:
                        beam = top_beam(children, trials, timeframes)
                        round_accepted = True
                        round_path.append(path_entry(state_file, loop, family, beam))
            # the counters, the beam and the champion move together at the round's end: a trial written in
            # flight carries the round it belongs to, and a run interrupted inside a round resumes at the
            # top of that round, every state it already scored a cache hit
            state_file["path"].extend(round_path)
            state_file["beam"] = list(beam)
            state_file["champion_trial"] = beam[0]
            state_file["pass_count_by_loop"] = {loop: round_number for loop in profile["loops"]}
            state_file["round_count"] = round_number
            state_file["search_converged"] = not round_accepted
            write_state(ticker, state_file, active_state, timeframes)

        champion_row = trials[state_file["champion_trial"] - 1]
        print(f"{ticker} {path.name}: converged after {state_file['round_count']} rounds and {len(trials)} trials, "
              f"champion {objective_line(champion_row)} "
              f"({feature_set_search.column_count(champion_row['columns_by_timeframe'], timeframes)} columns), "
              f"{len(state_file['proposals'])} proposals", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
