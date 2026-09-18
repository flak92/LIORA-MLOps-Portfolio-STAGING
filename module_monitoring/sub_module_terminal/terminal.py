"""The monitoring terminal — the monitoring module's text-based user interface (TUI): the four snapshots the dashboard
reads and the runs the recorder left, then one position of the presentation switch a hand chooses in the menu — on or
off — started through `make`, its lines on this screen as they come; then it closes. Drawn by tui.py to
module_skills/skill_tui_designer.md.

It computes nothing and writes nothing: the snapshots and the run records it reads through this module's own
`config.py`, and each action is `make on` or `make off` — the Makefile is where a container, and at the workspace the
two residents, are named.

keys:
  Enter takes the option under the cursor; Esc cancels and writes nothing (exit 0); Ctrl-C ends the TUI (exit 130),
  and what make already started runs on.

output is plain — state words in brackets, no colour, no symbol, no border — when NO_COLOR is set and not empty, TERM
is dumb or standard output is not a terminal; the words, the order and the counts are the same in both.

exit codes:
  0 the action done, or cancelled with nothing written; 1 a failure, named last on stderr; 2 an unknown argument;
  130 Ctrl-C

examples:
  make monitoring-terminal                                    the TUI over the stores one level up (the workspace's, or from this repository)
  STORE_STATUS_DIR=/path/to/store_status make monitoring-terminal   the TUI over another status store
  NO_COLOR=1 make monitoring-terminal                         the TUI in plain output
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys

from . import config, tui
from .. import config as monitoring_config


# ---- the screens' own rows ------------------------------------------------------------------------------

def _option_rows(*options: str) -> list[dict]:
    return [{"option": option} for option in options]


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


def _snapshot_rows() -> list[dict]:
    """One row per snapshot the dashboard reads: its `generated_at_utc` as the file carries it, `—` where the file
    carries no such key (skills_status.json), `absent` where the file is not there."""
    rows = []
    for name in config.SNAPSHOT_FILE_NAMES:
        path = monitoring_config.store_status_file(name)
        rows.append({"snapshot": name, "generated_at_utc": (config.load_json(path).get("generated_at_utc", "—")
                                                            if path.is_file() else "absent")})
    return rows


def _run_rows() -> list[dict]:
    """The run records as they stand: how many runs the store holds — `0` where the store is not there — and the
    newest, the greatest directory name, a run id sorting chronologically by design; `—` where there is none."""
    records = monitoring_config.STORE_RUN_RECORDS_DIR
    run_ids = sorted(path.name for path in records.iterdir() if path.is_dir()) if records.is_dir() else []
    return [{"parameter": "run records", "value": len(run_ids)},
            {"parameter": "newest run", "value": run_ids[-1] if run_ids else "—"}]


# ---- the actions ----------------------------------------------------------------------------------------

def _write_stage(stage: str) -> int:
    """One position of the presentation switch, started through make after the plan and its gate — the target the
    position's own word, a lifecycle target being bare in both Makefiles."""
    target = stage
    tui.gum_table(("parameter", "value"), [{"parameter": "action", "value": stage},
                                           {"parameter": "writes", "value": config.WRITES_BY_STAGE[stage]}])
    print(f"command         {shlex.join(('make', target))}")
    print()
    decision = tui.gum_choose(f"{stage}?", _option_rows(stage, "cancel"), "option")
    if decision != stage:
        return _cancelled_exit_code()
    print()
    code = _make(target)
    print()
    if code:
        return _failure_exit_code(f"{target} ended with exit {code}", shlex.join(("make", target)),
                                  f"make exited with {code}", "read make's lines above")
    tui.gum_style([f"{tui.state_label('DONE')}  {target} done"], "DONE")
    return 0


def main() -> int:
    argparse.ArgumentParser(prog="python3 -B -m module_monitoring.sub_module_terminal.terminal", description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False).parse_args()
    if not sys.stdin.isatty():
        return _failure_exit_code("the TUI needs a terminal", "standard input", "it is not a terminal, so no choice "
                                  "can be asked", f"run make {config.MODULE_TOKEN}-terminal in a terminal")
    if not shutil.which("gum"):
        return _failure_exit_code("gum is not on PATH", "PATH", None,
                                  "install gum 2: https://github.com/charmbracelet/gum#installation")
    try:
        snapshots, runs = _snapshot_rows(), _run_rows()
        present = sum(row["generated_at_utc"] != "absent" for row in snapshots)
        recorded = runs[0]["value"]   # the `run records` row: the count the table shows, repeated in the header
        tui.gum_style(["Monitoring terminal", f"{present} of {len(snapshots)} snapshots · {recorded} runs"], "CURRENT")
        print()
        tui.gum_table(("snapshot", "generated_at_utc"), snapshots)
        print()
        tui.gum_table(("parameter", "value"), runs)
        print()
        action = tui.gum_choose("action", _option_rows(*config.STAGES, "quit"), "option")
        if action in (None, "", "quit"):
            return _cancelled_exit_code()
        return _write_stage(action)
    except KeyboardInterrupt:
        print()
        print(f"{tui.state_label('CANCELLED')}  ended; what make already started runs on", file=sys.stderr)
        return tui.INTERRUPTED_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
