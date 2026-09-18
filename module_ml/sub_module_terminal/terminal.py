"""The ML terminal — the ML module's text-based user interface (TUI): each asset's artifacts and the search recorded
for it, then one action a hand chooses in the menu — a stage of the chain started through `make` (labels, hpo, train,
strategy, status), or one of the coordinate search's own: draft the profile, start the search, read its tables, or
promote a proposal — its forms and its result, drawn by tui.py to module_skills/skill_tui_designer.md; then it
closes.

It computes nothing: it reads the feature layer's contract and this module's own artifacts and search state as
JSON, writes the one file `<TICKER>_coordinate_search_profile.json`, and starts every stage through `make` — the
Makefile is where a container, a tmux session and the order of the chain are named.

keys:
  Enter takes the option under the cursor; x toggles a column, a coordinate or a loop; Esc cancels and writes
  nothing (exit 0); Ctrl-C ends the TUI (exit 130), and a stage or a search already started stays.

output is plain — state words in brackets, no colour, no symbol, no border — when NO_COLOR is set and not empty,
TERM is dumb or standard output is not a terminal; the words, the order and the counts are the same in both.

exit codes:
  0 the action done, or cancelled with nothing written; 1 a failure, named last on stderr; 2 an unknown
  argument; 130 Ctrl-C

examples:
  make ml-terminal                  the TUI over the basket (at the workspace) or over ASSET (in this repository)
  make ml-terminal ASSET=BTC        the TUI over one asset
  NO_COLOR=1 make ml-terminal       the TUI in plain output
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys

from . import config, tui
from .. import config as ml_config

DRAFT_STEPS = ["action", "columns to admit", "start state", "coordinates to search", "loops", "plan"]
PROMOTE_STEPS = ["action", "proposal", "plan"]
STATE_COLUMNS = ("asset", "catalogue", "labels", "parameters", "model", "strategy", "profile", "trials")
STATE_COLUMNS_DROP_ORDER = ("trials", "profile", "strategy", "model", "parameters", "labels")
PROPOSAL_COLUMNS = ("#", "trial", "coordinates moved", "path CAGR", "path Calmar", "path maxDD", "trades")
PROPOSAL_COLUMNS_DROP_ORDER = ("path maxDD", "trades", "path Calmar", "coordinates moved")
PATH_COLUMNS = ("#", "round", "loop", "family", "trial", "path CAGR", "path Calmar", "path maxDD", "trades")
PATH_COLUMNS_DROP_ORDER = ("trades", "path maxDD", "path Calmar", "family")
SEARCH_SESSIONS = ({"session": "detached", "target": config.SEARCH_DETACHED_TARGET},
                   {"session": "foreground", "target": config.SEARCH_TARGET})


# ---- the screens' own rows ------------------------------------------------------------------------------

def _option_rows(*options: str) -> list[dict]:
    return [{"option": option} for option in options]


def _step_rows(steps: list[str], chosen: dict[str, str]) -> list[dict]:
    """The action's steps in order: each answered DONE with its choice, the first unanswered CURRENT, the rest PENDING."""
    current = next(step for step in steps if step not in chosen)
    return [{"step": step, "state": tui.state_label("DONE" if step in chosen else "CURRENT" if step == current
                                                    else "PENDING"),
             "choice": chosen[step] if step in chosen else "select now" if step == current else "—"} for step in steps]


def _step_answer(steps: list[str], chosen: dict[str, str], rows: list[dict], value_column: str,
                 drop_order: tuple[str, ...] = (), selected: list[str] | None = None) -> str | None:
    """The answer to the action's current step under the steps table; a step of one option draws nothing, gum
    answering it, and the next steps table shows it DONE."""
    step = next(step for step in steps if step not in chosen)
    if len(rows) > 1:
        tui.gum_table(("step", "state", "choice"), _step_rows(steps, chosen))
        print()
    return tui.gum_choose(step, rows, value_column, drop_order, selected)


def _cancelled_exit_code() -> int:
    """Esc, cancel or quit: one line, nothing written, exit 0."""
    print(f"{tui.state_label('CANCELLED')}  nothing written")
    return 0


def _failure_exit_code(what: str, where: str, why: str | None, next_action: str) -> int:
    """A failure as the run's last block, on stderr: exit 1."""
    tui.gum_style(tui.error_lines(what, where, why, next_action), "ERROR", sys.stderr)
    return 1


