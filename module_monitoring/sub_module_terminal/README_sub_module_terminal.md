# Monitoring terminal

The hand's instrument over the monitoring module: the four snapshots the dashboard reads and the runs the recorder
left, then one position of the presentation switch — on or off — started through `make`; then it closes. Its rules
are `skill_monitoring_terminal.md`, beside this file, and the standards of its screens
`../skill_tui_designer.md`, which every terminal of this tree obeys.

```bash
make monitoring-terminal                                # the TUI over the stores one level up (from the workspace root, or from this repository)
STORE_STATUS_DIR=/path make monitoring-terminal         # the TUI over another status store
STORE_RUN_RECORDS_DIR=../store_run_records STORE_STATUS_DIR=../store_status python3 -B -m module_monitoring.sub_module_terminal.terminal -h   # the actions, the keys, plain output and the exit codes
```

It computes nothing and writes nothing: the snapshots and the run records it reads through this module's own
`config.py`, and everything that runs, runs through `make` — the Makefile is where a container is named, and at the
workspace the two residents.

| the file | what it is |
|---|---|
| `terminal.py` | the opening screen and the one action; the only file that calls `make` |
| `config.py` | the snapshots it shows, the two positions of the switch and what each writes, plain output |
| `tui.py` | how a screen is drawn and an answer taken — one file with every other terminal's and the crawler's, seven times by extraction |
