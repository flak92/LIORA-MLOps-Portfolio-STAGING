# Skill: the scalability crawler — the listed files read against the skills marked for them

`module_skills/sub_module_scalability_crawler/` reads each file a hand lists
against the skills a hand marks for it, writes a report a hand reads, and its
snapshot. A hand runs it in a terminal, one action per run; it gates nothing,
edits no file but its skill matrix and commits nothing (`AGENTS.md` § Values).
*The repository shows the destination, not the road*: the rules draw the
destination, and a report says where one file stands from it.

## The skill matrix, the mission, the report

- **The skill matrix** is `to_crawl.md`, kept by a hand, in the file or through
  the TUI: a Markdown table, a row per entry and a column per skill. An entry's
  `path` is a path from the root, a folder every file under it in byte order but
  `__pycache__` and the reports, and the rows' order is the queue. The skill
  columns are every file `SKILL_PATHS` finds — every module's `skills/`, the
  canon's `skill_*.md` and its sub-modules' — each headed by its stem, in the byte
  order of their paths. A cell is `X`, a mark — that skill acts on the crawl of
  every file the entry names — or empty; a file two entries name takes the marks
  of both. The skill matrix is drafted, not derived: its entries and its marks
  are a hand's decisions, and its header copies no project knowledge —
  `SKILL_PATHS` is the one definition, every read takes the columns from the tree
  and every write rewrites the header from it, every column as wide as its widest
  cell, so the same marks write the same bytes (`AGENTS.md` § Canonical
  vocabulary, *Rule-derived structure over repeated project knowledge*). A skill
  the header lacks is read unmarked.
- **A refusal** is one line, read when the skill matrix is read: a line that is
  not a row, a first column not headed `path`, a column naming no skill or written
  twice, two skills of one stem, a row of another width, a header without its
  separator, a row naming no path or a path listed twice, a cell but `X` or empty
  — and, entry by entry, a path holding `|`, one that names nothing or a file that
  is not UTF-8. `make skills-status` ends on it, exit 1.
  The TUI shows a table it cannot read in a failure block before its first
  screen, and an entry refused on its own as a `WARN` line under the listed paths,
  going on, so such an entry is removed through the TUI; a crawl ends before its
  forms while one is refused, and an add, a mark or a remove as its snapshot is
  written.
- **The mission** is `crawlers_mission.md`, kept by hand: what the agent reports
  of one file, and how.
- **The vendors** are `vendors_for_crawling.toml`, kept by hand (§ Vendors).
- **The message** for a file is the mission, then `# Rules` with every document
  `SENT_DOCUMENT_PATHS` finds — `AGENTS.md`, `module_skills/glossary.md` and the
  orientation of the module the file's first path segment names — a root file has
  none, and a file of the canon's own repository takes `module_skills/README_module_skills.md` — then `# Skills marked for this
  file` with each skill its row marks, in the columns' order, each under its path,
  then `# Skills not marked for this file`, every other skill by its path alone,
  then `# File under review: <path>` and the file, each line after its number. It
  carries every document the file is read against, so the agent needs no tool and
  answers in one turn of text; an unmarked skill is named, never sent.
- **The agent** is the command line `build_command()` built: one fresh session per
  chosen file, one after another, in its user's own login, its stderr on the
  screen as it runs. The first failure — an exit other than zero, an empty answer
  or `AGENT_TIMEOUT_MINUTES` passed — ends the crawl with a failure block naming
  the file and the reason — `the agent exited with <code>`, `the agent's answer
  was empty` or the minutes it ran past — and exit 1; the reports already written
  stay.
- **The report** of a file is `reports_after_crawled_files/<path>.md`. A crawl
  appends a blank line, the heading `## crawled <YYYY-MM-DD HH:MM> UTC · <vendor> · <labels> · <short commit> · skills: <stems>`,
  its labels the options chosen in the vendor's forms and its stems the skills
  sent with the file, `none` when its row marks none, the answer as it came and a
  blank line, and never overwrites or summarises. `REPO_ROOT`, the paths an add
  offers and the heading's commit are the sub-module's three calls of git.

## Vendors

`vendors_for_crawling.toml` holds one table per vendor, in the vendor list's
order; its header says what a table holds. After the vendor the TUI asks each
form its table has — `model`, `effort`, `permissions`, in that order — and
`build_command()` appends to `command` the `args` of the option chosen in each.
The first option is preselected and a form of one option is answered without
asking, so a crawl with the defaults is an Enter per form and one on the plan,
and a form the table lacks is not asked. The code knows no vendor and no
flag: a vendor, a model or a flag is a line of the file. The first `permissions`
option lets the agent use no tool — a crawl is one message and one answer — and
a vendor is `active` once one run of its command line on one file showed it
answering from the message alone.

