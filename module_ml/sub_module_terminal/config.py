"""The ML terminal's one surface of configuration: the stages it offers, the make targets its coordinate-search actions
start, the grid each coordinate is searched over, the readers and the writer of the files it drafts and reads back, and
whether its output is plain.

It runs on the host, on `python3` and gum, with no virtual environment: it imports the standard library and its own
package alone. `module_ml/config.py` is standard library and is imported by terminal.py for the descriptors of every
file this terminal reads, the frozen geometry a coordinate is pinned to and the loops of a round; `module_ml/dataset.py`
is not — it imports duckdb and numpy — so the two readers and the writer of JSON it shares with that module are carried
here, twice by extraction."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MODULE_TOKEN = "ml"   # the module token of every stage this terminal starts: ml-<stage>
# the stages of this module's chain, in the Makefile's order — each an option of the menu, each the target ml-<stage>
STAGES = ("labels", "hpo", "train", "strategy", "status")
# what each stage writes, as the plan says it before the gate — the names of module_skills/glossary.md § Artifacts
WRITES_BY_STAGE = {
    "labels": "<TICKER>_label_events_<slot>.parquet",
    "hpo": "<TICKER>_parameters.json, and the asset's trial ledger in the trials store",
    "train": "<TICKER>_oos_predictions_<slot>.parquet, <TICKER>_model_evaluation.json",
    "strategy": "<TICKER>_strategy_evaluation.json",
    "status": "ml_status.json in the status store, and every complete asset's <TICKER>_README.md",
}
# the make targets the coordinate-search actions start, and nothing else: tmux and docker compose are the Makefile's
SEARCH_DETACHED_TARGET = "tmux-ml-coordinate-search"   # the Makefile's detached twin, alive after this terminal closes
SEARCH_TARGET = "ml-coordinate-search"                  # the module's own stage, in the foreground of this screen
PROMOTE_TARGET = "ml-coordinate-search-promote"
# the grid each coordinate is searched over — the one preset the terminal offers; another grid is a hand's edit of the
# profile itself, which is what "drafted, never derived" permits. Multipliers are multiples of a quarter, exact in
# binary, so a state's key compares them without a tolerance; a horizon is a duration token
GRID_BY_COORDINATE_DEFAULT = {
    "atr_barrier_multiplier": [1.75, 2.0, 2.25],
    "label_horizon": ["2h", "4h", "8h", "12h", "1d"],
    "stop_loss_atr_multiplier": [1.5, 2.0, 2.5],
    "take_profit_atr_multiplier": [1.5, 2.0, 2.5],
}


# twice by extraction
def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# twice by extraction
def load_jsonl(path: Path) -> list[dict]:
    """A ledger as it was written: one object a line, in the order they were appended."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# twice by extraction
def write_json(path: Path, payload: dict) -> None:
    """The canonical JSON form of this tree, equal by value to module_ml/dataset.py's — without to_json_safe(),
    which canonicalises numpy values this sub-module never holds. The same decisions write the same bytes, so a
    draft that changes nothing leaves git unmoved."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=1) + "\n", encoding="utf-8")


# plain output — state words in brackets, no colour, no symbol, no border: NO_COLOR set and not empty, TERM=dumb,
# or standard output not a terminal (module_skills/skill_tui_designer.md § Colour and plain output)
# twice by extraction
OUTPUT_PLAIN = (bool(os.environ.get("NO_COLOR")) or os.environ.get("TERM") == "dumb"
                or not sys.stdout.isatty())
