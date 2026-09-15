"""The crawler's text-based user interface (TUI) and its crawl: the listed paths and the skill matrix, then one action a
hand chooses in the menu — crawl, add a path, mark skills or remove a path — its forms and its result, drawn by tui.py to
skill_tui_designer.md; then it closes.

keys:
  Enter takes the option under the cursor; x toggles a file or a skill; Esc cancels and writes nothing (exit 0); Ctrl-C
  ends the TUI (exit 130), and the reports a crawl already wrote stay.

output is plain — state words in brackets, no colour, no symbol, no border — when NO_COLOR is set and not empty, TERM
is dumb or standard output is not a terminal; the words, the order and the counts are the same in both.

exit codes:
  0 the action done, or cancelled with nothing written; 1 a failure, named last on stderr; 2 an unknown argument;
  130 Ctrl-C

examples:
  make skills-crawl               the TUI
  NO_COLOR=1 make skills-crawl    the TUI in plain output
  make skills-status              the snapshot alone, without the TUI
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import time
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from . import config, status, tui

VENDOR_FORMS = ("model", "effort", "permissions")   # the forms asked after the vendor, in this order, each its table has
FILE_COLUMNS = ("#", "file", "last crawl (UTC)", "crawls", "skills")   # a listed file, in every table and list of files
FILE_COLUMNS_DROP_ORDER = ("skills", "crawls", "last crawl (UTC)")    # the file columns a narrow terminal leaves out


def load_active_vendors() -> dict[str, dict]:
    """The tables of vendors_for_crawling.toml whose `active` is true, in the file's order."""
    tables = tomllib.loads(config.VENDORS_FOR_CRAWLING_TOML_PATH.read_text(encoding="utf-8"))
    return {name: table for name, table in tables.items() if table["active"]}


def load_repository_paths() -> list[str]:
    """Every path an add offers, off git: the files it tracks or does not ignore and the folders above them, in byte
    order, the reports left out."""
    output = subprocess.run(("git", "-C", config.REPO_ROOT, "ls-files", "-z", "--cached", "--others",
                             "--exclude-standard"), capture_output=True, text=True, check=True).stdout
    files = [path for path in output.split("\0") if path]
    folders = {str(parent) for path in files for parent in Path(path).parents if parent != Path(".")}
    reports = str(config.REPORTS_AFTER_CRAWLED_FILES_DIR.relative_to(config.REPO_ROOT))
    return sorted(path for path in {*files, *folders} if path != reports and not path.startswith(f"{reports}/"))


def load_preselected_skills(entry: str, skills: list[str]) -> list[str]:
    """The skills an add preselects for entry, in the skill matrix's column order: the matches of
    SKILL_PRESELECTED_PATHS, the entry's first path segment as {module}, the entry and each folder above it as {folder}."""
    parts = Path(entry).parts
    patterns = {pattern.format(module=parts[0], folder=Path(*parts[:end])) for pattern in config.SKILL_PRESELECTED_PATHS
                for end in range(1, len(parts) + 1)}
    found = {str(path.relative_to(config.REPO_ROOT)) for pattern in patterns for path in config.REPO_ROOT.glob(pattern)}
    return [skill for skill in skills if skill in found]


def _load_documents_text(documents: list[str]) -> str:
    """Each document under `## <path>`, its text as it stands; `none` when there is none."""
    return "\n".join(f"## {document}\n{(config.REPO_ROOT / document).read_text(encoding='utf-8').rstrip('\n')}"
                     for document in documents) or "none"


def load_rules_text(path: str, marked: list[str]) -> str:
    """What one listed file is read against, each document under its path: `# Rules`, the matches of
    SENT_DOCUMENT_PATHS with the file's first path segment as {module}, the patterns in order, each one's matches
    sorted; then `# Skills marked for this file`, the skills its row marks, in the skill matrix's column order."""
    root, module = config.REPO_ROOT, Path(path).parts[0]
    rules = [str(found.relative_to(root)) for pattern in config.SENT_DOCUMENT_PATHS
             for found in sorted(root.glob(pattern.format(module=module)))]
    return f"# Rules\n{_load_documents_text(rules)}\n\n# Skills marked for this file\n{_load_documents_text(marked)}"