## The TUI

`make skills-crawl` opens the crawler's text-based user interface (TUI): the
screens `crawl.py` composes and `tui.py` draws in gum, to the standards of
`skill_tui_designer.md`, which crosses the sub-modules that draw a terminal and
therefore sits in the canon. This section says what each screen holds, what each
answer writes, and the screens' own words, tables and lists; how a screen is
drawn is that skill's.

A run opens on the header block — *Scalability crawler* over the counts of paths
listed, skills, files, crawled and never crawled — the listed paths table, one
row per entry with its kind, its files and how many of them are crawled, and the
skill matrix turned for the terminal: a row per skill, `X` under the `#` of each
path whose row marks it; then the menu, `gum choose` headed *action*: crawl, add
a path, mark skills, remove a path, quit.

- **crawl** — refused while an entry is refused or the skill matrix names no
  file. The vendor, one row per active vendor off `load_active_vendors()` in the
  file's order, with whether its command line is on the `PATH`: without it the
  crawl ends, `<cli> is not on PATH`, exit 1. Then the vendor's forms (§ Vendors)
  and *files to crawl*, every listed file preselected in the skill matrix's order
  — the queue a hand keeps — each with its `last_crawled_utc` or never, its
  `crawl_count` off `status.load_file_row()` and how many skills it is read
  against; the steps table stands above each. The plan closes the forms — the
  choices, the command line `build_command()` built, the report heading with the
  skills sent, and the files — with *crawl*, *back* and *cancel*: no agent is
  called before *crawl*, and *back* asks the forms again from the vendor. Each
  chosen file in turn prints `CRAWLING`, goes with the mission, its rules, its
  marked skills and the unmarked skills' paths to the agent, has its answer
  appended to its report and prints `DONE` with its seconds; the results table and
  the outcome come last.
- **add a path** — `gum filter` headed *path to add*, over the files git tracks
  or does not ignore and the folders above them, the reports and the listed
  entries left out; a path git ignores is added in the file.
  `status.load_entry_paths()` resolves it — a path it refuses ends the program,
  exit 1, nothing written — then the skills form, `gum choose` headed *skills for
  <path>*, every skill in the columns' order, the matches of
  `SKILL_PRESELECTED_PATHS` chosen at the start: the canon's, those of the path's
  module and those in its folder or a folder above it. The preview shows the path,
  its kind, its files and how many skills it marks, and *add* alone appends its
  row through `write_skill_matrix()`.
- **mark skills** — refused while the skill matrix lists no path. `gum choose`
  headed *path to mark*, then the skills form with the entry's marks chosen at the
  start, then the changes table — each skill whose mark changes, now and after —
  with *mark*, *back* and *cancel*, or `no mark changes` with *back* and *cancel*
  alone: *mark* alone rewrites the entry's row through `write_skill_matrix()`, and
  *back* returns to *path to mark*.
- **remove a path** — `gum choose` headed *path to remove*, among the skill
  matrix's entries, then a block that says its row leaves `to_crawl.md` and no
  file and no report is deleted; *remove* alone takes the row out through
  `write_skill_matrix()`.

`_gum()` in `tui.py` reads a hand's answer off gum's stdout, gum drawing on
stderr. Esc, *cancel*, *quit* or no file chosen in *files to crawl* ends the
program with exit 0 and nothing written,
not even the snapshot; Ctrl-C with exit 130, a crawl's reports already written
staying; a failure with a block on stderr and exit 1; an argument other than
`-h`, `--help` with exit 2. One action per run: after it the program ends.

Without a terminal on standard input, without gum on the `PATH` (`AGENTS.md`
§ Values, *Minimum requirements*) or with no active vendor in
`vendors_for_crawling.toml`, the program ends in a failure block that says what
to do next, exit 1.

After a run `git status` shows the reports that grew, `to_crawl.md` if a path was
added, marked or removed, and the snapshot; a hand reads them and commits them.

### The crawler's own words, tables and lists

Two states beside the closed list of `skill_tui_designer.md` § One concept, one
representation: `CRAWLING` — the file the agent reads now, → cyan,
`[CRAWLING]` — and `NOT CRAWLED` — a chosen file the crawl did not reach, ○, no
colour, `[NOT CRAWLED]`. `never` is a value — the `last crawl (UTC)` of a file no
report dates — not a state; so is `X`, a mark of the skill matrix. Forbidden
here: `target` for a listed path, `DIRECTORY` for a folder, `workflow` for the
steps; `assign`, `tag` or `✓` for a mark.

The tables, with the columns a narrow terminal leaves out first:

