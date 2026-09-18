"""The data terminal's one surface of configuration: the stages it offers, what each writes, and whether its
output is plain.

It runs on the host, on `python3` and gum, with no virtual environment: it imports the standard library and its own
package alone. `module_data/config.py` is standard library and is imported by terminal.py for the venues and the
descriptors of every path this terminal reads — each venue's raw leaf and the asset's database — so no descriptor
is carried here; what is carried, twice by extraction, is the plain-output conditions and the filter's placeholder
every `tui.py` reads from its own `config.py`."""

from __future__ import annotations

import os
import sys

MODULE_TOKEN = "data"   # the module token of every stage this terminal starts: data-<stage>
# the stages of this module's chain, in the Makefile's order — each an option of the menu, each the target data-<stage>
STAGES = ("download", "ingest", "status")
# what each stage writes, as the plan says it before the gate — the names of module_skills/glossary.md § Stores
WRITES_BY_STAGE = {
    "download": "one Lean day ZIP per venue and UTC day into the raw store, days already there skipped",
    "ingest": "<TICKER>_research_ohlcv.duckdb — the two venue tables and the canonical series",
    "status": "data_status.json in the status store",
}
# plain output — state words in brackets, no colour, no symbol, no border: NO_COLOR set and not empty, TERM=dumb,
# or standard output not a terminal (module_skills/skill_tui_designer.md § Colour and plain output)
# twice by extraction
OUTPUT_PLAIN = (bool(os.environ.get("NO_COLOR")) or os.environ.get("TERM") == "dumb"
                or not sys.stdout.isatty())