def _make(target: str, *variables: str) -> int:
    """The one call of make: its lines reach this terminal as they come, and its exit code is the answer. The
    Makefile is where a stage, a container and a tmux session are named (AGENTS.md § Canonical vocabulary)."""
    command = ("make", target, *variables)
    print(f"{tui.state_label('CURRENT')}  {shlex.join(command)}", flush=True)
    return subprocess.run(command).returncode


def _profile_state(profile: dict | None, search: dict | None) -> str:
    """Where the asset's profile stands against the search recorded under it — the one comparison this terminal
    makes, on parsed objects and not on bytes: the search records the profile it was run with, verbatim."""
    if profile is None:
        return "not drafted"
    if search is None:
        return "no search"
    return "matches the search" if search["inputs"]["profile"] == profile else "differs from the search"


def _asset_files(ticker: str) -> tuple[dict | None, dict | None, dict | None]:
    """The three files of one asset this terminal reads as objects — the contract, the profile and the search — each
    None where the file is not there."""
    catalogue_path = ml_config.catalogue_json(ticker)
    profile_path, search_path = ml_config.coordinate_search_profile_json(ticker), ml_config.coordinate_search_json(ticker)
    return (config.load_json(catalogue_path) if catalogue_path.exists() else None,
            config.load_json(profile_path) if profile_path.exists() else None,
            config.load_json(search_path) if search_path.exists() else None)


def _trial_rows(ticker: str) -> list[dict]:
    """The search's ledger, line by line — the trials, where the state file holds where the search stands."""
    ledger = ml_config.coordinate_search_trials_jsonl(ticker)
    return config.load_jsonl(ledger) if ledger.exists() else []


def _present(path) -> str:
    return "yes" if path.exists() else "no"


def _asset_rows(tickers: list[str]) -> list[dict]:
    """One row per asset — which of its files stand, where its profile stands and how many trials its ledger holds;
    every cell a value as it stands, `—` where a file that would name it is not there."""
    rows = []
    for ticker in tickers:
        catalogue, profile, search = _asset_files(ticker)
        trials = _trial_rows(ticker)
        rows.append({"asset": ticker,
                     "catalogue": "yes" if catalogue else "no",
                     "labels": _present(ml_config.label_events_parquet(ticker, catalogue)) if catalogue else "—",
                     "parameters": _present(ml_config.parameters_json(ticker)),
                     "model": _present(ml_config.model_evaluation_json(ticker)),
                     "strategy": _present(ml_config.strategy_evaluation_json(ticker)),
                     "profile": _profile_state(profile, search),
                     "trials": len(trials) if trials else "—"})
    return rows


def _state_rows(ticker: str, profile: dict | None, search: dict | None,
                trials: list[dict]) -> list[dict]:
    """What the asset holds, one fact a row — every cell the file's own value, never an age or a share."""
    rows = [{"parameter": "asset", "value": ticker},
            {"parameter": "profile", "value": _profile_state(profile, search)}]
    if profile is not None:
        rows.append({"parameter": "coordinates searched",
                     "value": f"{sum(len(grid) > 1 for grid in profile['grid_by_coordinate'].values())} of {len(config.GRID_BY_COORDINATE_DEFAULT)}"})
        rows.append({"parameter": "loops", "value": " ".join(profile["loops"]) or "—"})
    if search is None:
        rows.append({"parameter": "search", "value": "none"})
        return rows
    # the search counted this at a round boundary; the terminal shows it and adds nothing to it
    by_loop = search["trial_count_by_loop"]
    rows += [{"parameter": "search", "value": f"{len(trials)} trials in {search['round_count']} rounds"},
             {"parameter": "trials by loop",
              "value": " ".join(f"{loop} {count}" for loop, count in sorted(by_loop.items())) or "—"},
             {"parameter": "converged", "value": "yes" if search["search_converged"] else "no"},
             {"parameter": "champion trial", "value": search["champion_trial_index"] or "—"},
             {"parameter": "proposals", "value": len(search["proposals"])}]
    return rows


def _number(value, digits: int = 4) -> str:
    return "—" if value is None else f"{value:+.{digits}f}"


def _path_block_cells(block: dict) -> dict:
    return {"path CAGR": _number(block["cagr"]), "path Calmar": _number(block["calmar"], 2),
            "path maxDD": _number(block["max_drawdown"], 4), "trades": block["trade_count"]}


