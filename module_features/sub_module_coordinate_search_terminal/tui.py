"""A sub-module's text-based user interface (TUI) over the gum command line: the state words, plain output, tables
and lists fitted to the terminal, blocks, and the answer a hand gives in a prompt. Its standards are
module_skills/skill_tui_designer.md; what a screen holds is the action module's. One file, twice by extraction
(module_skills/glossary.md § Twice by extraction): it knows none of its sub-module's own objects, and every
sentence of its own is in that sub-module's config.py."""

from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
import sys

from . import config

# a state's symbol and its colour, a number of the terminal's own palette, in normal output; plain output shows the word
# alone, in brackets, and a state with no colour is drawn in the terminal's default
STATE_SYMBOLS = {"DONE": "✓", "CURRENT": "→", "CRAWLING": "→", "PENDING": "○", "NOT CRAWLED": "○", "CANCELLED": "⚠",
                 "WARN": "⚠", "FAILED": "✕", "ERROR": "✕"}
STATE_COLOURS = {"DONE": "2", "CURRENT": "6", "CRAWLING": "6", "CANCELLED": "3", "WARN": "3", "FAILED": "1", "ERROR": "1"}
INTERRUPTED_EXIT_CODE = 130   # a process ended by Ctrl-C, 128 + SIGINT: gum's own, and this program's
LIST_MARGIN_COLUMNS = 6       # what a list draws before a label: the cursor `> ` and the selection prefix `[x] `


def state_label(state: str) -> str:
    """A state as the output shows it: `[DONE]` when plain, `✓ DONE` otherwise."""
    return f"[{state}]" if config.OUTPUT_PLAIN else f"{STATE_SYMBOLS[state]} {state}"


def error_lines(what: str, where: str, why: str | None, next_action: str) -> list[str]:
    """A failure as its block's lines: what failed, where, why when it is known, and what a hand does next."""
    return [f"{state_label('ERROR')}  {what}", f"where  {where}", *([f"why    {why}"] if why else []),
            f"next   {next_action}"]


