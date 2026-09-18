# Skill: a text-based user interface (TUI) — tables, lists and forms in gum

An owner of a TUI — a module's `sub_module_terminal/`, or a sub-module that opens a TUI — draws
every screen in gum, the one terminal instrument the host admits (`AGENTS.md` § Values, *Minimum
requirements*). Python decides what a screen holds — its rows, its columns, its words — and gum
draws it and takes the answer. The rule is neuro-optical consistency (`AGENTS.md` § Architecture
shape): a screen is read by eye before it is understood, so one concept always takes one form, a
change of form means a change of meaning, and the decision and the result stand where the eye
lands. What each screen holds and what each answer writes is the owner's own skill, beside its
code — `skill_<domain>_terminal.md` for a module's terminal,
`module_skills/sub_module_scalability_crawler/skill_scalability_crawler.md` § The TUI for the
crawler; how a screen is drawn is this skill. *The repository shows the destination, not the
road*: nothing measures, checks or schedules a screen — a hand runs it.

## The instruments

One role, one instrument; the one module that speaks them is the owner's `tui.py`, one file
five times by extraction (`glossary.md` § Twice by extraction).

| role | instrument | draws | never |
|---|---|---|---|
| context, an outcome | `gum style`, a rounded border in the state's colour | the header block that opens a run; a warning about what an action does; the result or the failure that closes it | a banner; a block inside a block; a block around a table |
| rows of one kind, read | `gum table --print` | the state, the steps, the plan, a preview, the changes, the results | a colour on a cell, a row or a border; the interactive `gum table` |
| a choice | `gum choose` | the action, each form of the action, every gate | `gum confirm`, whose default is shown by colour alone; `gum input` for a value the tree already holds |
| a value of a set too long to list | `gum filter`, inline, its placeholder an example the caller gives | a path of the tree | `--no-strict`, whose Enter returns the text typed, not the value under the cursor; a placeholder written into `tui.py`, which holds no sentence of its own |
| a line | Python's `print` | a fact beside a table, progress, `wrote …`, `CANCELLED` | a line rewritten in place; a cleared screen; an escape code written by Python |

## The screen

- **Order, top to bottom:** context → state → decision → result. The eye lands on the last line, so
  an action ends on its result or its failure, and nothing is printed after either.
- **One blank line** between sections — above a table, a list, a block; none inside one.
- **Density:** one header block per run; on a screen one decision, and one table per kind of row.
  Forbidden: a heading above a table (its header row is its heading), the same rows twice on one
  screen, ASCII art, an emoji, a gradient.

Each screen answers six questions, each in one place:

| question | answered by |
|---|---|
| where am I | the header block; the prompt's header |
| what is configured | the state table of the action's objects; the steps table |
| what have I selected | the steps table's choices; the plan; a preview; the changes table |
| what am I selecting now | the step shown `CURRENT`; the prompt's header |
| what happens next | the `PENDING` steps; a gate's question |
| what exactly runs | the plan's `command` line, verbatim, and what it will write |

## One concept, one representation

A state is a word from one closed list; a symbol and a colour repeat the word and never replace it.
An owner may name a state of its own beside these, in its own skill, on the same terms.

| word | means | symbol | colour | plain output |
|---|---|---|---|---|
| `DONE` | a step answered, an action carried out | ✓ | green | `[DONE]` |
| `CURRENT` | the step asked now | → | cyan | `[CURRENT]` |
| `PENDING` | a step still to come | ○ | — | `[PENDING]` |
| `WARN` | what an action refuses, and what it will overwrite | ⚠ | yellow | `[WARN]` |
| `CANCELLED` | Esc, `cancel`, `quit` or Ctrl-C: nothing more is written | ⚠ | yellow | `[CANCELLED]` |
| `FAILED` | one item of a list the action could not carry out | ✕ | red | `[FAILED]` |
| `ERROR` | the failure that ends the run | ✕ | red | `[ERROR]` |

- A colour is drawn only where gum draws one: a block's border, a prompt's cursor and header. A
  table cell and a printed line carry the word and the symbol, uncoloured — gum strips a colour from
  a cell, and Python writes no escape code.
- Forbidden: a colour or a symbol without its word; a coloured row (`AGENTS.md` § Rejected
  vocabulary); `running`, `ok`, `success`.

## Tables