def _proposal_rows(search: dict, trials: list[dict]) -> list[dict]:
    """The proposals, each read off the ledger line its trial index names — the state file holds the rank and
    the index, and no number of the trial."""
    return [{"#": proposal["proposal"], "trial": proposal["trial_index"],
             "coordinates moved": _moved(trials[proposal["trial_index"] - 1], search),
             **_path_block_cells(trials[proposal["trial_index"] - 1]["validation_path"])}
            for proposal in search["proposals"]]


def _path_rows(search: dict, trials: list[dict]) -> list[dict]:
    return [{"#": number, "round": entry["round"], "loop": entry["loop"], "family": entry["family"],
             "trial": entry["trial_index"], **_path_block_cells(trials[entry["trial_index"] - 1]["validation_path"])}
            for number, entry in enumerate(search["path"], start=1)]


def _moved(trial: dict, search: dict) -> str:
    """What one trial changes against the asset's own state the search was run on, as its inputs record it — the
    columns it holds that the state does not and the ones it drops, and each barrier coordinate whose value is not
    the state's. Membership and equality on the two files' own values: no number is computed."""
    active_columns, active_barriers = (search["inputs"]["active_columns_by_timeframe"],
                                       search["inputs"]["active_barriers"])
    columns = [f"+{name}_{timeframe}" for timeframe, names in sorted(trial["columns_by_timeframe"].items())
               for name in names if name not in active_columns[timeframe]]
    columns += [f"-{name}_{timeframe}" for timeframe, names in sorted(active_columns.items())
                for name in names if name not in trial["columns_by_timeframe"][timeframe]]
    barriers = [f"{name} {trial[name]}" for name in sorted(config.GRID_BY_COORDINATE_DEFAULT)
                if trial[name] != active_barriers[name]]
    return " ".join(columns + barriers) or "—"


# ---- the actions ----------------------------------------------------------------------------------------

def _write_stage(ticker: str, stage: str) -> int:
    """One stage of this module's chain for one asset, started through make after the plan and its gate."""
    target = f"{config.MODULE_TOKEN}-{stage}"
    tui.gum_table(("parameter", "value"), [
        {"parameter": "asset", "value": ticker},
        {"parameter": "stage", "value": stage},
        {"parameter": "writes", "value": config.WRITES_BY_STAGE[stage].replace("<TICKER>", ticker)}])
    print(f"command         {shlex.join(('make', target, f'ASSET={ticker}'))}")
    print()
    decision = tui.gum_choose(f"{stage} {ticker}?", _option_rows(stage, "cancel"), "option")
    if decision != stage:
        return _cancelled_exit_code()
    print()
    code = _make(target, f"ASSET={ticker}")
    print()
    if code:
        return _failure_exit_code(f"{target} of {ticker} ended with exit {code}",
                                  shlex.join(("make", target, f"ASSET={ticker}")), f"make exited with {code}",
                                  "read make's lines above")
    tui.gum_style([f"{tui.state_label('DONE')}  {target} of {ticker} done"], "DONE")
    return 0


def _pinned_point(profile: dict | None, name: str):
    """Where an unsearched coordinate is pinned: the point the profile already stands on — the first of the
    grid it holds — or the experiment's frozen geometry when a hand is drafting the first profile."""
    grid = (profile or {}).get("grid_by_coordinate", {}).get(name)
    return grid[0] if grid else ml_config.START_BY_COORDINATE_DEFAULT[name]


