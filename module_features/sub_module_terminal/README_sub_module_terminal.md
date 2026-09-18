# Features terminal

The hand's instrument over the feature module: each asset's database, its contract and its feature parquets, then
one stage — bars, catalogue or status — started through `make`; then it closes. Its rules are
`skill_features_terminal.md`, beside this file, and the standards of its screens
`../../module_skills/skill_tui_designer.md`, which every terminal of this tree obeys.

```bash
make features-terminal                  # the TUI over the basket
make features-terminal ASSET=BTC        # the TUI over one asset — ASSET= names it, as for every stage
STORE_ASSETS_ARTIFACTS_DIR=store/assets_artifacts STORE_STATUS_DIR=store/status python3 -B -m module_features.sub_module_terminal.terminal --tickers BTC -h   # the stages, the keys, plain output and the exit codes
```

It computes nothing and writes nothing of its own: whether an asset's database, its contract and its parquets stand
it reads off the artifacts store by the descriptors `config.py` carries, and everything that runs, runs through
`make` — the Makefile is where a container and the order of the chain are named.

| the file | what it is |
|---|---|
| `terminal.py` | the opening screen and the one stage; the only file that calls `make` |
| `config.py` | the store reads and the descriptors of the files it shows — registered copies, because `module_features/config.py` imports numpy —, the stages and what each writes, plain output |
| `tui.py` | how a screen is drawn and an answer taken — one file with every other terminal's and the crawler's, five times by extraction |
