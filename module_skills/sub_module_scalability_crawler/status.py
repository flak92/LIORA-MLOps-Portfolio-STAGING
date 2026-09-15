"""The crawler's snapshot, store/status/skills_status.json: every file to_crawl.md lists, how often it was crawled and
when last — a function of the skill matrix's paths and the reports, read off the dates of the reports' headings and
never a clock; and the skill matrix's one rule, which the TUI reads too.

    python3 -B -m module_skills.sub_module_scalability_crawler.status      (make skills-status)
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config

REPORT_HEADING_PREFIX = "## crawled "   # then <YYYY-MM-DD HH:MM> UTC · <vendor> · <labels> · <commit> · skills: <stems>
SKILL_MATRIX_PATH_COLUMN = "path"       # the header of the skill matrix's first column; every other is a skill's stem
SKILL_MARK = "X"                        # a cell where the skill of its column acts on the crawl of its row's path


def load_entry_paths(entry: str) -> list[str]:
    """The files one entry of to_crawl.md names, relative to the root: a folder stands for every file under it, in byte
    order, but the bytecode of __pycache__ and the reports this crawler wrote. An entry holding `|`, one that names
    nothing, or a file that is not UTF-8, is refused in one line, a SystemExit: it ends make skills-status, and the TUI
    shows it."""
    if "|" in entry:
        raise SystemExit(f"to_crawl.md: {entry} holds |, which ends a cell of the table")
    named = config.REPO_ROOT / entry
    if not (named.is_dir() or named.is_file()):
        raise SystemExit(f"to_crawl.md: {entry} names nothing")
    found = sorted(str(path.relative_to(config.REPO_ROOT)) for path in named.rglob("*") if path.is_file()
                   and "__pycache__" not in path.parts and config.REPORTS_AFTER_CRAWLED_FILES_DIR not in path.parents) \
        if named.is_dir() else [str(named.relative_to(config.REPO_ROOT))]
    for path in found:
        try:
            (config.REPO_ROOT / path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise SystemExit(f"to_crawl.md: {entry} — {path} is not UTF-8")
    return found


def load_skill_paths() -> list[str]:
    """Every skill of the tree, relative to the root, in byte order — the matches of SKILL_PATHS, the skill matrix's
    columns. Two skills of one stem are refused in one line, a column being named by its stem."""
    skills = sorted({str(found.relative_to(config.REPO_ROOT)) for pattern in config.SKILL_PATHS
                     for found in config.REPO_ROOT.glob(pattern)})
    stems = [Path(skill).stem for skill in skills]
    twice = next((stem for stem in stems if stems.count(stem) > 1), None)
    if twice:
        raise SystemExit(f"SKILL_PATHS: two skills share the stem {twice}, which names one column of to_crawl.md")
    return skills


def load_skill_matrix() -> dict[str, list[str]]:
    """to_crawl.md, the skill matrix: each listed path in the table's order with the skills its row marks, in the
    columns' order; a skill no column names is unmarked, and an empty file lists nothing. A line that is not a row, a
    first column not headed `path`, a column naming no skill or written twice, a row of another width, a header without
    its separator, a row naming no path or a path listed twice, or a cell but X or empty is refused in one line, a
    SystemExit: it ends make skills-status, and the TUI shows it."""
    stems = {Path(skill).stem: skill for skill in load_skill_paths()}
    rows = []
    for number, line in enumerate(config.TO_CRAWL_MD_PATH.read_text(encoding="utf-8").rstrip().splitlines(), 1):
        line = line.strip()
        if len(line) < 2 or not line.startswith("|") or not line.endswith("|"):
            raise SystemExit(f"to_crawl.md: line {number} is not a row of the table")
        rows.append((number, [cell.strip() for cell in line[1:-1].split("|")]))
    if not rows:
        return {}
    (_, header), *body = rows
    if header[0] != SKILL_MATRIX_PATH_COLUMN:
        raise SystemExit(f"to_crawl.md: the first column is headed {header[0]}, not {SKILL_MATRIX_PATH_COLUMN}")
    for stem in header[1:]:
        if stem not in stems:
            raise SystemExit(f"to_crawl.md: column {stem} names no skill of the tree")
        if header.count(stem) > 1:
            raise SystemExit(f"to_crawl.md: column {stem} is written twice")
    for number, cells in body:
        if len(cells) != len(header):
            raise SystemExit(f"to_crawl.md: line {number} has {len(cells)} cells, the header {len(header)}")
    if not body or not all(cell and set(cell) <= set("-:") for cell in body[0][1]):
        raise SystemExit("to_crawl.md: the header is not followed by its separator row")
    marks = {}
    for number, (path, *cells) in body[1:]:
        if not path:
            raise SystemExit(f"to_crawl.md: line {number} names no path")
        if path in marks:
            raise SystemExit(f"to_crawl.md: {path} is listed twice")
        for stem, cell in zip(header[1:], cells):
            if cell not in (SKILL_MARK, ""):
                raise SystemExit(f"to_crawl.md: {path} holds {cell} under {stem}, not {SKILL_MARK} or empty")
        marks[path] = sorted(stems[stem] for stem, cell in zip(header[1:], cells) if cell == SKILL_MARK)
    return marks


def load_crawl_paths() -> list[str]:
    """The files to_crawl.md names, in its rows' order, each entry's by load_entry_paths()."""
    return [path for entry in load_skill_matrix() for path in load_entry_paths(entry)]


def report_path(path: str) -> Path:
    return config.REPORTS_AFTER_CRAWLED_FILES_DIR / f"{path}.md"


def load_file_row(path: str) -> dict:
    """One listed file's row of the snapshot: its path, its report, how often it was crawled and when last, read off the
    dates of the report's headings."""
    report = report_path(path)
    lines = report.read_text(encoding="utf-8").splitlines() if report.is_file() else []
    stamps = [line[len(REPORT_HEADING_PREFIX):len(REPORT_HEADING_PREFIX) + len("YYYY-MM-DD HH:MM")] for line in lines
              if line.startswith(REPORT_HEADING_PREFIX)]
    return {"path": path, "report": str(report.relative_to(config.SUB_MODULE_DIR)),
            "crawl_count": len(stamps), "last_crawled_utc": stamps[-1] if stamps else None}


def build_skills_status() -> dict:
    return {"files": [load_file_row(path) for path in sorted(load_crawl_paths())]}


def main() -> int:
    config.SKILLS_STATUS_JSON_PATH.write_text(json.dumps(build_skills_status(), sort_keys=True, indent=1) + "\n",
                                              encoding="utf-8")
    print(f"wrote {config.SKILLS_STATUS_JSON_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