def _write_search_profile(ticker: str, catalogue: dict | None, profile: dict | None, search: dict | None) -> int:
    """Draft the asset's search profile: which columns the search may admit, which state it starts from, which
    coordinates it moves and which loops a round runs. The grids are the one preset — another grid is a hand's
    edit of the file, which is what a drafted artifact permits."""
    if catalogue is None:
        return _failure_exit_code(f"{ticker} has no feature contract", ml_config.catalogue_json(ticker).name, None,
                                  f"make features-catalogue ASSET={ticker} first")
    while True:
        chosen = {"action": "draft"}
        timeframes = [entry["timeframe"] for entry in catalogue["timeframes"]]
        column_rows = [{"column": f"{name}_{timeframe}", "timeframe": timeframe, "definition": name}
                       for timeframe in timeframes for name in catalogue["columns_by_timeframe"][timeframe]]
        admitted = ([f"{name}_{timeframe}" for timeframe, names in profile["columns_admitted_by_timeframe"].items()
                     for name in names] if profile else [row["column"] for row in column_rows])
        answer = _step_answer(DRAFT_STEPS, chosen, column_rows, "column", ("definition", "timeframe"),
                              selected=admitted)
        if answer in (None, ""):
            return _cancelled_exit_code()
        admitted = answer.splitlines()
        chosen["columns to admit"] = f"{len(admitted)} of {len(column_rows)}"

        start_rows = [{"start state": "the asset's own", "value": "null"}]
        if search is not None and search["champion_trial_index"]:
            start_rows.append({"start state": "the recorded search's champion", "value": "champion"})
        answer = _step_answer(DRAFT_STEPS, chosen, start_rows, "value")
        if answer in (None, ""):
            return _cancelled_exit_code()
        start_columns = (None if answer == "null" else
                         _trial_rows(ticker)[search["champion_trial_index"] - 1]["columns_by_timeframe"])
        chosen["start state"] = next(row["start state"] for row in start_rows if row["value"] == answer)

        coordinate_rows = [{"coordinate": name, "grid": ", ".join(str(point) for point in grid),
                            "points": len(grid)}
                           for name, grid in sorted(config.GRID_BY_COORDINATE_DEFAULT.items())]
        searched = (sorted(name for name, grid in profile["grid_by_coordinate"].items() if len(grid) > 1)
                    if profile else sorted(config.GRID_BY_COORDINATE_DEFAULT))
        answer = _step_answer(DRAFT_STEPS, chosen, coordinate_rows, "coordinate", ("points", "grid"),
                              selected=searched)
        if answer is None:
            return _cancelled_exit_code()
        searched = answer.splitlines() if answer else []
        chosen["coordinates to search"] = f"{len(searched)} of {len(coordinate_rows)}"

        loop_rows = [{"loop": loop} for loop in ml_config.COORDINATE_SEARCH_ROUND_LOOPS]
        loops = profile["loops"] if profile else list(ml_config.COORDINATE_SEARCH_ROUND_LOOPS)
        answer = _step_answer(DRAFT_STEPS, chosen, loop_rows, "loop", selected=loops)
        if answer is None:
            return _cancelled_exit_code()
        loops = [loop for loop in ml_config.COORDINATE_SEARCH_ROUND_LOOPS if loop in answer.splitlines()]
        chosen["loops"] = " ".join(loops) or "—"

        drafted = {
            "columns_admitted_by_timeframe": {
                timeframe: [name for name in catalogue["columns_by_timeframe"][timeframe]
                            if f"{name}_{timeframe}" in admitted]
                for timeframe in timeframes},
            # every coordinate, always: a profile that omits one leaves the search reading a key that is not
            # there, and a coordinate a hand did not tick is not a coordinate that stopped existing — it is
            # one pinned to where it stands. Its grid is that single point, which the kernel already handles,
            # because a one-point grid has no neighbour and a family with no neighbour makes no move
            "grid_by_coordinate": {name: (list(grid) if name in searched else [_pinned_point(profile, name)])
                                   for name, grid in sorted(config.GRID_BY_COORDINATE_DEFAULT.items())},
            "loops": loops,
            "start_columns_by_timeframe": start_columns,
        }
        path = ml_config.coordinate_search_profile_json(ticker)
        changes = [{"parameter": key, "now": _short(profile.get(key) if profile else None), "after": _short(value)}
                   for key, value in sorted(drafted.items())
                   if not profile or profile.get(key) != value]
        tui.gum_table(("step", "state", "choice"), _step_rows(DRAFT_STEPS, chosen))
        print()
        if changes:
            tui.gum_table(("parameter", "now", "after"), changes)
        else:
            print("no profile changes")
        print()
        if search is not None and drafted != search["inputs"]["profile"]:
            print(f"{tui.state_label('WARN')}  the recorded search was run under another profile — the next "
                  f"search starts a new state and overwrites {ml_config.coordinate_search_json(ticker).name}")
            print()
        answer = tui.gum_choose(f"draft {path.name}?",
                                _option_rows(*(("draft",) if changes else ()), "back", "cancel"), "option")
        if answer == "back":
            continue
        if answer != "draft":
            return _cancelled_exit_code()
        config.write_json(path, drafted)
        print()
        tui.gum_style([f"{tui.state_label('DONE')}  drafted {path.name} · {len(admitted)} columns admitted · "
                       f"{len(searched)} coordinates · {' '.join(loops) or 'no'} loops"], "DONE")
        return 0


