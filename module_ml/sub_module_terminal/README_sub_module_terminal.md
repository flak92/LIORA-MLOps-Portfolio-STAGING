# ML terminal

The hand's instrument over the ML module: each asset's artifacts and the coordinate search recorded for it, then one
action — a stage of the chain (labels, hpo, train, strategy, status) or one of the search's own (draft, search,
recorded search, promote) — started through `make`; then it closes. Its rules are `skill_ml_terminal.md`, beside this
file, and the standards of its screens `../../module_skills/skill_tui_designer.md`, which every terminal of this tree
obeys.

```bash
make ml-terminal ASSET=BTC              # the TUI over one asset
make ml-terminal                        # the TUI over the basket
STORE_ASSETS_ARTIFACTS_DIR=store/assets_artifacts STORE_TRIALS_DIR=store/trials STORE_STATUS_DIR=store/status python3 -B -m module_ml.sub_module_terminal.terminal --tickers BTC -h   # the actions, the keys, plain output and the exit codes
```

It computes nothing. Per asset it reads the feature layer's contract, the search's own state and its ledger, and the
profile, and looks whether the four artifacts of the chain stand; it writes one file,
`<TICKER>_coordinate_search_profile.json`, which is a hand's decision and may equally be edited in the file. Everything
that runs, runs through `make`: the Makefile is where a stage is named, and where its container, the chain after a
promotion and the search's detached session are.

| the file | what it is |
|---|---|
| `terminal.py` | the opening screen and the nine actions, what each screen holds; the only file that calls `make` |
| `config.py` | the stages and what each writes, the make targets the search's actions start, the grid of each coordinate, the readers and the writer `module_ml/dataset.py` cannot lend a host without numpy, plain output |
| `tui.py` | how a screen is drawn and an answer taken — one file with every other terminal's and the crawler's, five times by extraction |
