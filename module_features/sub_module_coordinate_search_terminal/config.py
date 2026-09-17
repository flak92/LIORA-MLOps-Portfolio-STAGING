"""The terminal's one surface of configuration: the asset folder it reads and the one file it writes, the grid
each coordinate is searched over, the loops of a round, and whether its output is plain.

It runs on the host, on `python3` and gum, with no virtual environment: so it imports the standard library and
its own package, and nothing else. `module_features/config.py` is not among its imports — that module imports
numpy at its thirteenth line, through the indicator register — and neither is any module of `module_ml`, whose
files it only ever reads as JSON. Every stage it starts, it starts through `make`."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# twice by extraction
STORE_ASSETS_ARTIFACTS_DIR = Path(os.environ["STORE_ASSETS_ARTIFACTS_DIR"])


# twice by extraction
def artifact_dir(ticker: str) -> Path:
    """One directory per ticker; inside it one file per artifact, named for it."""
    return STORE_ASSETS_ARTIFACTS_DIR / ticker


# twice by extraction
def catalogue_json(ticker: str) -> Path:
    """The asset's copy of the feature layer's contract — what the ML layer reads instead of the feature configuration."""
    return artifact_dir(ticker) / f"{ticker}_catalogue.json"


# twice by extraction
def coordinate_search_json(ticker: str) -> Path:
    """Where the search stood when a round began: what it was conditioned on, its beam, its champion, the
    path it took and the states it proposes. Written at the top of a round, so it is on disk before the
    ledger beside it — the trials themselves — holds its first line."""
    return artifact_dir(ticker) / f"{ticker}_coordinate_search.json"


# twice by extraction
def coordinate_search_trials_jsonl(ticker: str) -> Path:
    """The search's ledger: one scored state a line, appended and never rewritten."""
    return artifact_dir(ticker) / f"{ticker}_coordinate_search_trials.jsonl"


# twice by extraction
def load_jsonl(path: Path) -> list[dict]:
    """A ledger as it was written: one object a line, in the order they were appended."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# twice by extraction
def coordinate_search_profile_json(ticker: str) -> Path:
    """What a hand asks the search to look at: the columns admitted, the state to start from, the grid of
    each coordinate and the loops of a round. Drafted, never derived."""
    return artifact_dir(ticker) / f"{ticker}_coordinate_search_profile.json"


# twice by extraction
def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# twice by extraction
def write_json(path: Path, payload: dict) -> None:
    """The canonical JSON form of this tree, equal by value to module_ml/dataset.py's — without to_json_safe(),
    which canonicalises numpy values this sub-module never holds. The same decisions write the same bytes, so a
    draft that changes nothing leaves git unmoved."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=1) + "\n", encoding="utf-8")


# the grid each coordinate is searched over — the one preset the terminal offers; another grid is a hand's
# edit of the profile itself, which is what "drafted, never derived" permits. Multipliers are multiples of a
# quarter, exact in binary, so a state's key compares them without a tolerance; a horizon is a duration token
GRID_BY_COORDINATE_DEFAULT = {
    "atr_barrier_multiplier": [1.75, 2.0, 2.25],
    "label_horizon": ["2h", "4h", "8h", "12h", "1d"],
    "stop_loss_atr_multiplier": [1.5, 2.0, 2.5],
    "take_profit_atr_multiplier": [1.5, 2.0, 2.5],
}
# where a coordinate sits when a hand does not search it: its grid becomes this one point. A grid must
# contain the state it starts from, and a grid of one point offers no neighbour, so the family makes no move
# and the kernel needs no case for it. These are the experiment's frozen geometry, which `load_barriers()` in
# module_ml/dataset.py falls back to when no promotion has written one
# twice by extraction
START_BY_COORDINATE_DEFAULT = {
    "atr_barrier_multiplier": 2.0,
    "label_horizon": "4h",
    "stop_loss_atr_multiplier": 2.0,
    "take_profit_atr_multiplier": 2.0,
}
# the loops of a round, in the frozen order a round applies them — module_ml/config.py carries the same tuple
ROUND_LOOPS = ("barrier", "feature_set", "hpo")
# the two make targets this terminal starts, and nothing else: tmux and docker compose are the Makefile's
SEARCH_TARGET = "tmux-ml-coordinate-search"
PROMOTE_TARGET = "ml-coordinate-search-promote"
# twice by extraction
FILTER_PLACEHOLDER = "type part of a path — module_data/config.py or module_data"
# plain output — state words in brackets, no colour, no symbol, no border: NO_COLOR set and not empty, TERM=dumb,
# or standard output not a terminal (module_skills/skill_tui_designer.md § Colour and plain output)
# twice by extraction
OUTPUT_PLAIN = (bool(os.environ.get("NO_COLOR")) or os.environ.get("TERM") == "dumb"
                or not sys.stdout.isatty())
