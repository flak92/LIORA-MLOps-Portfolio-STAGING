"""The crawler's one surface of configuration: the snapshot's path, the files kept by hand, the reports' folder, the
documents sent with every file, the skills that are the skill matrix's columns and those an add preselects, the agent's
timeout and whether the TUI's output is plain. The sub-module's own files are read from its folder, a listed path, a
document and a skill from the root of the checkout."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

STORE_STATUS_DIR = Path(os.environ["STORE_STATUS_DIR"])
SKILLS_STATUS_JSON_PATH = STORE_STATUS_DIR / "skills_status.json"   # the snapshot status.py writes; the page reads it
SUB_MODULE_DIR = Path(__file__).resolve().parent                     # the sub-module's own files
# where a listed path and a rule are read from
REPO_ROOT = Path(subprocess.run(("git", "rev-parse", "--show-toplevel"), capture_output=True, text=True,
                                check=True).stdout.strip())
TO_CRAWL_MD_PATH = SUB_MODULE_DIR / "to_crawl.md"                                   # the skill matrix
CRAWLERS_MISSION_MD_PATH = SUB_MODULE_DIR / "crawlers_mission.md"                   # the mission
VENDORS_FOR_CRAWLING_TOML_PATH = SUB_MODULE_DIR / "vendors_for_crawling.toml"       # the vendors and their forms
REPORTS_AFTER_CRAWLED_FILES_DIR = SUB_MODULE_DIR / "reports_after_crawled_files"    # the root's tree, <path>.md
# the documents sent with every file, never a column of the skill matrix; {module}: the file's first path segment
SENT_DOCUMENT_PATHS = ("AGENTS.md", "module_skills/glossary.md",
                       "{module}/README_{module}.md")
# the skills, each a column of the skill matrix in the byte order of their paths — every module's skills/, the canon's
# and its sub-modules'; and those an add preselects — the canon's, those of the path's module ({module}) and those in
# the path's folder or a folder above it ({folder})
SKILL_PATHS = ("module_*/skills/*.md", "module_skills/skill_*.md", "module_*/sub_module_*/skill_*.md")
SKILL_PRESELECTED_PATHS = ("module_skills/skill_*.md", "{module}/skills/*.md", "{folder}/skill_*.md")
AGENT_TIMEOUT_MINUTES = 30
# plain output — state words in brackets, no colour, no symbol, no border: NO_COLOR set and not empty, TERM=dumb, or
# standard output not a terminal (module_skills/skill_tui_designer.md § Colour and plain output)
OUTPUT_PLAIN = (bool(os.environ.get("NO_COLOR")) or os.environ.get("TERM") == "dumb"
                or not sys.stdout.isatty())
PREVIEW_TABLE_LIMIT_ROWS = 10   # the files an add's preview lists before one line counts the rest
# twice by extraction
SECONDS_PER_MINUTE = 60
