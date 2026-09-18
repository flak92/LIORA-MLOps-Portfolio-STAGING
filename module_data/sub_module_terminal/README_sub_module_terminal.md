# Data terminal

The hand's instrument over the data module: each asset's raw days and its database, then one stage — download,
ingest or status — started through `make`; then it closes. Its rules are `skill_data_terminal.md`, beside this
file, and the standards of its screens `../skill_tui_designer.md`, which every terminal of this
tree obeys.

```bash
make data-terminal ASSET=BTC            # the TUI over one asset (in this repository)
make data-terminal                      # the TUI over the basket (at the workspace)
STORE_RAW_1M_DIR=store/raw_1m STORE_ASSETS_ARTIFACTS_DIR=../store_assets_artifacts STORE_STATUS_DIR=../store_status python3 -B -m module_data.sub_module_terminal.terminal --tickers BTC -h   # the actions, the keys, plain output and the exit codes
```

It computes nothing and writes nothing of its own: the venues, the raw leaf and the database it reads through this
module's own `config.py` and `lean.py`, and everything that runs, runs through `make` — the Makefile is where the
module's stages are named.

| the file | what it is |
|---|---|
| `terminal.py` | the opening screen and the one stage; the only file that calls `make` |
| `config.py` | the stages and what each writes, plain output |
| `tui.py` | how a screen is drawn and an answer taken — one file with every other terminal's and the crawler's, seven times by extraction |