| table | columns | left out first on a narrow terminal |
|---|---|---|
| the listed paths | `#`, `path`, `kind`, `files`, `crawled` | `kind`, `crawled`, `files` |
| the skill matrix, turned | `skill`, then the `#` of each listed path | the last paths' `#` |
| the steps | `step`, `state`, `choice` | — |
| the plan, a preview | `parameter`, `value` | — |
| the files — the queue, the files a crawl will read, the files an add resolves to | `#`, `file`, `last crawl (UTC)`, `crawls`, `skills` | `skills`, `crawls`, `last crawl (UTC)` |
| the changes | `skill`, `now`, `after` | — |
| the results | `#`, `file`, `result`, `time`, `report` | `report`, `time` |
| the vendor list | `vendor`, `on PATH`, `command` | `command` |
| a form's options | `label`, `args` | `args` |
| the skills form | `skill`, `path` | `path` |
| the paths to mark | `#`, `path`, `skills` | — |

- **The skill matrix is turned on the screen:** `to_crawl.md` holds a row per path
  and a column per skill; the terminal shows a row per skill by its stem and a
  column per listed path by its `#` — the `#` of the listed paths table right
  above — because a stem runs to 35 columns and a `#` to a few: no legend, and a
  stem never cut.
- **`#` counts from 1 in the skill matrix's order** — `to_crawl.md`'s rows, or the
  queue's. A cell is the snapshot's value as it stands (`crawl_count`,
  `last_crawled_utc` or `never`, `report`), a mark `X` or empty.
- **The one bounded table is an add's preview** — `PREVIEW_TABLE_LIMIT_ROWS` files,
  then `… <k> more, <n> files in all`.
- **The options in their file's order:** the actions; the vendors in
  `vendors_for_crawling.toml`'s; a form's options in theirs; the files in the
  queue's; the listed paths in `to_crawl.md`'s rows; the skills in its columns'.
  Every file starts chosen (`--selected "*"`), and a skill when its row marks it —
  in an add, when `SKILL_PRESELECTED_PATHS` finds it.
- **The headers of its lists,** each a register label: `action`, `vendor`, `model`,
  `effort`, `permissions`, `files to crawl`, `path to add`, `skills for <path>`,
  `path to mark`, `path to remove`.
- **A form's option shows its `args`** as a shell writes them (`shlex.join`),
  because they are what it does; a vendor shows whether its command line is on the
  `PATH`, and the command line — each left out, and said, only on a terminal too
  narrow for it, the plan showing the whole command line.
- **The steps table's rows** are `action`, `vendor`, each form the vendor's table
  has in `model`, `effort`, `permissions` order, `files to crawl`, `plan`. Before
  the vendor is chosen its forms are one row, `the vendor's forms`: a step is read
  off the vendor's table, never assumed. An add and a mark draw no steps table.
- **The plan** carries `timeout per file` and `reports` beside the choices, the
  `command` line and the `report heading` each report entry will carry, verbatim,
  and the files table of the chosen files; then the gate
  `crawl <n> files with <vendor>?` — `crawl`, `back`, `cancel`.
- **An add shows what it writes before it writes it:** the path picked in
  `gum filter` — typed in part, the placeholder a real example — then
  `resolving <path> …`, the skills form, the preview table (`path`, `kind`,
  `files`, `skills`, `writes`) and the files it resolves to, then `add`, `back`,
  `cancel`; `back` returns to the filter with the path typed again.
- **A remove says what it does and what it does not:** the `WARN` block — its row
  leaves `to_crawl.md`, yes; a file of the repository is deleted, no; its reports
  are deleted, no — then `remove`, `back`, `cancel`.
- **Progress:** `[<i>/<n>] → CRAWLING <path> · <vendor>` before a file's message is
  built, the agent's stderr on the screen as it runs, then
  `[<i>/<n>] ✓ DONE <path> <s> s` or `✕ FAILED`; after the crawl the results table
  and the `DONE` block, `crawled <k> of <n> files with <vendor> · <labels>`.
- **Its exits** are `skill_tui_designer.md` § Failures and exits, with two facts of
  its own: no file chosen in *files to crawl* is a cancel, exit 0, and Ctrl-C
  leaves a crawl's reports already written in place and writes its snapshot.
- **A screen reads and never recomputes:** the skill matrix's rule through
  `status.load_skill_matrix()` and `status.load_entry_paths()`, its columns through
  `status.load_skill_paths()` — a refusal shown in its own words —, a file's row
  through `status.load_file_row()`, the vendors through `load_active_vendors()`,
  the command line through `build_command()`, the timeout from
  `config.AGENT_TIMEOUT_MINUTES`.