- **A table** holds rows of one kind with more than one field; one fact is a line
  (`repository root  <path>`, `command  <command line>`).
- **Columns:** `#` where the rows are numbered, the identifier, then the fields, the secondary last.
  The header words are the register's UI labels (`glossary.md`, the owner's own section), lower
  case. Every table of a TUI is listed in its owner's own skill with its columns and the order
  a narrow terminal drops them in.
- **`#` counts from 1 in the order the file or the queue holds;** a screen sorts nothing.
- **A cell is the value as it stands** — a count, a state word, a mark, a number as the file carries
  it; `—` where no value applies. Forbidden: an age, a percentage, a date reformatted.
- **Width is measured at invocation,** never written: gum's table neither wraps nor cuts, so Python
  leaves columns out in the drop order until the table fits and prints
  `left out at <n> columns: <names>`. The identifier is never left out or cut; wider still, the
  terminal wraps it. Off a terminal every column stays.
- **A table prints whole:** no pager. A bound, when a table has one, is a constant of the
  owner's `config.py` and is never silent — the rows it leaves out are counted in a line under
  it.
- **Invocation:** the rows on gum's stdin as CSV from Python's `csv`; `--border rounded`,
  `--border hidden` in plain output; `TERM=dumb` in gum's environment, so gum bolds no row.
  Forbidden: `--widths`, a colour flag, a table padded by Python.

## Lists

- **A list is a table a hand picks from:** each label is its row's columns aligned, the second line
  of the header holds the column words over them, and the value gum returns is the row's identifier
  after a tab (`--label-delimiter`) — never a label parsed back. The rows are not drawn a second
  time above the list.
- **Options in their file's order.** The cursor starts on the first option; what a row already holds
  starts chosen. gum matches `--selected` against a label, never a value, so the call names the rows
  chosen by their labels. Nothing is sorted, and nothing is remembered between runs.
- **The header is the decision's register label** — or a gate's question.
- **Nothing is invented beside an option** — no description, no cost, no sign of a default.
- **A list of one row is answered without asking** (`--select-if-one`); the next steps table shows
  it `DONE`.
- **Selection prefixes and colour are arguments of the call:** the cursor `> `, the selection
  prefixes `[x] ` and `[ ] ` in both outputs; cursor, header and selection cyan in normal output.
  Forbidden: gum's own pink and purple, a gum configuration in the tree.
- **`back` and `cancel` belong to gates alone;** a list of data carries neither — Esc is its cancel —
  and the menu ends on `quit`. Forbidden: `exit` (the Lifecycle tab's exit code), `run` (a recorded
  run, `glossary.md` § Run record), a second menu after the action.

## Forms

A form is one decision; an action is its forms in order, and ends.

- **The steps table stands above each form of an action that has more than two,** wherever a hand is
  asked: a step answered `DONE` with its choice, the step asked `CURRENT` with `select now`, the rest
  `PENDING` with `—`. A step is read off the state, never assumed.
- **The plan stands before anything outside this program runs:** the table of the choices, what
  exactly will run verbatim, what it will write, then the gate `<verb> …?` — the verb, `back`,
  `cancel`. `back` asks the action's forms again from the first, every default preselected.
- **An action shows what changes before it writes it:** the changes table — only what changes — or
  the line `no … changes`, and then the gate drops its affirmative option and offers `back` and
  `cancel` alone.
- **An action whose preview stands where the choices are read draws no steps table.**
- **The affirmative option comes first, so it is preselected:** a gate refuses nothing a hand
  confirms, and an action with the defaults stays an Enter per form and one on the plan
  (`AGENTS.md` § Values, *UCAS*). A gate is not a guard.

## Feedback and progress

- **Nothing waits unannounced.** A screen is a few gum calls; before a slow step a line is flushed
  first.
- **What the program starts keeps the screen** as it runs — its own lines, uncaptured: no spinner,
  no bar, no percentage, no estimate. A session's length is unknown until it ends.
- **A program that works through a list prints one line per item** as it finishes: `<state> <item>`
  and what it cost, measured around the step and never stored.
- **After an action** `wrote <file>`, then the result last: the results table and the `DONE` block,
  or the failure.

## Failures and exits