def _short(value) -> str:
    """One profile value on one line: a list by its length, a mapping by its own, everything else as it stands."""
    if value is None:
        return "—"
    if isinstance(value, dict):
        return " ".join(f"{key} {len(value[key]) if isinstance(value[key], list) else value[key]}"
                        for key in sorted(value))
    if isinstance(value, list):
        return " ".join(str(item) for item in value) or "—"
    return str(value)


def _write_coordinate_search(ticker: str, profile: dict | None, search: dict | None) -> int:
    """Start the search, detached in its own tmux session or in the foreground of this screen, through the
    Makefile that names it."""
    path = ml_config.coordinate_search_profile_json(ticker)
    if profile is None:
        return _failure_exit_code("the search cannot start", f"{ticker}: {path.name}",
                                  "the asset has no search profile", "draft one first")
    target = tui.gum_choose("session", list(SEARCH_SESSIONS), "target", ("target",))
    if target in (None, ""):
        return _cancelled_exit_code()
    plan = [{"parameter": "asset", "value": ticker},
            {"parameter": "profile", "value": path.name},
            {"parameter": "coordinates searched",
             "value": f"{sum(len(grid) > 1 for grid in profile['grid_by_coordinate'].values())} of {len(config.GRID_BY_COORDINATE_DEFAULT)}"},
            {"parameter": "loops", "value": " ".join(profile["loops"]) or "—"},
            {"parameter": "session", "value": next(row["session"] for row in SEARCH_SESSIONS if row["target"] == target)},
            {"parameter": "writes", "value": f"{ml_config.coordinate_search_json(ticker).name}, after every scored state"}]
    tui.gum_table(("parameter", "value"), plan)
    print(f"command         {shlex.join(('make', target, f'ASSET={ticker}'))}")
    print()
    if profile["grid_by_coordinate"]:
        tui.gum_table(("coordinate", "grid", "points"),
                      [{"coordinate": name, "grid": ", ".join(str(point) for point in grid), "points": len(grid)}
                       for name, grid in sorted(profile["grid_by_coordinate"].items())], ("points",))
        print()
    if search is not None and search["inputs"]["profile"] != profile:
        print(f"{tui.state_label('WARN')}  the recorded search was run under another profile — this one starts "
              f"a new state and overwrites {ml_config.coordinate_search_json(ticker).name}")
        print()
    answer = tui.gum_choose(f"start the coordinate search of {ticker}?",
                            _option_rows("start", "cancel"), "option")
    if answer != "start":
        return _cancelled_exit_code()
    print()
    code = _make(target, f"ASSET={ticker}")
    print()
    if code:
        return _failure_exit_code(f"the coordinate search of {ticker} did not start",
                                  shlex.join(("make", target, f"ASSET={ticker}")),
                                  f"make exited with {code}", "read make's lines above, then try again")
    tui.gum_style([f"{tui.state_label('DONE')}  the search of {ticker} "
                   f"{'is in its session' if target == config.SEARCH_DETACHED_TARGET else 'ran on this screen'}"], "DONE")
    return 0


def _recorded_search_tables(ticker: str, profile: dict | None, search: dict | None) -> int:
    """Read the recorded search: where it stands, the path it took and the states it proposes. Writes nothing.

    Two files: the state file says where the search stands and names the trials it took and proposes, the ledger
    holds those trials and every number the tables show."""
    if search is None:
        return _failure_exit_code(f"{ticker} has no coordinate search",
                                  ml_config.coordinate_search_json(ticker).name,
                                  "no search has run for this asset", "draft a profile, then start the search")
    trials = _trial_rows(ticker)
    tui.gum_table(("parameter", "value"), _state_rows(ticker, profile, search, trials))
    print()
    if search["path"]:
        tui.gum_table(PATH_COLUMNS, _path_rows(search, trials), PATH_COLUMNS_DROP_ORDER)
    else:
        print("no accepted move")
    print()
    if search["proposals"]:
        tui.gum_table(PROPOSAL_COLUMNS, _proposal_rows(search, trials), PROPOSAL_COLUMNS_DROP_ORDER)
    else:
        print("no proposal")
    return 0