def build_message(mission: str, rules: str, unmarked: list[str], path: str) -> str:
    """The mission, the rules and the marked skills, every unmarked skill by its path alone, then the file under review,
    each line after its number: all the agent reads, in one."""
    lines = (config.REPO_ROOT / path).read_text(encoding="utf-8").splitlines()
    text = "\n".join(f"{number:>4}  {line}" for number, line in enumerate(lines, 1))
    listing = "\n".join(f"- `{skill}`" for skill in unmarked) or "none"
    return (f"{mission.rstrip('\n')}\n\n{rules}\n\n# Skills not marked for this file\n{listing}\n\n"
            f"# File under review: {path}\n{text}\n")


def write_report_entry(path: str, fields: list[str], answer: str) -> None:
    """A blank line, `## crawled <UTC now> · <fields>`, the answer as it came and a blank line, at the report's end."""
    report = status.report_path(path)
    report.parent.mkdir(parents=True, exist_ok=True)
    heading = f"{status.REPORT_HEADING_PREFIX}{datetime.now(UTC):%Y-%m-%d %H:%M} UTC · {' · '.join(fields)}"
    with report.open("a", encoding="utf-8") as handle:
        handle.write(f"\n{heading}\n{answer}" + ("\n" if answer.endswith("\n") else "\n\n"))


def write_skill_matrix(marks: dict[str, list[str]], skills: list[str]) -> None:
    """to_crawl.md as an add, a mark or a remove leaves it: the header — `path`, then each skill of the tree by its stem,
    so a skill new to the tree gains its column here — the separator, and a row per listed path in its order, X under
    each skill it marks; every column as wide as its widest cell, so the same marks write the same bytes."""
    rows = [[status.SKILL_MATRIX_PATH_COLUMN, *(Path(skill).stem for skill in skills)],
            *([entry, *(status.SKILL_MARK if skill in marked else "" for skill in skills)]
              for entry, marked in marks.items())]
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    lines = [f"| {' | '.join(cell.ljust(width) for cell, width in zip(row, widths))} |" for row in rows]
    separator = f"|{'|'.join('-' * (width + 2) for width in widths)}|"
    config.TO_CRAWL_MD_PATH.write_text("\n".join([lines[0], separator, *lines[1:]]) + "\n", encoding="utf-8")


def build_command(vendor: dict, chosen: dict[str, str]) -> tuple[list[str], list[str]]:
    """`command`, then the args of the option chosen in each form the vendor's table has, in VENDOR_FORMS' order, and
    the chosen labels."""
    labels = [chosen[form] for form in VENDOR_FORMS if vendor.get(form)]
    args = [next(option["args"] for option in vendor[form] if option["label"] == chosen[form])
            for form in VENDOR_FORMS if vendor.get(form)]
    return [*vendor["command"], *(arg for option_args in args for arg in option_args)], labels


def _skills_field(marked: list[str]) -> str:
    """A report heading's last field: `skills: <the marked skills' stems>`, or `skills: none`."""
    return f"skills: {', '.join(Path(skill).stem for skill in marked) or 'none'}"


def _load_entries(marks: dict[str, list[str]]) -> list[dict]:
    """Each listed entry with its kind, its marked skills and the snapshot's rows of the files it names — or, for one
    the skill matrix's rule refuses, that rule's one line as `refusal`, so the entry stays on the screen and removable."""
    entries = []
    for entry, marked in marks.items():
        try:
            paths = status.load_entry_paths(entry)
        except SystemExit as refusal:
            entries.append({"entry": entry, "kind": "—", "skills": marked, "rows": [], "refusal": str(refusal.code)})
            continue
        entries.append({"entry": entry, "kind": "folder" if (config.REPO_ROOT / entry).is_dir() else "file",
                        "skills": marked, "rows": [status.load_file_row(path) for path in paths], "refusal": None})
    return entries


def _queue_rows(entries: list[dict]) -> list[dict]:
    """The snapshot's rows of the listed files, in the skill matrix's order — the queue — each file once, with the
    skills every entry naming it marks, in the columns' order."""
    queue = {}
    for entry in entries:
        for row in entry["rows"]:
            queue.setdefault(row["path"], {**row, "skills": set()})["skills"].update(entry["skills"])
    return [{**row, "skills": sorted(row["skills"])} for row in queue.values()]


def _file_rows(rows: list[dict]) -> list[dict]:
    """The FILE_COLUMNS of the queue's rows, numbered in their order."""
    return [{"#": number, "file": row["path"], "last crawl (UTC)": row["last_crawled_utc"] or "never",
             "crawls": row["crawl_count"], "skills": len(row["skills"])} for number, row in enumerate(rows, 1)]


