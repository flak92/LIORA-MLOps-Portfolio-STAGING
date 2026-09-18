# Skill: the data terminal — what its screen holds and what each answer starts

`make data-terminal ASSET=<TICKER>` opens the data module's text-based user interface (TUI): the screen
`terminal.py` composes and `tui.py` draws in gum, to the standards of `../skill_tui_designer.md`.
This document says what the screen holds and what each answer starts; how a screen is drawn is that skill's. One
stage per run: after it the program ends.

## The assets, and what the terminal knows

The assets are `--tickers`, comma-separated — `ASSET=<TICKER>` on the make line in this repository, the basket
`TICKERS` at the workspace — and the terminal takes them as they are named: it defines no basket and reads no
snapshot. What it knows of an asset it reads through this module's own `config.py` and `lean.py`, the one grammar
of the raw tree: whether the database `research_ohlcv_duckdb()` names is there, and the day ZIPs `lean_day_zip_paths()`
enumerates in the leaf `raw_symbol_dir()` builds for each venue of `SOURCE_VENUES`. It opens no database — the
measurement of what a database holds is `data-status`'s — and it computes nothing: a count of files and the last
of the days they are named for is presentation.

## The opening

A run opens on the header block — *Data terminal* over the assets, their count and how many of them have a
database — then the state table, one row per asset: `asset`, `database` (`yes` / `no`), one `<venue> days` column
per venue of `SOURCE_VENUES` in its tier order (`binance days`, `bybit days` — the count of day ZIPs in that venue's
leaf, `0` where the leaf is not there) and `last day` (the greatest `YYYYMMDD` either leaf holds, `—` where neither
holds a day). Wider than the terminal, the columns leave in the order `last day`, then each `<venue> days` in tier
order; `asset` and `database` stay. Then the menu, `gum choose` headed *action*: download, ingest, status, quit.

## The actions

Every action is one stage of this module's chain, the make target `data-<stage>`, and the terminal decides nothing
about it. After the menu the *asset* form — the assets of `--tickers` as rows, one answered without asking — then
the plan (`parameter | value`: the asset, the stage and what it writes, from `WRITES_BY_STAGE`) and the `command`
line verbatim, `make data-<stage> ASSET=<TICKER>`, then the gate `<stage> <TICKER>?` with the stage first and
*cancel*. The target's own lines stay on the screen as they come, and the run ends on the `DONE` block or on the
failure block carrying make's exit code.

- **download** — both venues' 1m klines into the raw store, one Lean day ZIP per venue and UTC day; a day whose ZIP
  exists is skipped, so the same answer backfills and tops up.
- **ingest** — both ZIP trees into `<TICKER>_research_ohlcv.duckdb`: the two venue tables, then the canonical
  series.
- **status** — read-only scans of the databases into `data_status.json` in the status store.

One fact the plan states as the Makefile holds it: in this repository every stage runs the asset named, while at
the workspace `data-download` and `data-status` are basket lines — they run the whole basket whatever `ASSET` says,
and the snapshot `status` writes is one for the basket. `ingest` runs one asset in both.

**quit** — one `CANCELLED` line, nothing written, exit 0.

## What it starts, and how

`make`, and only `make` — one call, its lines uncaptured so they reach this terminal as they come, no `check`, no
`cwd`, no `env`, no timeout. The same target name resolves in both Makefiles: in this repository `data-<stage>`
runs the stage in the module's venv; at the workspace it runs the stage in a one-off container of the `data`
runner. The terminal names neither — the Makefile does.

## Exits

`skill_tui_designer.md` § Failures and exits, with one fact of its own: Ctrl-C ends the TUI with 130 and a stage
make already started stays. A failure block names what failed, where, why when it is known, and what a hand does
next — no terminal on standard input, no gum, no asset named, or a target that exited non-zero.

## Design rationale

| object | why here | why beside these | why this boundary |
|---|---|---|---|
| the sub-module | the data module's own instrument: its targets are `data-<stage>`, carried by this repository's Makefile and the Orchestration Makefile alike | inside `module_data`, beside the stages it starts; the shape every module's `sub_module_terminal/` shares | it imports the standard library and its own package alone (D05): the venues and the descriptors through `config.py`, the day ZIPs through `lean.py`; it runs on the host's `python3` with gum and no virtual environment, and opens no database |
| `terminal.py` | the one screen and the one stage | it imports `config.py` and `tui.py`, and its own package for the venues, the paths and the raw leaf's enumeration | it writes no file and starts the three make targets; `--tickers` is its only argument, `-h` its help |
| `config.py` | the one surface of configuration | `terminal.py` imports it; `tui.py` imports it for plain output and the filter's placeholder alone | it carries nothing but the stages, what each writes and the plain-output conditions: `module_data/config.py` is standard library, so the store reads, `SOURCE_VENUES`, `raw_symbol_dir()` and `research_ohlcv_duckdb()` are imported and never copied — an owner that can read its module's `config.py` duplicates nothing (`skill_tui_designer.md` § Where the screens live) |
| `tui.py` | how a screen is drawn and an answer taken | one file with every other terminal's and the crawler's, seven times by extraction and registered | it writes to the terminal and no file; it knows none of this sub-module's objects |
| the duplication | no module imports another (D05), and a package for what the terminals share would be the `common` the contract refuses | — | paid on purpose: one `tui.py`, `OUTPUT_PLAIN` and `FILTER_PLACEHOLDER`, the screen helpers `_option_rows()`, `_cancelled_exit_code()`, `_failure_exit_code()` and `_make()` — the rows of `../glossary.md` § Twice by extraction this sub-module joins, changed on every side at once |
