"""Coordinate search on the validation folds under the asset's profile, selecting on the model's own
validation objective: a move is kept only where it is better than the state it came from on **every**
validation fold — strictly for a move that grows the state, at no worse for one that shrinks it.

A **round** is `config.ROUND_SCHEDULE` read in order: a table of (loop, family) pairs, one line per
expansion the round makes. Each **family** expands the beam once and is seeded by the beam the family
before it left, so a forward move and a backward move over one coordinate are two lines of one round and
not two rounds. A profile searches the loops it names and the round skips the rest. A round that keeps
nothing is convergence, and the state it stopped at is coordinate-wise locally optimal, never a global
optimum.

Two files hold what the search knows. `<TICKER>_coordinate_search_trials.jsonl` is the ledger: one scored
state a line, appended and never rewritten, the line's number the trial's index. `<TICKER>_coordinate_search.json`
is where the search stood when a round began — what it was conditioned on, its beam, its champion, its path
and its proposals — written at the top of a round and nowhere else, so it is on disk before the ledger's
first line. An interrupted run therefore resumes at the top of its round without a refit, wherever it was
stopped, the lines that round already wrote being cache hits; and a finished run is read, not rewritten.

Promotes nothing: the proposals are read by a hand and copied by coordinate_search_promote."""

from __future__ import annotations

import collections
import json
import math

import numpy as np

from . import barrier_search, config, dataset, feature_set_search, hpo, labels, model, strategy, train

# one module per coordinate — the token a profile's `loops` names, the module that knows its moves and the
# families it expands them in. A generator answers with the candidates it offers and, under
# `asset["trial_count_drawn"]`, with how many points it put through a fit to find them: for a generator that
# enumerates a grid those are the same points, and the core sees them as ledger lines; for one that runs a
# study inside itself they are not, and the count would otherwise be invisible to every reader
LOOP_MODULES = {config.COORDINATE_SEARCH_LOOP_BARRIER: barrier_search,
                config.COORDINATE_SEARCH_LOOP_FEATURE_SET: feature_set_search,
                config.COORDINATE_SEARCH_LOOP_HPO: hpo}


def theta(row: dict) -> dict:
    """The state a trial holds, by itself: the columns of the set, the barrier geometry and the
    hyper-parameter point. A trial's row is this and the numbers it earned."""
    return {"columns_by_timeframe": row["columns_by_timeframe"],
            "best_params": row["best_params"],
            **{name: row[name] for name in config.BARRIER_COORDINATE_NAMES}}


def state_key(state: dict) -> str:
    """A state as the scored-trial index keys it — its own canonical text. A state is written the way the
    artifacts carry it, so a state read back off disk keys the same as the one that wrote it, with no shape
    to repair first. Every value is a string, a whole number or a multiple of a quarter, so the equality is
    exact and asks for no tolerance."""
    return json.dumps(state, sort_keys=True, separators=(",", ":"))


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
        **{name: selection[name] for name in strategy.SELECTION_EXPOSURE_KEYS},
        strategy.SELECTION_SCORE_KEY: selection[strategy.SELECTION_SCORE_KEY],
    }


# ---- the one selection: the objective the experiment froze, read per fold and over a whole state -------

def fold_objective(row: dict) -> list[float]:
    """What the gate compares fold by fold — each fold's Calmar ratio, in the fold table's order. The fold
    is the unit of robustness: a move has to be better on all three, not on average."""
    return [row["validation"][f"fold_{fold_id}"][config.SELECTION_FOLD_MEASURE]
            for fold_id in config.VALIDATION_FOLD_IDS]


def state_objective(row: dict) -> tuple:
    """What the ranking maximises over a whole state, most significant first: the chained validation path's
    CAGR, then its Calmar ratio, then its profit factor. A path that never lost has no profit factor and is
    the best there is, so it sorts first."""
    path = row["validation_path"]
    profit_factor = math.inf if path["profit_factor"] is None else path["profit_factor"]
    return (path["cagr"], path["calmar"], profit_factor)


