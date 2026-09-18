"""The monitoring terminal's one surface of configuration: the snapshots it shows, the two positions of the
presentation switch it starts through `make` and what each writes, and whether its output is plain.

It runs on the host, on `python3` and gum, with no virtual environment: it imports the standard library and its own
package alone. `module_monitoring/config.py` is standard library and is imported by terminal.py for the two stores this
terminal reads — the status store through `store_status_file()`, the run records through `STORE_RUN_RECORDS_DIR` —
so no path is carried here; what is carried, twice by extraction, is the one reader of JSON the dashboard's `serve.py`
holds, and the plain-output conditions and the filter's placeholder every `tui.py` reads from its own `config.py`."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MODULE_TOKEN = "monitoring"   # the module token of this module's own target, monitoring-terminal; the switch goes bare
# the presentation switch, in the Makefile's order — each an option of the menu; a lifecycle pair, so its two targets
# go bare, `on` and `off` (AGENTS.md § Canonical vocabulary, the Makefile-targets row)
STAGES = ("on", "off")
# what each position writes, as the plan says it before the gate
WRITES_BY_STAGE = {
    "on": "nothing — the dashboard and the DevOps panel up, the page's address printed",
    "off": "nothing — every container of this project removed",
}
# the four snapshots the dashboard reads, by file name in the status store (module_skills/glossary.md § Stores)
SNAPSHOT_FILE_NAMES = ("data_status.json", "features_status.json", "ml_status.json", "skills_status.json")


# twice by extraction
def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# plain output — state words in brackets, no colour, no symbol, no border: NO_COLOR set and not empty, TERM=dumb, or
# standard output not a terminal (module_skills/skill_tui_designer.md § Colour and plain output)
# twice by extraction
OUTPUT_PLAIN = (bool(os.environ.get("NO_COLOR")) or os.environ.get("TERM") == "dumb"
                or not sys.stdout.isatty())
