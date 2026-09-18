# Skill: the features terminal — what its screen holds and what each answer starts

`make features-terminal ASSET=<TICKER>` opens the feature module's text-based user interface (TUI): the screen
`terminal.py` composes and `tui.py` draws in gum, to the standards of `../skill_tui_designer.md`.
This document says what the screen holds and what each answer starts; how a screen is drawn is that skill's. One
stage per run: after it the program ends.

## The assets, and what the terminal knows

The assets are `ASSET=` on the make line and `--tickers` at the process boundary, like every stage: in this
repository `ASSET=<TICKER>` is required and names one; at the workspace `ASSET` names one, and its absence names the
basket. Of each asset the terminal knows three facts, read off the artifacts store by the descriptors `config.py`
carries and never recomputed: whether `<TICKER>_research_ohlcv.duckdb` stands (`research_ohlcv_duckdb()`), whether
`<TICKER>_catalogue.json` stands (`catalogue_json()`), and how many `<TICKER>_features_*.parquet` the asset's folder
holds (`artifact_dir()`). It opens no database and reads no parquet — a file's presence is the whole fact — and it
reads no snapshot: `features_status.json` is only as fresh as the last `make features-status`, and a catalogue
written a minute ago would read as absent.

## The opening

A run opens on the header block — *Features terminal* over the assets, their count and how many of them hold a
catalogue — then the state table, one row per asset:

| column | holds | left out |
|---|---|---|
| `asset` | the ticker | never |
| `database` | `yes` / `no` — whether `<TICKER>_research_ohlcv.duckdb` stands | never |
| `catalogue` | `yes` / `no` — whether `<TICKER>_catalogue.json` stands | second |
| `feature parquets` | the count of `<TICKER>_features_*.parquet` in the asset's folder, `0` where it holds none | first |

then the menu, `gum choose` headed *action*: bars, catalogue, status, quit.

## The actions

Every action is one stage of this module's chain, the make target `features-<stage>`, and the terminal decides
nothing about it. After the menu comes the *asset* form — the assets of `--tickers` as rows, one answered without
asking — then the plan, a `parameter | value` table:

| parameter | value |
|---|---|
| asset | the ticker chosen |
| stage | the stage chosen |
| writes | what the stage writes — its line of `WRITES_BY_STAGE`, the ticker in place of `<TICKER>` |

then the `command` line verbatim, `command  make features-<stage> ASSET=<TICKER>`, and the gate `<stage> <TICKER>?`
with the stage first and *cancel*. The target's own lines stay on the screen as they come, and the run ends on the
`DONE` block or on the failure block carrying make's exit code.

- **bars** — `make features-bars ASSET=<TICKER>`; writes the aggregation tables of every timeframe of the register
  into `<TICKER>_research_ohlcv.duckdb`.
- **catalogue** — `make features-catalogue ASSET=<TICKER>`; writes `<TICKER>_features_<slot>.parquet`, one per
  timeframe, and `<TICKER>_catalogue.json`.
- **status** — `make features-status ASSET=<TICKER>`; writes `features_status.json` in the status store. At the
  workspace that target folds the whole basket whatever `ASSET` says — the snapshot is the basket's, and the
  Orchestration Makefile passes `TICKERS_CSV` — while in this repository it folds the assets `ASSET` names.
- **quit** — one `CANCELLED` line, nothing written, exit 0.

## What it starts, and how

`make`, and only `make` — one call, its lines uncaptured so they reach this terminal as they come, no `check`, no
`cwd`, no `env`, no timeout. The same target name resolves in both Makefiles: at the workspace `features-<stage>`
runs the stage in a one-off container of the `features` runner; in this repository alone it runs in the module's
venv, against the stores one level up by default. A container and the order of the chain are the Makefile's
boundaries (`AGENTS.md` § Canonical vocabulary), and a TUI that spoke either would be a second place they are named.

## Exits

`skill_tui_designer.md` § Failures and exits, with one fact of its own: Ctrl-C ends the TUI with 130 and a stage
already started stays — its process is make's, not this terminal's. A failure block names what failed, where, why
when it is known, and what a hand does next — no terminal on standard input, no gum, no asset in `--tickers`, or a
target that exited non-zero.

## Design rationale

| object | why here | why beside these | why this boundary |
|---|---|---|---|
| the sub-module | the feature module's own instrument: its targets are `features-<stage>`, carried by this repository's Makefile and the Orchestration Makefile alike | inside `module_features`, beside the stages it starts; the shape every module's `sub_module_terminal/` shares | it imports the standard library and its own package alone (D05): it runs on the host's `python3` with gum and no virtual environment, computes nothing and opens no file of the store |
| `terminal.py` | the one screen and the one stage | it imports `config.py` and `tui.py`, and nothing of the module's package above it | it writes no file and starts the three make targets; `-h`, `--help` and `--tickers` are its only arguments |
| `config.py` | the one surface of configuration | `terminal.py` imports it; `tui.py` imports it for plain output and the filter's placeholder alone | it carries registered copies of the two store reads and the three descriptors it reads, because `module_features/config.py` imports `.indicators` — and numpy with it — at its thirteenth line, and a terminal runs on the host's `python3` with no virtual environment; the stages and what each writes are the one list |
| `tui.py` | how a screen is drawn and an answer taken | one file with every other terminal's and the crawler's, seven times by extraction and registered | it writes to the terminal and no file; it knows none of this sub-module's objects |
| the duplication | no module imports another (D05), and a package for what the terminals share would be the `common` the contract refuses | — | paid on purpose: one `tui.py`, `OUTPUT_PLAIN` and `FILTER_PLACEHOLDER`, the screen helpers and `_make()` — the rows every terminal joins — and, this terminal's own, the store reads, the descriptors `artifact_dir()` and `research_ohlcv_duckdb()`, and `catalogue_json()`, each a row of `module_skills/glossary.md` § Twice by extraction and changed on every side at once |