def _skill_rows(skills: list[str], entries: list[dict]) -> list[dict]:
    """The skill matrix turned for the terminal's width: a row per skill by its stem, X under the # of each listed path
    whose row marks it."""
    return [{"skill": Path(skill).stem, **{str(number): status.SKILL_MARK if skill in entry["skills"] else ""
                                           for number, entry in enumerate(entries, 1)}} for skill in skills]


def _option_rows(*options: str) -> list[dict]:
    return [{"option": option} for option in options]


def _step_rows(steps: list[str], chosen: dict[str, str]) -> list[dict]:
    """The crawl's steps in order: each answered DONE with its choice, the first unanswered CURRENT, the rest PENDING."""
    current = next(step for step in steps if step not in chosen)
    return [{"step": step, "state": tui.state_label("DONE" if step in chosen else "CURRENT" if step == current
                                                    else "PENDING"),
             "choice": chosen[step] if step in chosen else "select now" if step == current else "—"} for step in steps]


def _step_answer(steps: list[str], chosen: dict[str, str], rows: list[dict], value_column: str,
                 drop_order: tuple[str, ...] = (), selected: list[str] | None = None) -> str | None:
    """The answer to the crawl's current step under the steps table; a step of one option draws nothing, gum answering
    it, and the next steps table shows it DONE."""
    step = next(step for step in steps if step not in chosen)
    if len(rows) > 1:
        tui.gum_table(("step", "state", "choice"), _step_rows(steps, chosen))
        print()
    return tui.gum_choose(step, rows, value_column, drop_order, selected)


def _skills_answer(entry: str, skills: list[str], preselected: list[str]) -> list[str] | None:
    """The skills a hand marks for entry in the form `skills for <entry>`, in the skill matrix's column order, the
    preselected ones chosen at the start; None for Esc."""
    answer = tui.gum_choose(f"skills for {entry}", [{"skill": Path(skill).stem, "path": skill} for skill in skills],
                            "path", ("path",), selected=preselected)
    return None if answer is None else [skill for skill in skills if skill in answer.splitlines()]


def _cancelled_exit_code() -> int:
    """Esc, cancel or quit: one line, nothing written, exit 0."""
    print(f"{tui.state_label('CANCELLED')}  nothing written")
    return 0


def _failure_exit_code(what: str, where: str, why: str | None, next_action: str) -> int:
    """A failure as the run's last block, on stderr: exit 1."""
    tui.gum_style(tui.error_lines(what, where, why, next_action), "ERROR", sys.stderr)
    return 1