- **A failure is a block on stderr, the run's last:** `✕ ERROR <what failed>`, `where <path or file>`,
  `why <reason>` when it is known, `next <what a hand does>` — the reason in the refusing rule's own
  words. In plain output, without gum or wider than the terminal, the same lines without a border.
- **An expected failure has no traceback;** an unexpected one keeps Python's, the one fact a defect
  needs.
- **One screen holds one failure:** the first failure ends the action.

| exit | when |
|---|---|
| 0 | the action carried out; Esc, `cancel` or `quit` — nothing written |
| 1 | a failure, its block last on stderr |
| 2 | an argument the program does not take |
| 130 | Ctrl-C, gum's code and this program's: one `CANCELLED` line; what an action already started stays |

## Colour and plain output

- **A colour is a number of the terminal's own palette,** so a hand's theme decides the shade: 6
  cyan the context and the choice asked now, 2 green done, 3 yellow attention, 1 red failure. Nothing
  else is coloured by a TUI of this tree, and nothing is dimmed but gum's own key line and the
  filter's prompt and placeholder, in gum's grey.
- **Plain output switches on by itself** when `NO_COLOR` is set and not empty, `TERM` is `dumb`, or
  standard output is not a terminal (`OUTPUT_PLAIN`, in each owner's `config.py`, twice by
  extraction): no colour — gum is handed `NO_COLOR` —, no symbol — the word in brackets —, no border
  — a table `hidden`, a block printed as its lines.
- **Never changes between the two:** a word, the order, a count, a column, an exit code.
- Forbidden: a flag for either output, a theme, bold or underline set by the program.

## Help

`-h`, `--help` prints the action module's docstring and exits 0. The docstring holds the actions, the
keys — Enter, x, Esc, Ctrl-C —, plain output and its three conditions, the exit codes and three
examples. Each owner's own skill gives the line that runs it without the Makefile.

## Declined here

| asked of a terminal interface | declined, because | rests on |
|---|---|---|
| Rich, Textual, curses | the host is the standard library and gum 2 | `AGENTS.md` § Values, *Minimum requirements* |
| `--json` | the snapshot, or the artifact, is the machine-readable state | `glossary.md` § Stores |
| `--no-input` | a hand alone runs a TUI, one action per run | `AGENTS.md` § Values, *A rule may be read* |
| `--simple`, `--a11y`, `--no-color`, `--no-animation` | plain output follows the environment, and nothing animates | § Colour and plain output |
| a spinner, a progress bar, a percentage | a spinner hides the lines of what the program started, and a session's length is unknown | § Feedback and progress |
| a main loop, an `exit` option, a second menu | one action per run | `AGENTS.md` § Values |
| the branch or the repository's name in the header | no decision needs it | § The screen |
| a pager | a second screen to leave before the decision; the tables are short | § Tables |
| a coloured cell or row | gum strips it, and the word says it | § One concept, one representation |
| a table of grouped failures | the first failure ends the action | § Failures and exits |
| `--lang`, a translation | one language, British English | `AGENTS.md` § Canonical vocabulary |

## Where the screens live

- **`tui.py` draws and asks; the action module decides what a screen holds.** `tui.py` knows nothing
  of the owner's own objects, writes no file, and is the one module that speaks gum.
- **An owner reads its module's `config.py` where it can:** an owner that can import its module's
  standard-library `config.py` does so and duplicates nothing; the one that cannot
  (`module_features`, whose `config.py` imports numpy) carries registered copies (`glossary.md`
  § Twice by extraction).
- **A screen reads and never recomputes:** every fact it shows comes from the function that owns it.
  Presentation arithmetic stays presentation: a count of rows, `<k> / <n>`, a step's seconds, the
  columns that fit.
- **Names follow `AGENTS.md` § Canonical vocabulary:** a gum call is `gum_<subcommand>` (`gum_table`,
  `gum_style`, `gum_choose`, `gum_filter`) and the one private prompt call `_gum()`; a screen's rows
  are descriptors (`_step_rows()`, `_file_rows()`, `_skill_rows()`); an action is named for what it
  writes and returns its exit code (`_write_crawl_reports()`, `_write_search_profile()`), and an
  action that writes nothing is named for what it draws (`_recorded_search_tables()`) and returns its
  exit code too; an action that starts a target does so through `_make()` — one call of `make`, its
  lines uncaptured. Forbidden: `render_`, `show_`, `print_`, `draw_`, a screen class.