- **Without the Makefile** the help is read as
  `STORE_STATUS_DIR=../store_status python3 -B -m module_skills.sub_module_scalability_crawler.crawl -h`.

## The actuality

Every action of `make skills-crawl` that changes something ends with
`make skills-status`'s work, a failed or an interrupted crawl too.
`store/status/skills_status.json` holds a row per listed file, sorted by `path`,
with its `report`, its `crawl_count` and its `last_crawled_utc`, read off the
dates of the report's headings — a heading's skills enter no row. No clock enters
it, so unchanged reports write the same bytes. The Scalability tab draws it as one
table and adds each file's age against the browser's clock.

## Design rationale

Why each object sits where it does — the answers of
`skill_self_explaining_naming.md` § The naming review; the module argues its
objects in `README_module_skills.md` § Design rationale, and its sub-module argues
its own files here (`AGENTS.md` § Pre-AWS architectural direction).

| object | why here | why beside these | why this boundary | answers to |
|---|---|---|---|---|
| `__init__.py` | The package that makes `crawl` and `status` commands of `python3 -m`. | It imports nothing, so a command of this sub-module runs without the module's own stages. | The commands run from the checkout's root. | no row — a reading of the tree that travels with the canon |
| `README_sub_module_scalability_crawler.md` | The front door: the commands, the three files kept by hand and the loop. | Beside the files it names; the rules stay in this skill and the standards of the screens in `module_skills/skill_tui_designer.md`, which it cites. | It restates no rule and decides nothing. | no row — a reading of the tree that travels with the canon |
| `config.py` | The one surface of configuration (its docstring). | `crawl.py`, `status.py` and `tui.py` import it; `STORE_STATUS_DIR` comes from the environment, as in every `config.py`, and `OUTPUT_PLAIN` from `NO_COLOR`, `TERM` and whether standard output is a terminal; the sub-module's own files are read from `SUB_MODULE_DIR`, a listed path, a document and a skill from `REPO_ROOT`. | A document sent with every file is one line of `SENT_DOCUMENT_PATHS`, a family of skills one pattern of `SKILL_PATHS`, and which skill acts on a file's crawl a mark of `to_crawl.md`, never a line here; a vendor is a table of `vendors_for_crawling.toml`; plain output is the environment's, never a flag. | no row — a reading of the tree that travels with the canon |
| `crawl.py` | The TUI's screens and the crawl (its docstring). | It imports `config.py`, `status.py` and `tui.py`, reads the active vendors through `load_active_vendors()`, builds the agent's command line through `build_command()`, runs git twice — the paths an add offers, the commit a report entry names — and that command line over `subprocess`, and draws every screen through `tui.py`. | It writes the reports, the skill matrix through `write_skill_matrix()` and, through `status.py`, the snapshot — nothing else; `-h`, `--help` is its one argument. | no row — a reading of the tree that travels with the canon |
| `status.py` | The snapshot and the skill matrix's rule (its docstring). | It imports `config.py`, reads the skill matrix and the reports, and writes `skills_status.json`; its `load_skill_matrix()`, `load_skill_paths()` and `load_entry_paths()` are the skill matrix's one rule and `load_file_row()` a file's one row, which the TUI also reads. | A function of the skill matrix's paths and the reports; a mark enters no row. | no row — a reading of the tree that travels with the canon |
| `tui.py` | How a screen is drawn and an answer taken (its docstring): the state words, plain output, the columns that fit, and every gum command line over `subprocess`. | `crawl.py` alone imports it, and it imports `config.py` for plain output alone; it knows no vendor, no skill matrix and no report. | It writes to the terminal and no file; a hand's answer returns to `crawl.py` as text. | no row — a reading of the tree that travels with the canon |
| `to_crawl.md` + `crawlers_mission.md` + `vendors_for_crawling.toml` | The three inputs a hand keeps. | Beside the code that reads them. | `to_crawl.md` — its entries and its marks — edited by a hand in the file or in the TUI, its header rewritten from the tree by every write; `crawlers_mission.md` and `vendors_for_crawling.toml` by hand alone; never by a crawl. | no row — a reading of the tree that travels with the canon |
| `reports_after_crawled_files/` | The reports, one per listed file, its path the file's. | Beside the crawler and tracked: documents a hand reads, not state of the chain (`AGENTS.md` § Pre-AWS architectural direction, *Storage is separate from compute*). | Appended by a crawl, committed by a hand. | no row — a reading of the tree that travels with the canon |
| `store/status/skills_status.json` | The snapshot `status.py` writes, tracked like the other three. | In the status store; the route `/store_status/<name>` serves it. | `STORE_STATUS_DIR / skills_status.json` in `config.py`. | STORAGE — status, run and trial objects |
