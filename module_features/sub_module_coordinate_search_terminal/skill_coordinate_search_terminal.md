# Skill: the coordinate search terminal — what each screen holds and what each answer writes

`make features-coordinate-search-terminal` opens the feature layer's text-based user interface (TUI) over the
coordinate search: the screens `terminal.py` composes and `tui.py` draws in gum, to the standards of
`../../module_skills/skill_tui_designer.md`. This section says what each screen holds and what each answer
writes; how a screen is drawn is that skill's. One action per run: after it the program ends.

## The asset, and what the terminal knows about it

The asset is `ASSET=` on the make line and `--tickers` at the process boundary, like every stage — the terminal
has no screen for choosing one, and refuses a run that names more than one, saying to narrow it. It reads
`<TICKER>_catalogue.json` for the columns the search may admit, `<TICKER>_coordinate_search.json` for where
the search stands — its beam, its champion, its path and its proposals, each naming a trial by its index —
`<TICKER>_coordinate_search_trials.jsonl` for the trials themselves and every number the tables show, read off
the line an index names, and `<TICKER>_coordinate_search_profile.json` for what a hand last asked for. The
counts it shows per loop are `trial_count_by_loop` from the search file, read and not recomputed: the search
adds its own lines and the points its studies drew, once, at a round boundary. It reads no
snapshot: `ml_status.json` is only as fresh as the last `make ml-status`, and a search that started a minute
ago would read as absent.

**The one comparison it makes** is the profile it holds against the profile the recorded search was run with —
parsed objects, never bytes, because the search records that profile verbatim inside its `inputs`. Its four
answers are the `profile` cell of the opening table: `not drafted`, `no search`, `matches the search`,
`differs from the search`. The page's `inputs_current` is a wider question — it folds the parameters, the
catalogue and the asset's own state — and stays the page's, because answering it needs numpy.

## The opening

A run opens on the header block — *Coordinate search terminal* over the asset, where its profile stands and how
many trials its search holds — then the state table, one fact a row: the asset, the profile, the coordinates
searched, the loops, the trials in all and per loop, whether it converged, the champion trial and the proposal
count; then the menu, `gum choose` headed *action*: draft, search, status, promote, quit.

## The actions

- **draft** — four forms under the steps table, then the changes. *columns to admit*, every column of the
  contract in catalogue order, timeframe-major, those the profile admits chosen at the start and all of them
  when there is no profile — so a column the catalogue does not offer on a timeframe cannot be admitted on it.
  *start state*, the asset's own or the recorded search's champion. *coordinates to search*, the coordinates of
  `GRID_BY_COORDINATE_DEFAULT`, each shown with its grid; the grid itself is not asked, because it is one
  preset and another grid is a hand's edit of the file. The drafted profile carries **every** coordinate
  whatever a hand ticks: one left unticked is pinned to where it stands — the first point of the grid the
  profile already holds, or `START_BY_COORDINATE_DEFAULT` when there is no profile yet — and its grid becomes
  that one point. A one-point grid has no neighbour, so its family makes no move and the kernel needs no case
  for it; a profile that simply omitted the coordinate left the search reading a key that was not there.
  On the state table, *coordinates searched* counts the grids offering a choice, not the keys present. *loops*, the loops of a round in their frozen order.
  Then the changes table — each key of the profile whose value moves, now and after — or the line
  `no profile changes`, and the gate `draft <TICKER>_coordinate_search_profile.json?` with *draft* first,
  *back* and *cancel*; *draft* is absent when nothing changes, and *back* asks the forms again from the first.
  A recorded search run under another profile puts one `WARN` line above the gate: the next search will start a
  new state and overwrite the search file. That is a fact about how the search resumes, not a refusal.
- **search** — the plan: the asset, the profile, the coordinates searched, the loops, what will be written, and
  the `command` line verbatim; then the grid of each searched coordinate; then the same `WARN` line where it
  applies, and the gate `start the coordinate search of <TICKER>?` with *start* first. *start* runs
  `make tmux-ml-coordinate-search ASSET=<TICKER>` and the Makefile's own lines stay on the screen — whether the
  session already exists or has just begun.
