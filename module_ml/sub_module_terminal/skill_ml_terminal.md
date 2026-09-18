# Skill: the ML terminal — what each screen holds and what each answer writes

`make ml-terminal` opens the ML module's text-based user interface (TUI): the screens `terminal.py` composes and
`tui.py` draws in gum, to the standards of `../../module_skills/skill_tui_designer.md`. This document says what each
screen holds and what each answer writes or starts; how a screen is drawn is that skill's. One action per run: after it
the program ends.

## The assets, and what the terminal knows

The assets are `ASSET=` on the make line and `--tickers` at the process boundary, like every stage — one or more,
comma-separated: the basket is the default and `ASSET=` narrows it to one. An action is for one asset. Where the run
names more than one, the asset form — `gum choose` headed *asset*, the assets of `--tickers` as rows — asks which,
after the menu; a run of one asset is answered without asking (`--select-if-one`). A ticker is never typed.

Per asset it reads, as objects, `<TICKER>_catalogue.json` for the columns the search may admit and the decision slot
the labels parquet is named by, `<TICKER>_coordinate_search.json` for where the search stands — its beam, its champion,
its path and its proposals, each naming a trial by its index — `<TICKER>_coordinate_search_trials.jsonl` for the
trials themselves and every number the tables show, read off the line an index names, and
`<TICKER>_coordinate_search_profile.json` for what a hand last asked for; and by presence alone —
`descriptor(ticker).exists()`, `yes` or `no` — `<TICKER>_label_events_<slot>.parquet`, `<TICKER>_parameters.json`,
`<TICKER>_model_evaluation.json` and `<TICKER>_strategy_evaluation.json`. Every descriptor is `module_ml/config.py`'s
own, imported — that file is standard library — and `is_artifact_set_complete()`, the one question `status.py` asks,
counts the header's complete sets. The counts it shows per loop are `trial_count_by_loop` from the search file, read
and not recomputed: the search adds its own lines and the points its studies drew, once, at a round boundary. It reads
no snapshot: `ml_status.json` is only as fresh as the last `make ml-status`, and a search that started a minute ago
would read as absent.

**The one comparison it makes** is the profile it holds against the profile the recorded search was run with — parsed
objects, never bytes, because the search records that profile verbatim inside its `inputs`. Its four answers are the
`profile` cell of the state table: `not drafted`, `no search`, `matches the search`, `differs from the search`. The
page's `inputs_current` is a wider question — it folds the parameters, the catalogue and the asset's own state — and
stays the page's, because answering it needs numpy.

## The opening

A run opens on the header block — *ML terminal* over `<tickers> · <n> assets · <k> artifact sets complete`, the
tickers as `--tickers` named them and a set complete when the parameters, the model evaluation and the strategy
evaluation all stand — then the state table, one row per asset: `asset`, `catalogue`, `labels`, `parameters`, `model`,
`strategy`, `profile`, `trials` — `yes` or `no` for each file, `—` for the labels where no catalogue names their slot,
for the profile one of the four words above, for the trials the ledger's line count or `—` where there is no ledger —
then the menu, `gum choose` headed *action*: labels, hpo, train, strategy, status, draft, search, recorded search,
promote, quit. The first five words are the stages of this module's chain in the Makefile's order, each the target
`ml-<stage>`; the four after them are the coordinate search's own; then the asset form, where the run names more than
one asset.

## The actions

- **a stage** — labels, hpo, train, strategy or status: the plan, `parameter | value` — the asset, the stage and what
  it writes, the artifact's registered name with the asset's ticker in it (`WRITES_BY_STAGE`) — and the `command` line
  verbatim, `make ml-<stage> ASSET=<TICKER>`; then the gate `<stage> <TICKER>?` with the stage first and *cancel*. The
  stage runs through `make` and its own lines stay on the screen as they come; the run ends on the `DONE` block —
  `ml-<stage> of <TICKER> done` — or on the failure block carrying make's exit code. The terminal knows no order of
  the chain and no precondition of a stage: a stage started before the one it reads from fails in its own words, on the
  file it did not find, and those words stand above the block. `status` folds the assets its target is named —
  through this terminal the one asset chosen.
- **draft** — four forms under the steps table, then the changes. *columns to admit*, every column of the contract in
  catalogue order, timeframe-major, those the profile admits chosen at the start and all of them when there is no
  profile — so a column the catalogue does not offer on a timeframe cannot be admitted on it. *start state*, the
  asset's own or the recorded search's champion. *coordinates to search*, the coordinates of
  `GRID_BY_COORDINATE_DEFAULT`, each shown with its grid; the grid itself is not asked, because it is one preset and
  another grid is a hand's edit of the file. The drafted profile carries **every** coordinate whatever a hand ticks:
  one left unticked is pinned to where it stands — the first point of the grid the profile already holds, or
  `START_BY_COORDINATE_DEFAULT` of `module_ml/config.py` when there is no profile yet — and its grid becomes that one
  point. A one-point grid has no neighbour, so its family makes no move and the kernel needs no case for it; a profile
  that simply omitted the coordinate left the search reading a key that was not there. On the recorded search's state
  table, *coordinates searched* counts the grids offering a choice, not the keys present. *loops*, the loops of a round
  in their frozen order, `COORDINATE_SEARCH_ROUND_LOOPS` of `module_ml/config.py`. Then the changes table — each key
  of the profile whose value moves, now and after — or the line `no profile changes`, and the gate
  `draft <TICKER>_coordinate_search_profile.json?` with *draft* first, *back* and *cancel*; *draft* is absent when
  nothing changes, and *back* asks the forms again from the first. A recorded search run under another profile puts
  one `WARN` line above the gate: the next search will start a new state and overwrite the search file. That is a fact
  about how the search resumes, not a refusal. A draft needs the contract: without `<TICKER>_catalogue.json` the action
  ends on the failure block, whose *next* is `make features-catalogue ASSET=<TICKER>` first.
