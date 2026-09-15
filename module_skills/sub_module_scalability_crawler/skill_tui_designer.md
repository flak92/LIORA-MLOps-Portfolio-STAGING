# Skill: the crawler's text-based user interface (TUI) — tables, lists and forms in gum

`make skills-crawl` is the scalability crawler's text-based user interface (TUI): every screen is drawn in gum, the one
terminal instrument the host admits (`AGENTS.md` § Values, *Minimum requirements*). Python decides what a screen holds —
its rows, its columns, its words — and gum draws it and takes the answer. The rule is neuro-optical consistency
(`AGENTS.md` § Architecture shape): a screen is read by eye before it is understood, so one concept always takes one
form, a change of form means a change of meaning, and the decision and the result stand where the eye lands. What each
screen holds and what each answer writes is `../skill_scalability_crawler.md` § The TUI; how a screen is drawn is this
skill. *The repository shows the destination, not the road*: nothing measures, checks or schedules a screen — a hand
runs it.

## The instruments

One role, one instrument; the one module that speaks them is `tui.py`.

| role | instrument | draws | never |
|---|---|---|---|
| context, an outcome | `gum style`, a rounded border in the state's colour | the header block that opens a run; the remove's warning; the result or the failure that closes it | a banner; a block inside a block; a block around a table |
| rows of one kind, read | `gum table --print` | the listed paths, the skill matrix, the steps, the plan, a preview, the changes, the results | a colour on a cell, a row or a border; the interactive `gum table` |
| a choice | `gum choose` | the action, the vendor, each form, the files, the skills, the path to mark, the path to remove, every gate | `gum confirm`, whose default is shown by colour alone; `gum input` for a value the tree already holds |
| a path of the tree | `gum filter`, inline | the path to add | `--no-strict`, whose Enter returns the text typed, not the path under the cursor |
| a line | Python's `print` | a fact beside a table, progress, `wrote …`, `CANCELLED` | a line rewritten in place; a cleared screen; an escape code written by Python |

## The screen

- **Order, top to bottom:** context → state → decision → result. The eye lands on the last line, so an action ends on
  its result or its failure, and nothing is printed after either.
- **One blank line** between sections — above a table, a list, a block; none inside one.
- **Density:** one header block per run; on a screen one decision, and one table per kind of row. Forbidden: a heading
  above a table (its header row is its heading), the same rows twice on one screen, ASCII art, an emoji, a gradient.

Each screen answers six questions, each in one place:

| question | answered by |
|---|---|
| where am I | the header block; the prompt's header |
| what is configured | the listed paths table; the skill matrix table; the steps table |
| what have I selected | the steps table's choices; the plan; a preview; the changes table |
| what am I selecting now | the step shown `CURRENT`; the prompt's header |
| what happens next | the `PENDING` steps; a gate's question |
| what exactly runs | the plan's `command` and `report heading`, verbatim |

## One concept, one representation

A state is a word from one closed list; a symbol and a colour repeat the word and never replace it.

| word | means | symbol | colour | plain output |
|---|---|---|---|---|
| `DONE` | a step answered, a file crawled, an action carried out | ✓ | green | `[DONE]` |
| `CURRENT` | the step asked now | → | cyan | `[CURRENT]` |
| `CRAWLING` | the file the agent reads now | → | cyan | `[CRAWLING]` |
| `PENDING` | a step still to come | ○ | — | `[PENDING]` |
| `NOT CRAWLED` | a chosen file the crawl did not reach | ○ | — | `[NOT CRAWLED]` |
| `WARN` | a listed path the skill matrix's rule refuses; what a remove does | ⚠ | yellow | `[WARN]` |
| `CANCELLED` | Esc, `cancel`, `quit`, no file chosen in `files to crawl`, or Ctrl-C: nothing more is written | ⚠ | yellow | `[CANCELLED]` |
| `FAILED` | the file the agent gave no answer for | ✕ | red | `[FAILED]` |
| `ERROR` | the failure that ends the run | ✕ | red | `[ERROR]` |

