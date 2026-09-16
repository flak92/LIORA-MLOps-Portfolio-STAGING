# Coordinate search terminal

The hand's instrument over the coordinate search: it drafts the asset's search profile, starts the search in
its own tmux session, reads the state that search writes, and promotes one of its proposals. Its rules are
`skill_coordinate_search_terminal.md`, beside this file, and the standards of its screens
`../../module_skills/skill_tui_designer.md`, which every TUI of this tree obeys.

```bash
make features-coordinate-search-terminal              # the TUI for the basket's one asset
make features-coordinate-search-terminal ASSET=BTC    # the TUI for one asset of a wider basket
STORE_ASSETS_ARTIFACTS_DIR=store/assets_artifacts python3 -B -m module_features.sub_module_coordinate_search_terminal.terminal --tickers BTC -h   # the actions, the keys, plain output and the exit codes
```

It computes nothing. It reads three files of the asset's folder — the feature layer's contract, the search's
own state and the profile — and writes one, `<TICKER>_coordinate_search_profile.json`, which is a hand's
decision and may equally be edited in the file. Everything that runs, runs through `make`: the Makefile is
where a container, a tmux session and the order of the chain are named.

| the file | what it is |
|---|---|
| `terminal.py` | the five actions and what each screen holds; the only file that calls `make` |
| `config.py` | the asset folder it reads, the one file it writes, the grid of each coordinate and the loops of a round |
| `tui.py` | how a screen is drawn and an answer taken — one file with `module_skills/sub_module_scalability_crawler/tui.py`, twice by extraction |