- **status** — the state table, the research path (each accepted expansion with its round, loop, family, trial
  and the path's CAGR, Calmar, drawdown and trade count) and the proposals (each with the coordinates it moves
  and the same four numbers). Which trials the path and the proposals hold comes from the state file; each
  trial's columns, geometry and numbers from its line of the ledger, and the coordinates a proposal moves are
  that line against the asset's own state the search recorded in its inputs; the counts per loop from the state
  file. It writes nothing and ends on its last table; a table with no rows is a line
  instead — `no accepted move`, `no proposal`.
- **promote** — the proposals as a list, then the plan with the coordinates that proposal moves and the
  `command` line verbatim, then the gate `promote proposal <n> and rerun the ML chain for <TICKER>?`. *promote*
  runs `make ml-coordinate-search-promote ASSET=<TICKER> PROPOSAL=<n>`, whose second recipe line is the chain
  itself, so the chain's own lines stay on the screen as they come.
- **quit** — one `CANCELLED` line, nothing written, exit 0.

There is no **stop**: a hand stops a search with `tmux attach -t coordinate-search-<ticker>` and Ctrl-C, as
`make help` says. There is no **holdout**: F5 is computed by `ml-all`, which the promotion runs.

## What it starts, and how

`make`, and only `make` — one call, its lines uncaptured so they reach this terminal as they come, no `check`,
no `cwd`, no `env`, no timeout. tmux and docker compose are the Makefile's boundaries (`AGENTS.md`
§ Canonical vocabulary), and a TUI that spoke either would be a second place they are named. The terminal does
not even test whether tmux is on the `PATH`: when it is not, `make` says so in its own words and the failure
block carries them.

`PROPOSAL=` on the outer make line does nothing — the terminal always passes the rank a hand chose.

A state file older than the code is not read: the terminal and the search fail on the missing key. Delete
the file — the search writes a new one. A stage that guessed at a key it did not find would be guessing at
which experiment the file described.

## Exits

`skill_tui_designer.md` § Failures and exits, with one fact of its own: Ctrl-C ends the TUI with 130 and a
search already started stays in its session, because the session outlives the terminal that started it. A
failure block names what failed, where, why when it is known, and what a hand does next — no profile, no
catalogue, no recorded search, no proposal, more than one asset, no terminal on standard input, no gum, or a
`make` that exited non-zero.

## Design rationale

| object | why here | why beside these | why this boundary |
|---|---|---|---|
| the sub-module | the search's coordinates are the feature layer's own — the catalogue generates the columns a profile admits — and a hand steers the search from the layer that prepares what it searches | inside `module_features`, which owns the catalogue; not inside `module_ml`, which owns the loop that computes | it imports the standard library and its own package alone: it runs on the host's `python3` with gum and no virtual environment, and `module_features/config.py` imports numpy at its thirteenth line |
| `terminal.py` | the five actions and what each screen holds | it imports `config.py` and `tui.py` | it writes the one profile file and starts the two make targets; `-h`, `--help` and `--tickers` are its only arguments |
| `config.py` | the one surface of configuration | `terminal.py` imports it; `tui.py` imports it for plain output and the filter's placeholder alone | the store is read from the environment as in every `config.py`; the grid preset lives here, so another grid is an edit of the profile and not of the code |
| `tui.py` | how a screen is drawn and an answer taken | one file with the crawler's, twice by extraction and registered | it writes to the terminal and no file; it knows none of this sub-module's objects |
| the duplication | `module_features` may not import `module_skills` (D02), and a package for what two sub-modules share would be the `common` the contract refuses | — | it is paid on purpose: one `tui.py` and five screen helpers, registered in `module_skills/glossary.md` § Twice by extraction and changed on every side at once |