def _to_csv(columns: list[str], rows: list[dict]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows([columns, *([row[column] for column in columns] for row in rows)])
    return buffer.getvalue()


def _column_widths(columns: list[str], rows: list[dict]) -> list[int]:
    return [max(len(column), *(len(str(row[column])) for row in rows)) for column in columns]


def _fitting_columns(columns: tuple[str, ...], rows: list[dict], drop_order: tuple[str, ...], margin_columns: int,
                     gap_columns: int) -> list[str]:
    """The columns that fit the terminal: while wider, drop_order's leave in turn, and one line names them; off a
    terminal every column stays."""
    kept, width = list(columns), shutil.get_terminal_size((sys.maxsize, 0)).columns
    for column in drop_order:
        if margin_columns + sum(cell + gap_columns for cell in _column_widths(kept, rows)) <= width:
            break
        kept.remove(column)
    if len(kept) < len(columns):
        print(f"left out at {width} columns: {', '.join(column for column in columns if column not in kept)}")
    return kept


def gum_table(columns: tuple[str, ...], rows: list[dict], drop_order: tuple[str, ...] = ()) -> None:
    """The rows under their columns on stdout, by `gum table --print`; the identifier is never left out or cut."""
    kept = _fitting_columns(columns, rows, drop_order, margin_columns=1, gap_columns=3)
    sys.stdout.flush()
    # gum 2 bolds a printed table's first row unless TERM is dumb; a table carries no colour at all
    subprocess.run(("gum", "table", "--print", "--border", "hidden" if config.OUTPUT_PLAIN else "rounded"),
                   input=_to_csv(kept, rows), text=True, env={**os.environ, "TERM": "dumb"})


def gum_style(lines: list[str], state: str, stream=sys.stdout) -> None:
    """A block: inside a rounded border in the state's colour — or, in plain output, without gum or wider than the
    terminal, the lines alone."""
    sys.stdout.flush()
    stream.flush()
    if (config.OUTPUT_PLAIN or not shutil.which("gum")
            or max(map(len, lines)) + 4 > shutil.get_terminal_size((sys.maxsize, 0)).columns):
        print(*lines, sep="\n", file=stream, flush=True)
        return
    subprocess.run(("gum", "style", "--border", "rounded", "--border-foreground", STATE_COLOURS[state],
                    "--padding", "0 1", "--", *lines), stdout=stream)


def _gum(*arguments: str) -> str | None:
    """A hand's answer in one gum prompt, off its stdout (gum draws on stderr): `""` when nothing is chosen, None for
    Esc, Ctrl-C raised as KeyboardInterrupt; plain output hands gum NO_COLOR."""
    sys.stdout.flush()
    answer = subprocess.run(("gum", *arguments), stdout=subprocess.PIPE, text=True,
                            env={**os.environ, "NO_COLOR": "1"} if config.OUTPUT_PLAIN else None)
    if answer.returncode == INTERRUPTED_EXIT_CODE:
        raise KeyboardInterrupt
    return answer.stdout.strip("\n") if answer.returncode == 0 else None


def gum_choose(header: str, rows: list[dict], value_column: str, drop_order: tuple[str, ...] = (),
               selected: list[str] | None = None) -> str | None:
    """The value a hand chooses under header — with selected the values chosen, one per line, those in selected chosen
    at the start; a list is a table: each label is the row's columns aligned, the second header line their words, and
    gum returns the row's value_column, never a label parsed back; one row is answered without asking."""
    columns = _fitting_columns(tuple(rows[0]), rows, drop_order, margin_columns=LIST_MARGIN_COLUMNS, gap_columns=2)
    widths = _column_widths(columns, rows)
    # a tab ends a label for gum (--label-delimiter), so a cell's tab is drawn as a space; the value keeps its own
    labels = ["  ".join(str(row[column]).replace("\t", " ").ljust(width)
                        for column, width in zip(columns, widths)).rstrip() for row in rows]
    if len(columns) > 1:
        indent = " " * (LIST_MARGIN_COLUMNS if selected is not None else 2)
        header = f"{header}\n{indent}{'  '.join(column.ljust(width) for column, width in zip(columns, widths)).rstrip()}"
    colours = () if config.OUTPUT_PLAIN else tuple(
        argument for flag in ("--cursor.foreground", "--header.foreground", "--selected.foreground")
        for argument in (flag, STATE_COLOURS["CURRENT"]))
    height = max(3, min(len(rows), shutil.get_terminal_size().lines - 6))
    # gum 2 matches --selected against a label, never the value after --label-delimiter, and splits it at commas
    chosen = [label for label, row in zip(labels, rows) if selected is not None and row[value_column] in selected]
    preselected = "*" if len(chosen) == len(rows) else ",".join(chosen)
    return _gum("choose", "--header", header, "--label-delimiter", "\t", "--select-if-one", "--height", str(height),
                "--cursor", "> ", "--cursor-prefix", "[ ] ", "--selected-prefix", "[x] ", "--unselected-prefix", "[ ] ",
                *colours, *(("--no-limit",) if selected is not None else ()),
                *(("--selected", preselected) if preselected else ()),
                "--", *(f"{label}\t{row[value_column]}" for label, row in zip(labels, rows)))


def gum_filter(header: str, candidates: list[str], value: str = "") -> str | None:
    """The candidate a hand picks under header by typing part of it, drawn inline under the screen above it."""
    colours = () if config.OUTPUT_PLAIN else tuple(
        argument for flag in ("--indicator.foreground", "--match.foreground", "--header.foreground")
        for argument in (flag, STATE_COLOURS["CURRENT"]))
    return _gum("filter", "--header", header, "--placeholder", config.FILTER_PLACEHOLDER,
                f"--value={value}", "--height", "12", "--prompt", "> ", "--indicator", ">", *colours, "--", *candidates)
