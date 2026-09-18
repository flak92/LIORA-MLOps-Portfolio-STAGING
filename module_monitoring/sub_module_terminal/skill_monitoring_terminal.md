# Skill: the monitoring terminal — what its screen holds and what each answer starts

`make monitoring-terminal` opens the monitoring module's text-based user interface (TUI): the screen `terminal.py`
composes and `tui.py` draws in gum, to the standards of `../../module_skills/skill_tui_designer.md`. This document
says what the screen holds and what each answer starts; how a screen is drawn is that skill's. One action per run:
after it the program ends.

## The opening

A run opens on the header block — *Monitoring terminal* over how many of the four snapshots are there and how many
runs are recorded — then two tables, each read through this module's own `config.py` and never recomputed:

- the snapshots table, one row per name of `SNAPSHOT_FILE_NAMES` in the status store — `snapshot`, the file name,
  and `generated_at_utc` as the file carries it: `—` where the file carries no such key (`skills_status.json`, whose
  dates are its reports' own), `absent` where the file is not there;
- the run-records table, `parameter | value`: `run records`, the count of run directories in the run-records store
  (`0` where the store is not there), and `newest run`, the greatest run id — a run id sorts chronologically by
  design (`../../module_skills/glossary.md` § Run record) — `—` where none is.

Neither table drops a column: each has the identifier and one value. Then the menu, `gum choose` headed *action*:
on, off, quit.

## The actions

Every action is one position of the presentation switch, the lifecycle pair `on` / `off` that goes bare in the
Makefile, and the terminal decides nothing about it: the plan (`parameter | value`: the action and what it writes,
from `WRITES_BY_STAGE`) and the `command` line verbatim, `make on` or `make off`, stand before the gate `<action>?`
with the action first and *cancel*; the target's own lines stay on the screen as they come, and the run ends on the
`DONE` block or on the failure block carrying make's exit code. Two facts of its own:

- **what each word moves.** `on` builds the one image every service runs and brings the two residents up together,
  `dashboard` and `devops`, then prints the page's address it measured and opens it; `off` is `docker compose down`,
  every container of this project stopped and removed. The terminal names none of it: the plan's `command` line says
  `make on`, and what that raises is the Makefile's to say.
- **the switch is the whole menu.** `monitoring-terminal` is the only other target this module's token names, and it
  is what opened this screen, so the two positions and *quit* are all a run offers — one option per target the
  terminal is over (`module_skills/glossary.md` § Terminals, the row *the stages a terminal offers*).

**quit** — one `CANCELLED` line, nothing written, exit 0.

## What it starts, and how

`make`, and only `make` — one call, its lines uncaptured so they reach this terminal as they come, no `check`, no
`cwd`, no `env`, no timeout. The call is the target's own word and nothing more: no image, no container name and
no published port is written in `terminal.py`, which imports the standard library and its own package alone (D19) —
what `on` raises and `off` takes down is the Makefile's to say, over the topology of `docker-compose.yml`.

## Exits

`skill_tui_designer.md` § Failures and exits, with one fact of its own: Ctrl-C ends the TUI with 130 and what make
already started runs on — a container `on` started stays up. A failure block names what failed, where, why when it
is known, and what a hand does next — no terminal on standard input, no gum, or a target that exited non-zero.

## Design rationale

| object | why here | why beside these | why this boundary |
|---|---|---|---|
| the sub-module | the monitoring module's own instrument: its targets are the switch, `on` and `off`, the lifecycle pair the Makefile carries bare | inside `module_monitoring`, beside the dashboard whose stores it shows and the panel; the shape every module's `sub_module_terminal/` shares | it imports the standard library and its own package alone (D19): the two stores through `module_monitoring/config.py`; it runs on the host's `python3` with gum and no virtual environment, in no container, and opens no socket |
| `terminal.py` | the one screen and the one action | it imports `config.py` and `tui.py`, and its own package's `config.py` for `store_status_file()` and `STORE_RUN_RECORDS_DIR` | it writes no file and starts the two make targets; `-h`, `--help` is its only argument |
| `config.py` | the one surface of configuration | `terminal.py` imports it; `tui.py` imports it for plain output and the filter's placeholder alone | it carries the snapshot names, the two positions and what each writes, the plain-output conditions and the one reader of JSON: `module_monitoring/config.py` is standard library, so the store reads and the descriptors are imported and never copied — an owner that can read its module's `config.py` duplicates nothing (`skill_tui_designer.md` § Where the screens live) |
| `tui.py` | how a screen is drawn and an answer taken | one file with every other terminal's and the crawler's, five times by extraction and registered | it writes to the terminal and no file; it knows none of this sub-module's objects |
| the duplication | no module imports another (D02), and a package for what the terminals share would be the `common` the contract refuses | — | paid on purpose: one `tui.py`, `load_json()`, `OUTPUT_PLAIN` and `FILTER_PLACEHOLDER`, the screen helpers `_option_rows()`, `_cancelled_exit_code()`, `_failure_exit_code()` and `_make()` — the rows of `../../module_skills/glossary.md` § Twice by extraction this sub-module joins, changed on every side at once |
