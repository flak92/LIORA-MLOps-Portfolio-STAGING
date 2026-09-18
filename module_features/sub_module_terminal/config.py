"""The features terminal's one surface of configuration: the stages it offers and what each writes, the store reads and
the descriptors of the files it shows a hand, and whether its output is plain.

It runs on the host, on `python3` and gum, with no virtual environment: it imports the standard library and its own
package alone. It cannot import `module_features/config.py` — its thirteenth line imports `.indicators`, and numpy
with it — so the two store reads and the three descriptors this terminal reads are carried here as registered
copies, twice by extraction (module_skills/glossary.md § Twice by extraction), each the same bytes as its owner's.
The stores are read from the two variables every stage of this module reads, so a shell that lacks one fails here,
at import, before a hand chooses a stage."""

from __future__ import annotations

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
def research_ohlcv_duckdb(ticker: str) -> Path:
    """The asset's own database — the market object's one home, resident in the asset folder."""
    return artifact_dir(ticker) / f"{ticker}_research_ohlcv.duckdb"


# twice by extraction
def catalogue_json(ticker: str):
    """The asset's copy of the feature layer's contract — what the ML layer reads instead of the feature configuration."""
    return artifact_dir(ticker) / f"{ticker}_catalogue.json"


MODULE_TOKEN = "features"   # the module token of every stage this terminal starts: features-<stage>
# the stages of this module's chain, in the Makefile's order — each an option of the menu, each the target features-<stage>
STAGES = ("bars", "catalogue", "status")
# what each stage writes, as the plan says it before the gate — the names of module_skills/glossary.md § Artifacts
WRITES_BY_STAGE = {
    "bars": "the aggregation tables of every timeframe of the register, in <TICKER>_research_ohlcv.duckdb",
    "catalogue": "<TICKER>_features_<slot>.parquet, one per timeframe, and <TICKER>_catalogue.json",
    "status": "features_status.json in the status store",
}
# plain output — state words in brackets, no colour, no symbol, no border: NO_COLOR set and not empty, TERM=dumb,
# or standard output not a terminal (module_skills/skill_tui_designer.md § Colour and plain output)
# twice by extraction
OUTPUT_PLAIN = (bool(os.environ.get("NO_COLOR")) or os.environ.get("TERM") == "dumb"
                or not sys.stdout.isatty())