def _write_crawl_reports(vendors: dict[str, dict], entries: list[dict], skills: list[str]) -> int:
    refused = next((entry for entry in entries if entry["refusal"]), None)
    if refused:
        return _failure_exit_code("the crawl cannot start", f"to_crawl.md: {refused['entry']}", refused["refusal"],
                                  "take it out through remove a path, or mend it in to_crawl.md")
    queue = _queue_rows(entries)
    if not queue:
        return _failure_exit_code("nothing to crawl", "to_crawl.md", "the skill matrix names no file",
                                  "add a path first")
    while True:   # one pass per plan; back at the plan starts again at the vendor, every default preselected
        chosen = {"action": "crawl"}
        name = _step_answer(["action", "vendor", "the vendor's forms", "files to crawl", "plan"], chosen,
                            [{"vendor": vendor_name, "on PATH": "yes" if shutil.which(vendor["command"][0]) else "no",
                              "command": shlex.join(vendor["command"])} for vendor_name, vendor in vendors.items()],
                            "vendor", ("command",))
        if not name:
            return _cancelled_exit_code()
        vendor, chosen["vendor"] = vendors[name], name
        if not shutil.which(vendor["command"][0]):
            return _failure_exit_code(f"{vendor['command'][0]} is not on PATH", f"vendors_for_crawling.toml: [{name}]",
                                      None, "install it and log in, or choose another vendor")
        forms = [form for form in VENDOR_FORMS if vendor.get(form)]
        steps = ["action", "vendor", *forms, "files to crawl", "plan"]
        for form in forms:
            label = _step_answer(steps, chosen, [{"label": option["label"], "args": shlex.join(option["args"])}
                                                 for option in vendor[form]], "label", ("args",))
            if not label:
                return _cancelled_exit_code()
            chosen[form] = label
        answer = _step_answer(steps, chosen, _file_rows(queue), "file", FILE_COLUMNS_DROP_ORDER,
                              selected=[row["path"] for row in queue])
        if not answer:
            return _cancelled_exit_code()
        crawled_rows = [row for row in queue if row["path"] in answer.splitlines()]
        chosen["files to crawl"] = f"{len(crawled_rows)} of {len(queue)} files"
        command, labels = build_command(vendor, chosen)
        commit = subprocess.check_output(("git", "-C", config.REPO_ROOT, "rev-parse", "--short", "HEAD"),
                                         text=True).strip()
        skills_fields = {_skills_field(row["skills"]) for row in crawled_rows}
        tui.gum_table(("parameter", "value"), [
            {"parameter": "vendor", "value": name}, *({"parameter": form, "value": chosen[form]} for form in forms),
            {"parameter": "files to crawl", "value": chosen["files to crawl"]},
            {"parameter": "timeout per file", "value": f"{config.AGENT_TIMEOUT_MINUTES} minutes"},
            {"parameter": "reports", "value": "reports_after_crawled_files/<file>.md, one entry appended to each"}])
        print(f"command         {shlex.join(command)}  < the mission, the rules, the marked skills and the file")
        print(f"report heading  {status.REPORT_HEADING_PREFIX}<YYYY-MM-DD HH:MM> UTC · "
              f"{' · '.join([name, *labels, commit])} · "
              f"{skills_fields.pop() if len(skills_fields) == 1 else "skills: <each file's marked skills>"}")
        print()
        tui.gum_table(FILE_COLUMNS, _file_rows(crawled_rows), FILE_COLUMNS_DROP_ORDER)
        print()
        decision = tui.gum_choose(f"crawl {len(crawled_rows)} files with {name}?",
                                  _option_rows("crawl", "back", "cancel"), "option")
        if decision == "crawl":
            break
        if decision != "back":
            return _cancelled_exit_code()
        print()
    mission = config.CRAWLERS_MISSION_MD_PATH.read_text(encoding="utf-8")
    results, failure = [], None
    print()
    try:
        try:
            for number, row in enumerate(crawled_rows, 1):
                path, marked = row["path"], row["skills"]
                print(f"[{number}/{len(crawled_rows)}] {tui.state_label('CRAWLING')}  {path} · {name}", flush=True)
                started_seconds = time.monotonic()
                try:
                    message = build_message(mission, load_rules_text(path, marked),
                                            [skill for skill in skills if skill not in marked and skill != path], path)
                    answer = subprocess.run(command, input=message, stdout=subprocess.PIPE, text=True,
                                            timeout=config.AGENT_TIMEOUT_MINUTES * config.SECONDS_PER_MINUTE)
                    why = (f"the agent exited with {answer.returncode}" if answer.returncode != 0
                           else "the agent's answer was empty" if not answer.stdout.strip() else None)
                except subprocess.TimeoutExpired:
                    why = f"the agent ran past {config.AGENT_TIMEOUT_MINUTES} minutes"
                elapsed_seconds = round(time.monotonic() - started_seconds)
                if why is None:
                    write_report_entry(path, [name, *labels, commit, _skills_field(marked)], answer.stdout)
                result = tui.state_label("FAILED" if why else "DONE")
                print(f"[{number}/{len(crawled_rows)}] {result}  {path}  {elapsed_seconds} s", flush=True)
                results.append({"#": number, "file": path, "result": result, "time": f"{elapsed_seconds} s",
                                "report": row["report"]})
                if why:
                    failure = (path, why)
                    break
        finally:
            status.main()   # after a crawl began, always: a failed or an interrupted one too
    except KeyboardInterrupt:
        print(f"{tui.state_label('CANCELLED')}  the crawl was interrupted at [{len(results) + 1}/{len(crawled_rows)}] — "
              f"the reports already written stay", file=sys.stderr)
        return tui.INTERRUPTED_EXIT_CODE
    results += [{"#": number, "file": row["path"], "result": tui.state_label("NOT CRAWLED"), "time": "—",
                 "report": row["report"]}
                for number, row in enumerate(crawled_rows[len(results):], len(results) + 1)]
    print()
    tui.gum_table(("#", "file", "result", "time", "report"), results, ("report", "time"))
    print()
    done = sum(1 for result_row in results if result_row["result"] == tui.state_label("DONE"))
    if failure:
        return _failure_exit_code(f"the crawl ended at {failure[0]} — {done} of {len(crawled_rows)} files crawled",
                                  failure[0], failure[1], "read the agent's lines above, then make skills-crawl again; "
                                  "the reports already written stay")
    tui.gum_style([f"{tui.state_label('DONE')}  crawled {done} of {len(crawled_rows)} files with "
                   f"{' · '.join([name, *labels])}"], "DONE")
    return 0


def _write_added_path(marks: dict[str, list[str]], skills: list[str]) -> int:
    print(f"repository root  {config.REPO_ROOT}")
    print()
    listed_paths = {str(Path(entry)) for entry in marks}
    candidates = [path for path in load_repository_paths() if path not in listed_paths]
    entry = ""
    while True:   # back at the add's gate returns here, the path last picked typed again
        entry = tui.gum_filter("path to add", candidates, entry)
        if not entry:
            return _cancelled_exit_code()
        print(f"resolving {entry} …", flush=True)
        try:
            paths = status.load_entry_paths(entry)
        except SystemExit as refusal:
            print()
            return _failure_exit_code(f"{entry} cannot be added", f"to_crawl.md: {entry}", str(refusal.code),
                                      "choose another path")
        kind = "folder" if (config.REPO_ROOT / entry).is_dir() else "file"
        print()
        marked = _skills_answer(entry, skills, load_preselected_skills(entry, skills))
        if marked is None:
            return _cancelled_exit_code()
        tui.gum_table(("parameter", "value"), [{"parameter": "path", "value": entry},
                                               {"parameter": "kind", "value": kind},
                                               {"parameter": "files", "value": str(len(paths))},
                                               {"parameter": "skills", "value": f"{len(marked)} of {len(skills)}"},
                                               {"parameter": "writes", "value": "one row at the end of to_crawl.md"}])
        if paths:
            print()
            # each file as a crawl reads it once the row is added: with the skills of every row naming it
            after = {row["path"]: row for row in _queue_rows(_load_entries({**marks, entry: marked}))}
            tui.gum_table(FILE_COLUMNS, _file_rows([after[path] for path in paths[:config.PREVIEW_TABLE_LIMIT_ROWS]]),
                          FILE_COLUMNS_DROP_ORDER)
        if len(paths) > config.PREVIEW_TABLE_LIMIT_ROWS:
            print(f"… {len(paths) - config.PREVIEW_TABLE_LIMIT_ROWS} more, {len(paths)} files in all")
        print()
        decision = tui.gum_choose(f"add {entry} to to_crawl.md?", _option_rows("add", "back", "cancel"), "option")
        if decision == "add":
            break
        if decision != "back":
            return _cancelled_exit_code()
        print()
    write_skill_matrix({**marks, entry: marked}, skills)
    status.main()
    print()
    tui.gum_style([f"{tui.state_label('DONE')}  added {entry} to to_crawl.md · {kind} · {len(paths)} files · "
                   f"{len(marked)} of {len(skills)} skills"], "DONE")
    return 0


def _write_marked_skills(marks: dict[str, list[str]], skills: list[str]) -> int:
    if not marks:
        return _failure_exit_code("nothing to mark", "to_crawl.md", "the skill matrix lists no path", "add a path first")
    while True:   # back at the mark's gate returns here
        entry = tui.gum_choose("path to mark", [{"#": number, "path": entry, "skills": len(marked)}
                                                for number, (entry, marked) in enumerate(marks.items(), 1)], "path")
        if not entry:
            return _cancelled_exit_code()
        marked = _skills_answer(entry, skills, marks[entry])
        if marked is None:
            return _cancelled_exit_code()
        changes = [{"skill": Path(skill).stem, "now": status.SKILL_MARK if skill in marks[entry] else "",
                    "after": status.SKILL_MARK if skill in marked else ""}
                   for skill in skills if (skill in marks[entry]) != (skill in marked)]
        if changes:
            tui.gum_table(("skill", "now", "after"), changes)
        else:
            print("no mark changes")
        print()
        decision = tui.gum_choose(f"mark {entry} in to_crawl.md?",
                                  _option_rows(*(("mark",) if changes else ()), "back", "cancel"), "option")
        if decision == "mark":
            break
        if decision != "back":
            return _cancelled_exit_code()
        print()
    write_skill_matrix({**marks, entry: marked}, skills)
    status.main()
    print()
    tui.gum_style([f"{tui.state_label('DONE')}  marked {entry} in to_crawl.md · {len(marked)} of {len(skills)} skills · "
                   f"{len(changes)} changed"], "DONE")
    return 0


def _write_removed_path(marks: dict[str, list[str]], skills: list[str]) -> int:
    if not marks:
        return _failure_exit_code("nothing to remove", "to_crawl.md", "the skill matrix lists no path",
                                  "add a path first")
    while True:   # back at the remove's gate returns here
        entry = tui.gum_choose("path to remove", [{"#": number, "path": entry}
                                                  for number, entry in enumerate(marks, 1)], "path")
        if not entry:
            return _cancelled_exit_code()
        tui.gum_style([f"{tui.state_label('WARN')}  remove {entry}", "removes its row from to_crawl.md    yes",
                       "deletes a file of the repository   no", "deletes its reports                no"], "WARN")
        print()
        decision = tui.gum_choose(f"remove {entry} from to_crawl.md?", _option_rows("remove", "back", "cancel"),
                                  "option")
        if decision == "remove":
            break
        if decision != "back":
            return _cancelled_exit_code()
        print()
    write_skill_matrix({listed: marked for listed, marked in marks.items() if listed != entry}, skills)
    status.main()
    print()
    tui.gum_style([f"{tui.state_label('DONE')}  removed {entry} from to_crawl.md · its reports stay"], "DONE")
    return 0


def main() -> int:
    argparse.ArgumentParser(prog="python3 -B -m module_skills.sub_module_scalability_crawler.crawl",
                            description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                            allow_abbrev=False).parse_args()
    if not sys.stdin.isatty():
        return _failure_exit_code("the TUI needs a terminal", "standard input", "it is not a terminal, so no choice "
                                  "can be asked", "run make skills-crawl in a terminal; make skills-status writes the "
                                  "snapshot without it")
    if not shutil.which("gum"):
        return _failure_exit_code("gum is not on PATH", "PATH", None,
                                  "install gum 2: https://github.com/charmbracelet/gum#installation")
    vendors = load_active_vendors()
    if not vendors:
        return _failure_exit_code("no vendor is active", "vendors_for_crawling.toml", None,
                                  "set active = true in one vendor's table")
    try:
        skills = status.load_skill_paths()
    except SystemExit as refusal:
        return _failure_exit_code("the skills cannot be read", "SKILL_PATHS in config.py", str(refusal.code),
                                  "rename one of the two skills, then make skills-crawl again")
    try:
        marks = status.load_skill_matrix()
    except SystemExit as refusal:
        return _failure_exit_code("the skill matrix cannot be read", "to_crawl.md", str(refusal.code),
                                  "mend it in to_crawl.md, then make skills-crawl again")
    try:
        entries = _load_entries(marks)
        queue = _queue_rows(entries)
        crawled = sum(1 for row in queue if row["crawl_count"])
        tui.gum_style(["Scalability crawler", f"{len(marks)} paths listed · {len(skills)} skills · {len(queue)} files · "
                                              f"{crawled} crawled · {len(queue) - crawled} never crawled"], "CURRENT")
        if entries:
            print()
            tui.gum_table(("#", "path", "kind", "files", "crawled"), [
                {"#": number, "path": entry["entry"], "kind": entry["kind"],
                 "files": len(entry["rows"]) if not entry["refusal"] else "—",
                 "crawled": f"{sum(1 for row in entry['rows'] if row['crawl_count'])} / {len(entry['rows'])}"
                 if not entry["refusal"] else "—"} for number, entry in enumerate(entries, 1)],
                ("kind", "crawled", "files"))
            for entry in entries:
                if entry["refusal"]:
                    print(f"{tui.state_label('WARN')}  {entry['refusal']} — remove a path takes it out")
            print()
            tui.gum_table(("skill", *(str(number) for number in range(1, len(entries) + 1))),
                          _skill_rows(skills, entries), tuple(str(number) for number in range(len(entries), 0, -1)))
        print()
        action = tui.gum_choose("action", _option_rows("crawl", "add a path", "mark skills", "remove a path", "quit"),
                                "option")
        if action in (None, "", "quit"):
            return _cancelled_exit_code()
        if action == "add a path":
            return _write_added_path(marks, skills)
        if action == "mark skills":
            return _write_marked_skills(marks, skills)
        if action == "remove a path":
            return _write_removed_path(marks, skills)
        return _write_crawl_reports(vendors, entries, skills)
    except KeyboardInterrupt:
        print(f"\n{tui.state_label('CANCELLED')}  interrupted by Ctrl-C", file=sys.stderr)
        return tui.INTERRUPTED_EXIT_CODE
    except SystemExit as refusal:   # the skill matrix's rule refusing an entry as the snapshot is written after a write
        if not isinstance(refusal.code, str):
            raise
        return _failure_exit_code("the snapshot was not written", "to_crawl.md", refusal.code,
                                  "take that path out through remove a path, then make skills-status")


if __name__ == "__main__":
    raise SystemExit(main())