- **search** — the *session* form first, `gum choose` headed *session*: *detached*, the search in its own tmux session
  through the Makefile's twin `tmux-ml-coordinate-search`, alive after this terminal closes; *foreground*, the module's
  own stage `ml-coordinate-search` on this screen, ending with the search. Then the plan: the asset, the profile, the
  coordinates searched, the loops, the session, what will be written, and the `command` line verbatim; then the grid of
  each coordinate; then the same `WARN` line where it applies, and the gate
  `start the coordinate search of <TICKER>?` with *start* first. *start* runs `make <target> ASSET=<TICKER>` and the
  Makefile's own lines stay on the screen — for a detached session, whether it already exists or has just begun; for
  the foreground, the search's own lines until it ends. The `DONE` block says which: the search `is in its session` or
  `ran on this screen`. *detached* runs the Makefile's own `tmux-ml-coordinate-search`, which requires the `ASSET=`
  the terminal always passes and starts `make ml-coordinate-search` for it in the tmux session
  `coordinate-search-<ticker>`, one per asset; where that session is already running, the target says so and starts
  nothing. A search needs a profile: without one the action ends on the failure block, whose *next* is to draft one.
- **recorded search** — the state table, `parameter | value`: the asset, the profile, the coordinates searched, the
  loops, the trials in all and per loop, whether it converged, the champion trial and the proposal count; the research
  path (each accepted expansion with its round, loop, family, trial and the path's CAGR, Calmar, drawdown and trade
  count) and the proposals (each with the coordinates it moves and the same four numbers). Which trials the path and
  the proposals hold comes from the state file; each trial's columns, geometry and numbers from its line of the
  ledger, and the coordinates a proposal moves are that line against the asset's own state the search recorded in its
  inputs; the counts per loop from the state file. It writes nothing and ends on its last table; a table with no rows
  is a line instead — `no accepted move`, `no proposal`. The word is *recorded search* and not *status*, which is the
  `ml-status` stage's on the same menu (`glossary.md` § Terminals).
- **promote** — the proposals as a list under the steps table, then the plan with the coordinates that proposal moves
  and what it writes — `<TICKER>_feature_set.json`, `<TICKER>_barriers.json` — and the `command` line verbatim, then the
  gate `promote proposal <n> of <TICKER>?`. *promote* runs
  `make ml-coordinate-search-promote ASSET=<TICKER> PROPOSAL=<n>`: the promotion in a one-off container of the `ml`
  runner, then that target's second recipe line, `ml-all` for that asset, so the chain's own lines stay on the screen
  as they come — the `DONE` block says whose lines they are.
- **quit** — one `CANCELLED` line, nothing written, exit 0.

There is no **stop**: a hand stops a detached search with `tmux attach -t coordinate-search-<ticker>` and Ctrl-C, as
`make help` says, and a foreground one with Ctrl-C on this screen. There is no **holdout**: F5 is computed by
`ml-all`, which the promotion runs after it.

## The tables

Every table of this TUI, its columns and the order a narrow terminal drops them in (`skill_tui_designer.md` § Tables);
the identifier is never dropped, and a list is a table a hand picks from.

| table | where | columns | drop order |
|---|---|---|---|
| the state table | the opening | `asset`, `catalogue`, `labels`, `parameters`, `model`, `strategy`, `profile`, `trials` | `trials`, `profile`, `strategy`, `model`, `parameters`, `labels` |
| the menu, every gate | the opening; before a stage, a draft, a search, a promotion | `option` | — |
| the asset form | after the menu, more than one asset | `asset` | — |
| the plan | a stage, search, promote | `parameter`, `value` | — |
| the steps table | draft, promote — above each form where more than one row is asked | `step`, `state`, `choice` | — |
| the columns form | draft | `column`, `timeframe`, `definition` | `definition`, `timeframe` |
| the start state form | draft | `start state`, `value` | — |
| the coordinates form | draft | `coordinate`, `grid`, `points` | `points`, `grid` |
| the loops form | draft | `loop` | — |
| the changes table | draft | `parameter`, `now`, `after` | — |
| the session form | search | `session`, `target` | `target` |
| the grid table | search, under the plan | `coordinate`, `grid`, `points` | `points` |
| the recorded search's state table | recorded search | `parameter`, `value` | — |
| the path table | recorded search | `#`, `round`, `loop`, `family`, `trial`, `path CAGR`, `path Calmar`, `path maxDD`, `trades` | `trades`, `path maxDD`, `path Calmar`, `family` |
| the proposals table; the proposal list | recorded search; promote | `#`, `trial`, `coordinates moved`, `path CAGR`, `path Calmar`, `path maxDD`, `trades` | `path maxDD`, `trades`, `path Calmar`, `coordinates moved` |