def is_gate_cleared(row: dict, parent: dict, move: str) -> bool:
    """Whether a child may be kept at all: better than the state it came from **on the objective and on
    every validation fold**, or, for a move that shrinks the state, no worse on either.

    Two conditions and not one. The folds alone admitted a child that beat its parent on all three fold
    Calmars while the chained path's CAGR — the quantity the search selects on and reports — fell; the
    search then kept a state worse at the thing it was searching for because it was better at the thing
    guarding it. The guard does not get to outvote the objective.

    The fold measure is a strategy number, so a state whose threshold fell back to the grid floor — no point
    of the grid cleared the trade floor in every fold — is refused before it is compared: its numbers stand
    at a threshold nothing qualified for."""
    if not row["entry_edge_threshold_constraint_met"]:
        return False
    objective, parent_objective = state_objective(row)[0], state_objective(parent)[0]
    if move == config.COORDINATE_SEARCH_MOVE_BACKWARD:
        return (objective >= parent_objective
                and all(child >= own for child, own in zip(fold_objective(row), fold_objective(parent))))
    return (objective > parent_objective
            and all(child > own for child, own in zip(fold_objective(row), fold_objective(parent))))


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

def path_entry(trials: list[dict], round_number: int, loop: str, family: str, beam: list[int]) -> dict:
    """One accepted expansion of the research path: which loop and family moved the search, where it landed
    and what the beam held after it."""
    row = trials[beam[0] - 1]
    return {"round": round_number, "loop": loop, "family": family,
            "trial_index": beam[0], "beam": list(beam), "move": row["move"],
            "mean_relative_logloss_skill": row["mean_relative_logloss_skill"],
            "validation_path": row["validation_path"]}


def proposals_block(trials: list[dict], active_state: dict, champion_trial_index: int,
                    timeframes: tuple[str, ...]) -> list[dict]:
    """The states a hand may promote: the champion the search accepted first, then the trials no validation
    fold scores below the state the search started from, by the ranking key. A state worse on any fold is
    never proposed, and neither is one whose threshold fell back to the grid floor — a fallback row wears
    the numbers of a threshold nothing qualified for, and against a baseline that lost it could rank."""
    active_key = state_key(active_state)
    qualifiers = [(index, row) for index, row in enumerate(trials, start=1)
                  if row["entry_edge_threshold_constraint_met"]
                  and state_key(theta(row)) != active_key
                  and all(child >= own for child, own in zip(fold_objective(row), fold_objective(trials[0])))]
    # the champion first — the state the search itself accepted, move by move — then the rest by the key
    ranked = sorted(qualifiers, key=lambda item: (item[0] != champion_trial_index,
                                                  *ranking_key(trials, item[0], timeframes)))
    active = active_state["columns_by_timeframe"]
    return [{
        "proposal": rank,
        "trial_index": index,
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
        strategy.SELECTION_SCORE_KEY: row[strategy.SELECTION_SCORE_KEY],
    } for rank, (index, row) in enumerate(ranked[:config.COORDINATE_SEARCH_PROPOSAL_COUNT], start=1)]


def write_round_state(ticker: str, state_file: dict, trials: list[dict], active_state: dict,
                      timeframes: tuple[str, ...]) -> None:
    """Where the search stood when the round about to run began — the one place this file is written.

    Written at the top of a round, so it exists before the ledger's first line and every line the ledger
    holds has, on disk, the experiment it belongs to; the write that records a finished search is this same
    write one iteration later. The trials are the ledger beside it, appended a line at a time, so the state
    is a fixed handful of keys and the proposals are derived once a round rather than once a trial. That is
    what makes the search's own record grow with what it gains: the ledger by one line, this file not at
    all."""
    state_file["proposals"] = proposals_block(trials, active_state, state_file["champion_trial_index"] or 1, timeframes)
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
        "selection": {"beam_width": config.COORDINATE_SEARCH_BEAM_WIDTH},
    }


def start_state(profile: dict, active_columns_by_timeframe: dict, active_barriers: dict,
                best_params: dict, timeframes: tuple[str, ...]) -> dict:
    """The state a search starts from: the columns the profile names, else the asset's own set, with the
    asset's own barrier geometry and the parameters it holds fixed."""
    columns = profile["start_columns_by_timeframe"] or active_columns_by_timeframe
    return {"columns_by_timeframe": {timeframe: list(columns[timeframe]) for timeframe in timeframes},
            "best_params": best_params,
            **{name: active_barriers[name] for name in config.BARRIER_COORDINATE_NAMES}}


def objective_line(row: dict) -> str:
    """A state's objective and the folds the gate reads."""
    return (f"cagr {state_objective(row)[0]:+.4f} "
            f"folds {config.SELECTION_FOLD_MEASURE} {'/'.join(f'{value:+.4f}' for value in fold_objective(row))} "
            f"trades {'/'.join(str(row['validation'][f'fold_{fold_id}']['trade_count']) for fold_id in config.VALIDATION_FOLD_IDS)}")