- A colour is drawn only where gum draws one: a block's border, a prompt's cursor and header. A table cell and a printed
  line carry the word and the symbol, uncoloured — gum strips a colour from a cell, and Python writes no escape code.
- `never` is a value — the `last crawl (UTC)` of a file no report dates — not a state; so is `X`, a mark of the skill
  matrix.
- Forbidden: a colour or a symbol without its word; a coloured row (`AGENTS.md` § Rejected vocabulary); `running` (the
  crawl is `CRAWLING`), `ok`, `success`; `target` for a listed path, `DIRECTORY` for a folder, `workflow` for the steps;
  `assign`, `tag` or `✓` for a mark.

## Tables

- **A table** holds rows of one kind with more than one field; one fact is a line (`repository root  <path>`,
  `command  <command line>`).
- **Columns:** `#` where the rows are numbered, the identifier, then the fields, the secondary last. The header words are
  the register's UI labels (`../glossary.md` § Scalability crawler), lower case.

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

- **The skill matrix is turned on the screen:** `to_crawl.md` holds a row per path and a column per skill; the terminal
  shows a row per skill by its stem and a column per listed path by its `#` — the `#` of the listed paths table right
  above — because a stem runs to 35 columns and a `#` to a few: no legend, and a stem never cut.
- **`#` counts from 1 in the skill matrix's order** — `to_crawl.md`'s rows, or the queue's; a screen sorts nothing.
- **A cell is the snapshot's value as it stands** (`crawl_count`, `last_crawled_utc` or `never`, `report`), a mark `X`
  or empty, a count or a state word; `—` where no value applies. Forbidden: an age, a percentage, a date reformatted.
- **Width is measured at invocation,** never written: gum's table neither wraps nor cuts, so Python leaves columns out in
  the order above until the table fits and prints `left out at <n> columns: <names>`. The identifier is never left out
  or cut; wider still, the terminal wraps it. Off a terminal every column stays.
- **A table prints whole:** no pager. The one bound is an add's preview — `PREVIEW_TABLE_LIMIT_ROWS` files, then
  `… <k> more, <n> files in all` — never silent.
- **Invocation:** the rows on gum's stdin as CSV from Python's `csv`; `--border rounded`, `--border hidden` in plain
  output; `TERM=dumb` in gum's environment, so gum bolds no row. Forbidden: `--widths`, a colour flag, a table padded by
  Python.

## Lists

- **A list is a table a hand picks from:** each label is its row's columns aligned, the second line of the header holds
  the column words over them, and the value gum returns is the row's identifier after a tab (`--label-delimiter`) —
  never a label parsed back. The rows are not drawn a second time above the list.
- **Options in their file's order:** the actions; the vendors in `vendors_for_crawling.toml`'s; a form's options in
  theirs; the files in the queue's; the listed paths in `to_crawl.md`'s rows; the skills in its columns'. The cursor
  starts on the first option; every file starts chosen (`--selected "*"`), and a skill when its row marks it — in an
  add, when `SKILL_PRESELECTED_PATHS` finds it. gum matches `--selected` against a label, never a value, so the call
  names the rows chosen by their labels. Nothing is sorted, and nothing is remembered between runs.
- **The header is the decision's register label** — `action`, `vendor`, `model`, `effort`, `permissions`,
  `files to crawl`, `path to add`, `skills for <path>`, `path to mark`, `path to remove` — or a gate's question.
- **A form's option shows its `args`** as a shell writes them (`shlex.join`), because they are what it does; a vendor
  shows whether its command line is on the `PATH`, and the command line — each left out, and said, only on a terminal
  too narrow for it, the plan showing the whole command line. Nothing is invented beside an option — no
  description, no cost, no sign of a default.
- **A list of one row is answered without asking** (`--select-if-one`); the next steps table shows it `DONE`.
- **Selection prefixes and colour are arguments of the call:** the cursor `> `, the selection prefixes `[x] ` and `[ ] `
  in both outputs; cursor,
  header and selection cyan in normal output. Forbidden: gum's own pink and purple, a gum configuration in the tree.