## What it starts, and how

`make`, and only `make` — one call, its lines uncaptured so they reach this terminal as they come, no `check`, no
`cwd`, no `env`, no timeout. Every target it names is the Makefile's: `ml-<stage>`, `ml-coordinate-search` and
`ml-coordinate-search-promote` each run their stage in a one-off container of the `ml` runner, and an option of the
menu exists only for a target the Makefile carries. The session form's second target is `tmux-ml-coordinate-search`,
the detached twin of `ml-coordinate-search` — a terminal does not resume, a search does, and only a stage that
resumes has a detached twin (`AGENTS.md` § Canonical vocabulary, the Makefile-targets row). tmux and docker compose
are the Makefile's boundaries, and a TUI that spoke either would be a second place they are named. The terminal does
not even test whether tmux is on the `PATH`, or whether a target is in the Makefile it runs: when either is not,
`make` says so in its own words and the failure block carries them.

`PROPOSAL=` on the outer make line does nothing — the terminal always passes the rank a hand chose.

A state file written by an older shape of the code is not migrated. Where it lacks a key the code reads, the terminal
and the search fail on that key, loudly — a state from before the exposure count fails on `trial_count_by_loop` — and a
hand deletes the search's two files so the search writes new ones. Where it holds every key the code reads and more
besides, as a state from before the path and the proposals stopped copying their trials' numbers does, it is read and
the extra keys are ignored: the tables are the same, because the numbers come from the ledger either way, but the file
is not this code's bytes, and the proof that two runs give the same bytes is taken on a file this code wrote — delete
it before taking it. A stage that guessed at a key it did not find would be guessing at which experiment the file
described.

## Exits

`skill_tui_designer.md` § Failures and exits, with one fact of its own: Ctrl-C ends the TUI with 130 and sends nothing
to what it started — a detached search stays in its session, because the session outlives the terminal that started
it; a stage or a search in the foreground is this screen's own and takes the same Ctrl-C, and a search resumes when it
is started again. A failure block names what failed, where, why when it is known, and what a hand does next — no
catalogue, no profile, no recorded search, no proposal, no asset named, no terminal on standard input, no gum, or a
`make` that exited non-zero.

## Design rationale

| object | why here | why beside these | why this boundary |
|---|---|---|---|
| the sub-module | the ML module's own instrument: the stages its menu offers are this module's chain, and the search and the promotion are `ml-*` targets of the Makefile; the catalogue it reads is a store file the feature layer wrote — the per-asset contract `AGENTS.md` § Architecture shape names, crossing as a file and not as an import — so nothing of `module_features` is imported | inside `module_ml`, whose `config.py` owns every descriptor it reads and the search's frozen geometry; the shape every module's `sub_module_terminal/` shares | it imports the standard library and its own package alone (D19): it runs on the host's `python3` with gum and no virtual environment |
| `terminal.py` | the opening screen and the nine actions, what each screen holds | it imports `config.py` and `tui.py`, and `module_ml/config.py` as `ml_config` for the descriptors, `START_BY_COORDINATE_DEFAULT`, `COORDINATE_SEARCH_ROUND_LOOPS` and `is_artifact_set_complete()` | it writes the one profile file and starts the make targets — `ml-<stage>`, the session form's two, the promotion; `-h`, `--help` and `--tickers` are its only arguments |
| `config.py` | the one surface of configuration | `terminal.py` imports it; `tui.py` imports it for plain output and the filter's placeholder alone | it carries what `module_ml/config.py` lacks and `module_ml/dataset.py` cannot lend: `dataset.py` imports duckdb and numpy, which the host's `python3` does not hold, so `load_json()`, `load_jsonl()` and `write_json()` stand here twice by extraction; `MODULE_TOKEN`, `STAGES`, `WRITES_BY_STAGE`, the three targets and the grid preset live here, so another grid is an edit of the profile and not of the code; no store read and no descriptor — those are imported |
| `tui.py` | how a screen is drawn and an answer taken | one file with every other terminal's and the crawler's, five times by extraction and registered | it writes to the terminal and no file; it knows none of this sub-module's objects |
| the duplication | no module imports another (D02), and a package for what the terminals share would be the `common` the contract refuses | — | paid on purpose: one `tui.py`, `OUTPUT_PLAIN`, the screen helpers and `_make()`, registered in `module_skills/glossary.md` § Twice by extraction and changed on every side at once; and the readers and the writer of JSON its `config.py` carries — `load_json()`, `load_jsonl()` and the canonical form of `write_json()` — each with its own row there |