def _write_promoted_proposal(ticker: str, profile: dict | None, search: dict | None) -> int:
    """Promote one proposal into the asset's own state, through the Makefile — which, at the workspace, reruns the
    chain after it."""
    if search is None or not search["proposals"]:
        return _failure_exit_code(f"{ticker} has no proposal to promote",
                                  ml_config.coordinate_search_json(ticker).name,
                                  "no search has run for this asset" if search is None else "the search proposes none",
                                  "start the search, then read its tables")
    chosen = {"action": "promote"}
    trials = _trial_rows(ticker)
    answer = _step_answer(PROMOTE_STEPS, chosen, _proposal_rows(search, trials), "#", PROPOSAL_COLUMNS_DROP_ORDER)
    if answer in (None, ""):
        return _cancelled_exit_code()
    proposal = next(row for row in search["proposals"] if str(row["proposal"]) == answer)
    chosen["proposal"] = answer
    tui.gum_table(("step", "state", "choice"), _step_rows(PROMOTE_STEPS, chosen))
    print()
    tui.gum_table(("parameter", "value"),
                  [{"parameter": "asset", "value": ticker},
                   {"parameter": "proposal", "value": f"{answer} of {len(search['proposals'])}"},
                   {"parameter": "trial", "value": proposal["trial_index"]},
                   {"parameter": "coordinates moved",
                    "value": _moved(trials[proposal["trial_index"] - 1], search)},
                   {"parameter": "writes",
                    "value": f"{ml_config.feature_set_json(ticker).name}, {ml_config.barriers_json(ticker).name}"}])
    print(f"command         {shlex.join(('make', config.PROMOTE_TARGET, f'ASSET={ticker}', f'PROPOSAL={answer}'))}")
    print()
    decision = tui.gum_choose(f"promote proposal {answer} of {ticker}?",
                              _option_rows("promote", "cancel"), "option")
    if decision != "promote":
        return _cancelled_exit_code()
    print()
    code = _make(config.PROMOTE_TARGET, f"ASSET={ticker}", f"PROPOSAL={answer}")
    print()
    if code:
        return _failure_exit_code(f"the promotion of {ticker} did not finish",
                                  shlex.join(("make", config.PROMOTE_TARGET, f"ASSET={ticker}", f"PROPOSAL={answer}")),
                                  f"make exited with {code}", "read make's lines above")
    tui.gum_style([f"{tui.state_label('DONE')}  promoted proposal {answer} of {ticker}; make's lines above are the "
                   f"chain's where the Makefile reruns it"], "DONE")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -B -m module_ml.sub_module_terminal.terminal",
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--tickers", required=True, help="the assets this run is about, comma-separated, e.g. BTC")
    args = parser.parse_args()
    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]

    if not sys.stdin.isatty():
        return _failure_exit_code("the TUI needs a terminal", "standard input", "it is not a terminal, so no "
                                  "choice can be asked", "run make ml-terminal in a terminal")
    if not shutil.which("gum"):
        return _failure_exit_code("gum is not on PATH", "PATH", None,
                                  "install gum 2: https://github.com/charmbracelet/gum#installation")
    if not tickers:
        return _failure_exit_code("the TUI needs an asset", "--tickers", "it names none", "ASSET=<TICKER> on the make line")
    try:
        complete = sum(1 for ticker in tickers if ml_config.is_artifact_set_complete(ticker))
        tui.gum_style(["ML terminal", f"{' '.join(tickers)} · {len(tickers)} assets · {complete} artifact sets complete"],
                      "CURRENT")
        print()
        tui.gum_table(STATE_COLUMNS, _asset_rows(tickers), STATE_COLUMNS_DROP_ORDER)
        print()
        action = tui.gum_choose("action", _option_rows(*config.STAGES, "draft", "search", "recorded search",
                                                       "promote", "quit"), "option")
        if action in (None, "", "quit"):
            return _cancelled_exit_code()
        ticker = tui.gum_choose("asset", [{"asset": ticker} for ticker in tickers], "asset")
        if ticker in (None, ""):
            return _cancelled_exit_code()
        if action in config.STAGES:
            return _write_stage(ticker, action)
        catalogue, profile, search = _asset_files(ticker)
        if action == "draft":
            return _write_search_profile(ticker, catalogue, profile, search)
        if action == "search":
            return _write_coordinate_search(ticker, profile, search)
        if action == "recorded search":
            return _recorded_search_tables(ticker, profile, search)
        return _write_promoted_proposal(ticker, profile, search)
    except KeyboardInterrupt:
        print()
        print(f"{tui.state_label('CANCELLED')}  ended; a stage or a search already started stays", file=sys.stderr)
        return tui.INTERRUPTED_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