- **`back` and `cancel` belong to gates alone;** a list of data carries neither — Esc is its cancel — and the menu ends
  on `quit`. Forbidden: `exit` (the Lifecycle tab's exit code), `run` (a recorded run, `../glossary.md` § Run record), a
  second menu after the action.

## Forms

A form is one decision; an action is its forms in order, and ends.

- **The steps table stands above the vendor, each form and the files to crawl, wherever a hand is asked:** its rows are
  `action`, `vendor`, each form the vendor's table has in `model`, `effort`, `permissions` order, `files to crawl`,
  `plan` — a step answered `DONE` with its choice, the step asked `CURRENT` with `select now`, the rest `PENDING` with
  `—`. Before the vendor is chosen its forms are one row,
  `the vendor's forms`: a step is read off the vendor's table, never assumed.
- **The plan stands before any agent is called:** the table of the vendor, each form's choice, the files to crawl,
  `timeout per file` and `reports`; the `command` line and the `report heading` each report entry will carry, verbatim;
  the files table of the chosen files; then the gate `crawl <n> files with <vendor>?` — `crawl`, `back`, `cancel`.
  `back` asks the crawl's forms again from the vendor, every default preselected.
- **An add shows what it writes before it writes it:** the path picked in `gum filter` — typed in part, the placeholder
  a real example — then `resolving <path> …`, the skills form `skills for <path>`, the preview table (`path`, `kind`,
  `files`, `skills`, `writes`) and the files it resolves to, then `add`, `back`, `cancel`; `back` returns to the filter
  with the path typed again.
- **A mark shows what changes before it writes it:** `path to mark`, the skills form `skills for <path>` with the row's
  marks chosen at the start, then the changes table — only the skills whose mark changes, in the columns' order — or
  the line `no mark changes`, then `mark <path> in to_crawl.md?` — `mark`, `back`, `cancel`, or `back` and `cancel`
  alone when nothing changes; `back` returns to `path to mark`. An add and a mark draw no steps table: their preview
  and their changes table stand where the choices are read.
- **A remove says what it does and what it does not:** the `WARN` block — its row leaves `to_crawl.md`, yes; a file of
  the repository is deleted, no; its reports are deleted, no — then `remove`, `back`, `cancel`.
- **The affirmative option comes first, so it is preselected:** a gate refuses nothing a hand confirms, and a crawl with
  the defaults stays an Enter per form and one on the plan (`AGENTS.md` § Values, *UCAS*). A gate is not a guard.

## Feedback and progress

- **Nothing waits unannounced.** A screen before the crawl is a few gum calls; before a slow step a line is flushed
  first — `resolving <path> …`, and `[<i>/<n>] → CRAWLING <path> · <vendor>` before the file's message is built.
- **The agent's stderr stays on the screen** as it runs: no spinner, no bar, no percentage, no estimate — a session's
  length is unknown until it ends — and the files go one after another, as they are crawled.
- **After each file** one line: `[<i>/<n>] ✓ DONE <path> <s> s`, or `✕ FAILED`; the seconds are measured around the
  session and never stored.
- **After an action** `wrote <snapshot>`, then the result last: after a crawl the results table and the `DONE` block —
  `crawled <k> of <n> files with <vendor> · <labels>` — or the failure; after an add, a mark or a remove, its `DONE`
  block.

## Failures and exits

- **A failure is a block on stderr, the run's last:** `✕ ERROR <what failed>`, `where <path or file>`, `why <reason>`
  when it is known, `next <what a hand does>` — the reason in the skill matrix's, the crawl's or the agent's own words.
  In plain output, without gum or wider than the terminal, the same lines without a border.
- **An expected failure has no traceback;** an unexpected one keeps Python's, the one fact a defect needs.
- **The first failure ends a crawl,** so a screen holds one; the paths the skill matrix's rule refuses are grouped at the start,
  one `WARN` line each under the listed paths table, and stay removable.

| exit | when |
|---|---|
| 0 | the action carried out; Esc, `cancel`, `quit` or no file chosen in `files to crawl` — nothing written |
| 1 | a failure, its block last on stderr |
| 2 | an argument other than `-h`, `--help` |
| 130 | Ctrl-C, gum's code and this program's: one `CANCELLED` line; a crawl's reports already written stay and its snapshot is written |

## Colour and plain output

- **A colour is a number of the terminal's own palette,** so a hand's theme decides the shade: 6 cyan the context and
  the choice asked now, 2 green done, 3 yellow attention, 1 red failure. Nothing else is coloured by the crawler, and
  nothing is dimmed but gum's own key line and the filter's prompt and placeholder, in gum's grey.
- **Plain output switches on by itself** when `NO_COLOR` is set and not empty, `TERM` is `dumb`, or standard output is
  not a terminal (`OUTPUT_PLAIN` in `config.py`): no colour — gum is handed `NO_COLOR` —, no symbol — the word in
  brackets —, no border — a table `hidden`, a block printed as its lines.
- **Never changes between the two:** a word, the order, a count, a column, an exit code.
- Forbidden: a flag for either output, a theme, bold or underline set by the crawler.

## Help

`-h`, `--help` prints `crawl.py`'s docstring and exits 0; no other argument exists. The docstring holds the actions, the
keys — Enter, x, Esc, Ctrl-C —, plain output and its three conditions, the exit codes and three examples. Without the
Makefile it is read as
`STORE_STATUS_DIR=store/status python3 -B -m module_skills.sub_module_scalability_crawler.crawl -h`.

## Declined here

| asked of a terminal interface | declined, because | rests on |
|---|---|---|
| Rich, Textual, curses | the host is the standard library and gum 2 | `AGENTS.md` § Values, *Minimum requirements* |
| `--json` | the snapshot is the machine-readable state | `AGENTS.md` D17; `../skill_scalability_crawler.md` § The actuality |
| `--no-input` | a hand alone runs the crawler, one action per run | `AGENTS.md` § Values, D18 |
| `--simple`, `--a11y`, `--no-color`, `--no-animation` | plain output follows the environment, and nothing animates | § Colour and plain output |
| a spinner, a progress bar, a percentage | a spinner hides the agent's stderr, and a session's length is unknown | § Feedback and progress |
| a main loop, an `exit` option, a second menu | one action per run | `AGENTS.md` § Values |
| the branch or the repository's name in the header | no decision needs it; the commit stands in every report heading | `../skill_scalability_crawler.md` § The skill matrix, the mission, the report |
| a pager | a second screen to leave before the decision; the tables are short | § Tables |
| a coloured cell or row | gum strips it, and the word says it | § One concept, one representation |
| a table of grouped failures | the first failure ends a crawl | § Failures and exits |
| `--lang`, a translation | one language, British English | `AGENTS.md` § Canonical vocabulary |

## Where the screens live

- **`tui.py` draws and asks; `crawl.py` decides what a screen holds.** `tui.py` knows no vendor, no skill matrix and no
  report, writes no file, and is the one module that speaks gum.
- **A screen reads and never recomputes:** the skill matrix's rule through `status.load_skill_matrix()` and
  `status.load_entry_paths()`, its columns through `status.load_skill_paths()` — a refusal shown in its own words —, a
  file's row through `status.load_file_row()`, the vendors through `load_active_vendors()`, the
  command line through `build_command()`, the timeout from `config.AGENT_TIMEOUT_MINUTES`. Presentation arithmetic stays
  presentation: a count of rows, `<k> / <n>`, a session's seconds, the columns that fit.
- **Names follow `AGENTS.md` § Canonical vocabulary:** a gum call is `gum_<subcommand>` (`gum_table`, `gum_style`,
  `gum_choose`, `gum_filter`) and the one private prompt call `_gum()`; a screen's rows are descriptors (`_step_rows()`,
  `_file_rows()`, `_skill_rows()`); an action is named for what it writes and returns its exit code
  (`_write_crawl_reports()`, `_write_added_path()`, `_write_marked_skills()`, `_write_removed_path()`). Forbidden:
  `render_`, `show_`, `print_`, `draw_`, a screen class.