def progress_line(ticker: str, state_file: dict, loop: str, family: str, label: str,
                  parent: dict, row: dict) -> str:
    return (f"{ticker} round {state_file['round_count'] + 1} {loop}/{family} {label} "
            f"cagr {state_objective(parent)[0]:+.4f} -> {state_objective(row)[0]:+.4f} "
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
        # a profile is drafted by a hand and the catalogue is generated: a column named here and absent there
        # is a typo, and it would otherwise be silence — the forward family admits by membership, so an
        # unknown name simply never matches and the search runs a smaller space than the profile asked for
        unknown = feature_set_search.unknown_columns(profile["columns_admitted_by_timeframe"],
                                                    cat["columns_by_timeframe"], timeframes)
        if unknown:
            raise ValueError(f"profile admits columns the catalogue does not offer: {unknown}")
        catalogue_values, decision_grids = dataset.load_feature_material(ticker, cat, timeframes)
        active_columns = dataset.load_feature_columns(ticker, cat)
        active_barriers = dataset.load_barriers(ticker)
        xy = dataset.build_xy(cat, timeframes, catalogue_values, decision_grids,
                              dataset.load_label_events(ticker, cat), active_columns, active_barriers)
        asset = {"ticker": ticker, "round": None, "champion_objective": None,
                 "xy": xy, "catalogue": cat, "timeframes": timeframes,
                 "catalogue_values": catalogue_values, "decision_grids": decision_grids,
                 "label_inputs": labels.load_label_inputs(ticker, cat),
                 "bars_1m": strategy.load_bars_1m(ticker), "champion_by_fold": None}
        # how a state is materialised, handed to the coordinates that need it — the hyper-parameter loop
        # runs a study on one state's own X and Y, and knows nothing else about how they are built
        asset["xy_for"] = lambda state: xy_for_state(asset, state)

        active_state = start_state({"start_columns_by_timeframe": None}, active_columns, active_barriers, best, timeframes)
        inputs = dataset.to_json_safe(build_search_inputs(best, active_columns, active_barriers, cat, profile))

        # the state: the recorded run when its inputs are the inputs of this one, else a fresh state and a
        # fresh ledger — a trial of another experiment is not a cache hit for this one
        path, ledger = config.coordinate_search_json(ticker), config.coordinate_search_trials_jsonl(ticker)
        state_file = dataset.load_json(path) if path.exists() else None
        if state_file is None or state_file["inputs"] != inputs:
            state_file = {"inputs": inputs, "beam": [], "champion_trial_index": None, "round_count": 0,
                          "search_converged": False, "path": [], "trial_count_by_loop": {}}
            ledger.unlink(missing_ok=True)
        # every line of the ledger, the ones a round interrupted after the last boundary wrote among them:
        # those are cache hits, because the round they belong to starts again at its first family
        trials = dataset.load_jsonl(ledger) if ledger.exists() else []
        trial_index_by_state = {state_key(theta(row)): index
                                for index, row in enumerate(trials, start=1)}
        # what the loops drew inside themselves, recovered rather than carried in a second key: the state's
        # count is the ledger's lines plus those draws, and the lines are countable, so the difference is the
        # draws. A fresh state carries neither and the difference is empty
        drawn_by_loop = (collections.Counter(state_file["trial_count_by_loop"])
                         - collections.Counter(row["loop"] for row in trials if row["loop"]))
        if state_file["search_converged"]:
            print(f"{ticker}: the search converged after {state_file['round_count']} rounds and {len(trials)} "
                  f"trials — {len(state_file['proposals'])} proposals in {path.name}", flush=True)
            continue

        def score(child: dict, loop: str | None, family: str | None, move: str | None,
                  parent: int | None, rebuild: str, inherited: dict | None) -> int:
            """The trial index of a state: its earlier trial's when it was scored before, else a new trial
            scored now. The counters advance at the end of a round, so a trial of the round in flight
            carries the number that round will take."""
            key = state_key(child)
            if key in trial_index_by_state:
                return trial_index_by_state[key]
            row = {**trial_result(asset, child, state_material(asset, child, rebuild, inherited)),
                   "loop": loop, "family": family, "move": move,
                   "round": state_file["round_count"] + 1 if move else 0,
                   "parent_trial_index": parent}
            dataset.append_jsonl(ledger, row)                 # the ledger grows by one line, and by nothing else
            trials.append(dataset.to_json_safe(row))          # held as the ledger will read it back
            trial_index_by_state[key] = len(trials)
            return len(trials)

        # The state is written at the top of a round, and it says where the search stood when that round
        # began — which, for the first round, is before anything has been scored. So the state file exists
        # before the ledger's first line, and every line the ledger holds has, on disk, the experiment it
        # belongs to: a run stopped anywhere, the baseline trial included, resumes instead of starting over.
        # The write that ends the search is the same write, one iteration later, which is why there is one
        # call and not two.
        while True:
            write_round_state(ticker, state_file, trials, active_state, timeframes)
            if state_file["search_converged"]:
                break
            if not trials:
                start = start_state(profile, active_columns, active_barriers, best, timeframes)
                index = score(start, None, None, None, None, config.REBUILD_FITS, None)
                print(f"{ticker} start state {objective_line(trials[index - 1])}", flush=True)
            # trial 1 is the state the search started from — the champion until a family keeps a move. The
            # beam in flight is a local, read back from the file at the top of every round, because the
            # round is the unit of resume and a replay has to start where the interrupted round started
            beam = state_file["beam"] or [state_file["champion_trial_index"] or 1]
            round_number = state_file["round_count"] + 1
            # what this round accepted, kept aside until it ends: a round replayed after an interrupt walks
            # its families again, and the file's path must hold each expansion once, not once per attempt
            round_accepted, round_path, round_drawn = False, [], collections.Counter()
            asset["round"] = round_number      # a generator that keeps its own ledger says which round it drew in
            # a round is its schedule, read in order; a profile searches the loops it names and skips the rest
            for loop, family in config.ROUND_SCHEDULE:
                if loop not in profile["loops"]:
                    continue
                children = []
                for parent in beam:
                    parent_row = trials[parent - 1]
                    parent_state = theta(parent_row)
                    # the champion a study inside this loop has to beat, fold by fold
                    asset["champion_by_fold"] = {fold_id: parent_row["validation"][f"fold_{fold_id}"]
                                                 for fold_id in config.VALIDATION_FOLD_IDS}
                    # and the objective it stands at, so a generator that offers one candidate can ask the
                    # gate's own question of its own points instead of offering one the gate will refuse
                    asset["champion_objective"] = state_objective(parent_row)[0]
                    inherited = None      # the parent's own material, built only if a child inherits it
                    # the fits a generator spends inside itself are its own to count: zeroed before it is
                    # asked and read back after, so a generator that spends none reports none without saying so
                    asset["trial_count_drawn"] = 0
                    candidates = LOOP_MODULES[loop].moves(parent_state, asset, profile, family)
                    round_drawn[loop] += asset["trial_count_drawn"]
                    for move, label, child, rebuild in candidates:
                        if rebuild == config.REBUILD_BACKTEST and inherited is None:
                            inherited = state_material(asset, parent_state, config.REBUILD_FITS, None)
                        index = score(child, loop, family, move, parent, rebuild, inherited)
                        print(progress_line(ticker, state_file, loop, family, label,
                                            parent_row, trials[index - 1]), flush=True)
                        if is_gate_cleared(trials[index - 1], parent_row, move):
                            children.append(index)
                # the beam the family leaves is the best of its children **and the parents it came from**:
                # a family that finds nothing better keeps what it had, and one that improves only the third
                # member does not thereby unseat the first. Ranking children alone let a family replace a
                # beam wholesale with states that had each beaten their own parent and none of which had
                # beaten the champion — the path could then descend, which is the one thing it must not do
                previous_beam = beam
                beam = top_beam(children + beam, trials, timeframes)
                if beam != previous_beam:
                    round_accepted = True
                    round_path.append(path_entry(trials, round_number, loop, family, beam))
            # the counters, the beam and the champion move together at the round's end: a trial written in
            # flight carries the round it belongs to, and a run interrupted inside a round resumes at the
            # top of that round, every state it already scored a cache hit
            state_file["path"].extend(round_path)
            # one number per loop, written where the search knows it and copied by everything that shows it:
            # the ledger's lines for a loop that enumerates a grid, plus the points a loop that runs a study
            # inside itself drew and never turned into lines
            drawn_by_loop += round_drawn
            state_file["trial_count_by_loop"] = dict(
                collections.Counter(row["loop"] for row in trials if row["loop"]) + drawn_by_loop)
            state_file["beam"] = list(beam)
            state_file["champion_trial_index"] = beam[0]
            state_file["round_count"] = round_number
            state_file["search_converged"] = not round_accepted

        champion_row = trials[state_file["champion_trial_index"] - 1]
        print(f"{ticker} {path.name}: converged after {state_file['round_count']} rounds and {len(trials)} trials, "
              f"champion {objective_line(champion_row)} "
              f"({feature_set_search.column_count(champion_row['columns_by_timeframe'], timeframes)} columns), "
              f"{len(state_file['proposals'])} proposals", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
