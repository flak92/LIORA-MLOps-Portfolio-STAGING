# AGENTS — the contract of this repository

The governing contract for every change, human or agent. Read the project in
this order: **AGENTS.md → module names →
`README_module_<name>.md` → the module's own `skills/` → code**, with
`module_skills/` beside them for the rules that cross modules, indexed by
`module_skills/README.md`. (A `README.md` is general information, not part of
the working path.) If a change conflicts with this file, the change is wrong.

## Values

- **Destination, not road.** *The repository shows the destination, not the road*. No tests, no security
  layers, no CI, no precautionary guardrails; the only guards are the ones the
  mathematics requires, and a stage proves itself by running. One crawler
  stands beside the chain: the scalability crawler,
  `module_skills/sub_module_scalability_crawler/`, reads each file a hand lists
  against the skills a hand marks for it, writes a report a hand reads, and its
  snapshot; a hand runs it in a terminal, one action per run, and nothing
  schedules it; it gates nothing, edits no file but its skill matrix, commits
  nothing.
- **Minimalism.** Every line, file, module and dependency has a concrete
  purpose. If its purpose cannot be named, it goes.
- **Minimum requirements.** Python 3.12.x with `venv` and `pip`; the container
  is `python:3.12-slim`, one image for the tree. A library is added
  only when the standard library and the current stack — `duckdb`,
  `mlflow-skinny`, `numpy`, `optuna`, `xgboost-cpu` — cannot do the job, or when
  it is the field's own instrument for a responsibility this project names and
  the stack's equivalent would be a private reimplementation of it: § Canonical
  vocabulary's preference for an established name over a local synonym, read
  forward from names to instruments. `mlflow-skinny` is the one such addition
  and the trial ledger the one such responsibility. By the same reading the
  host admits `gum`, the field's own instrument for a responsibility this
  project names — a hand's choice in a terminal and the screens around it, the
  crawler's text-based user interface (TUI) — where the alternative would be a
  private chooser and table over curses: a binary of the host,
  no pin of `requirements.txt`. `requirements.txt` declares
  the project's direct dependencies only, one pinned version each.
- **KISS / YAGNI / DRY / SOLID.** The simplest correct implementation, built
  for the need that exists, never for a hypothetical one. One responsibility
  per module; repeated logic becomes one function, not three copies.
- **UCAS — Useless Click Avoiding System.** Manual steps, clicks and context
  switches that can be automated, are: `make all` runs the whole pipeline
  from a fresh clone, every stage is idempotent in what it derives — the
  trial ledger alone accumulates, each search appending its `hpo_<n>` runs,
  until a hand clears it, and beside the chain the crawler's reports, one entry
  appended per file crawled — and the dashboard opens itself.
- **Main = clean working logic.** No test frameworks, security layers,
  validation frameworks or precautionary guards. What stays are the seven
  guards the mathematics requires: causality invariants (`indicators.asof_index`) and
  arithmetic preconditions (the full canonical grid inside the frozen research
  window, asserted per asset by `labels.load_research_1m`, and a finite,
  positive ATR at every decision, asserted beside it; the aligned decision
  grids of the arrays `dataset.load_xy` joins by position — one guard, asserted twice, because the feature parquets agreeing with each other and X agreeing with Y are two checks; a finite
  catalogue after the warm-up, asserted by `catalogue.build_catalogue`; the download that
  aborts on a short post-listing day, and the listing probe that aborts when a
  symbol's history starts after the window) — and beside them, not guards:
  the one-line message of a status stage with nothing to report, naming the
  stage to run first, and a venue's own error code surfaced as it came. A test suite, a linter,
  a coverage gate, a workflow or a merge block does not belong here. No debt
  marker in a tracked file — this contract names the forbidden form — and no code left inside a comment: a marker is a
  postponed decision, a commented-out line is a version git already holds.
  Thread caps (`nthread=1`, `OMP_NUM_THREADS=1`) are part of correctness, not
  a setting.
- **Research logic over tooling.** External sources, libraries and
  infrastructure are implementation details. The repository should expose the
  mathematical and causal research pipeline as directly as possible.
- **Source-neutral downstream.** Venue-specific logic ends at ingestion and
  data-quality provenance. Features, labels, validation, modelling and research
  simulation operate on the canonical research dataset.
- **Academic, not production.** Prefer explicit equations, causal invariants and
  reproducible transformations over production security, orchestration and
  validation frameworks.
- **Pipeline-first.** The repository exists to close one full chain:

  ```
  market sources → ingest → validation necessary for correctness → canonical dataset
  → features / labels → training / retraining → strategy / results → monitoring
  ```

## Architecture shape

`module_*` is a top-level project responsibility; `store/` is persisted or
generated state. Four modules — one Python package `module_<domain>` each, in
the order the data moves through them — and, around them, the launcher that runs
them and carries no dataflow of its own:

```
module_data/         sources → normalised raw 1m → one canonical DuckDB per asset
module_features/     canonical DuckDB → the bars of the register → the feature catalogue, one parquet per timeframe, the per-asset contract and its snapshot
module_ml/           the catalogue and the canonical path → X, Y → search → model → research simulation
module_monitoring/   presentation of what the three computational modules measured about themselves, of what record.py measured around every stage and of the dates of the canon's crawler's reports, and the server that serves it
the root             the Makefile and docker-compose.yml that run the four, record.py, the five stores, one folder each under store/, and the canon: this contract, the name register (module_skills/glossary.md), the cross-cutting skills, the index of every module's own, and the one sub-module that reads each listed file against the skills a hand marks for it (module_skills/sub_module_scalability_crawler/)
```

Each module holds its package, its orientation `README_module_<domain>.md` and
its own `skills/` under one directory; nothing above it belongs to one module
alone. `make all` from a fresh clone runs the chain. A reference is a path in
backticks, always.

`module_skills` participates in no runtime import and in no dataflow of the chain:
its one sub-module reads the files a hand lists and writes their reports and one snapshot about them. **No module
imports another.** What would cross a module boundary as an import crosses it as a
file in a store instead — the five `STORE_*_DIR` the launcher names
(`module_skills/glossary.md` § Stores), the per-asset contract
`<TICKER>_catalogue.json` the feature layer writes and every ML stage reads, the
four snapshots — the three each computational module writes about itself and the crawler's —
which the dashboard serves, the run record `record.py` writes around every stage — or as a copy
registered in `module_skills/glossary.md` § Twice by extraction, identical to the
byte on every side unless its row there says equal by value. The basket is the launcher's: `TICKERS` in the
`Makefile`; every stage is told its assets by `--tickers` and defines
none. A new `module_<domain>` is justified only by a
distinct responsibility with a stable input/output boundary; until then the
owning module is extended, and no repository is ever created for what two
modules share — a dozen shared lines are a registered duplicate, not a `common`.
`module_features` is that case: its input is the canonical series, its output
one parquet per timeframe that any model could read and the contract that names
them, and nothing above it in the dataflow imports it.

Each `module_*` is an **extracted bounded context**: its domain rules, its
orientation and its code sit together under its own directory, so its meaning is
never reconstructed from documentation that stayed elsewhere. It runs standalone
against the `store/<content>/` folders it touches, each named by the launcher
(`python -m <module>.<stage> --tickers <TICKER>`, in a venv with the
`STORE_*_DIR` it reads exported or in a one-off container of its runner), and knows
nothing of the others: they share the store contract, the files it names and the
copies the register lists, and nothing between them speaks over a network.

Regular, predictable, symmetrical, easy to scan — the structure should be
recognisable by eye before it is parsed (neuro-optical consistency):

- **names also define visual structure.** Before introducing a file or
  directory, determine its semantic family and derive its name from that
  family's established grammar, so analogous objects sort together and both the
  object's role and its expected location are predictable from its name. The
  detailed sorting grammar lives in
  `module_skills/skill_sorting_files_naming_standard.md`;
- one obvious responsibility per module; no wrappers without logic of their own;
- analogous names for analogous objects (`download_binance.py` ↔
  `download_bybit.py`, `store/assets_artifacts/<TICKER>/<TICKER>_<artifact>.<ext>`, `ml-<stage>`
  targets); each computational module (`module_data`,
  `module_features`, `module_ml`) measures its own domain state in `status.py`,
  and `module_monitoring` presents their snapshots; the canon's sub-module
  measures the tree against the canon in a `status.py` of its own;
- **taxonomic ordering — the category token comes first, so siblings sort
  together.** A listing is read by eye before it is parsed: at the root
  `module_data`, `module_features`, `module_ml`,
  `module_monitoring` — the chain in its own order — then `module_skills`,
  then the one folder `store/`, whose five children — `assets_artifacts`,
  `raw_1m`, `run_records`, `status`, `trials` — sort together inside it, the
  category token spoken once, by their parent: blocks, not scattered entries. If
  renaming would put things of one category next to each other, rename them;
- short, predictable paths, built only in a module's `config.py` — never
  assembled at the point of use; the one exception is an external format's own
  file names, built by its adapter (`module_data/lean.py` builds the QuantConnect
  Lean tree's file names, `record.py` those of the four pipeline stores it lists,
  every store but `store/trials/`)
  — and the browser, which has no config module and fetches its four snapshots
  (`data_status.json`, `features_status.json`, `ml_status.json`, `skills_status.json`) under
  `/store_status/` and the run and `/devops/api/*` routes by literal
  name; one asset is one folder,
  `store/assets_artifacts/<TICKER>/`, one file per distinct artifact
  responsibility. The artifact folder is the ticker in capitals, the raw tree
  is the symbol in lower case because Lean demands it — that difference is a
  boundary, not an inconsistency to tidy away. A store's variable
  spells the exact canonical tokens of its path, the parent folder's first and
  then its child's, so the name predicts the
  directory it names — on the host `STORE_RAW_1M_DIR` → `store/raw_1m/`,
  `STORE_RUN_RECORDS_DIR` → `store/run_records/`, in a container the same
  variables → `/store/raw_1m`, `/store/run_records`;
- one convention per language: BEM in CSS, snake_case in Python and JSON,
  the same hierarchy everywhere, no accidental exceptions.

## Pre-AWS architectural direction

Pre-AWS is this repository's word for its own shape: a local, academic
architecture whose boundaries would still be the right boundaries after local
storage, local container execution and local stage order were replaced by their
standard equivalents on Amazon Web Services (AWS). No cloud is used and none is
planned; the mapping is described in `module_skills/skill_pre_aws_solution.md`
and built nowhere.

- **Academic, not AWS.** The runtime is local — one image for the tree under
  docker compose, driven by a Makefile — and the goal is a correct dataflow with visible
  responsibilities: a demonstrator, not a deployment.
- **Every boundary decision weighs the future mapping.** Where a function lives,
  who writes a file, what a stage takes as its parameter, how a container is
  started — each is chosen so the mapping stays a rename, never a redesign;
  nothing is implemented for the cloud.
- **No cloud complexity without an academic need.** A mechanism that exists only
  because production would require it, and that the research logic does not
  need, is described in the skill as its future equivalent and never built here.
  Stated, not mitigated.
- **The asset is the namespace.** `ASSET=<TICKER>` — `--tickers` at the process
  boundary — selects every datum and artifact; no code, file, function or
  service definition is named for a ticker, and a ticker may name a convenience
  alias in the Makefile, with its sunset note, never a target another file
  depends on; a new asset is one ticker in the `Makefile`'s `TICKERS`, and
  nothing else.
- **Compute owns no state.** A stage reads a store, writes a store and exits; it
  holds nothing between invocations, binds no port, reads no `ASSET` and assumes
  no resident peer.
- **Storage is separate from compute.** Pipeline state lives in the five stores,
  one folder each under `store/`, named to every `config.py` by its
  `STORE_*_DIR` and mounted from `store/<content>/` at `/store/<content>` into each service that touches
  them, read-only where a service only reads
  (`module_skills/skill_asset_containers.md` § The topology) — never
  inside a container and never inside a module's source tree; the image carries the
  pins and nothing else, the code and the state arrive as mounts, and the four
  snapshots are the one store tracked whole,
  beside the tracked remnant of the
  artifacts store (D15). The crawler's reports lie beside the crawler, tracked,
  because they are documents a hand reads and not state of the chain.
- **Modules are built by ownership and lifetime.** A function sits beside the
  functions that write the same state and live as long as it does, never beside
  what happened to be written with it; every object is classified before it is
  placed.
- **Every placement is argued, and the mapping is the test.** For every object
  a module holds, its `README_module_<name>.md` § Design rationale writes down,
  in one row, the answers of `module_skills/skill_self_explaining_naming.md`
  § The naming review that place it — why here, why beside these, why this
  boundary — and which row of the mapping table it answers to, the fourth being
  the test of the first three. An object one of whose responsibilities answers
  to no row, or to two, is questioned before it is committed; a file that holds
  several responsibilities — a descriptor per store —
  answers with one row each, and says so. The rows are
  `module_skills/skill_pre_aws_solution.md` § The mapping table. The canon has
  no orientation of its own: its sub-module argues its objects in
  `module_skills/skill_scalability_crawler.md` § Design rationale, and its
  documents are the rows of the index.
- **Names carry the responsibility.** A name says what the object is, what it
  does and where it belongs — a service by its runtime role, a store by what it
  holds, a function by its verb from the closed list or by the quantity it is;
  local names never imitate cloud resources, and cloud resources would inherit
  the local vocabulary unchanged.
- **The Makefile is the local developer interface.** It names stages after their
  modules, lists their order and never schedules; orchestration sits above the
  stages and inside none.
- **Docker is compute.** A container is the local counterpart of the one-off
  container a cloud runtime would launch per stage and per asset; the runners
  `data`, `features` and `ml` are how the fan-out does it locally.
- **A few assets are proof enough.** The whole chain on `BTC` demonstrates the
  architecture; scale is `ASSET=<TICKER>`, never hundreds of assets.

Cloud proper nouns are external vocabulary. Apart from the repository's own word
*Pre-AWS* — `module_skills/glossary.md` § Pre-AWS direction, and the `pre_aws`
file stem it registers, the skill's and the report's — they are spoken only
where the stance is stated, reviewed or a local object is seated: this section
and § Skills absent here, described, `README.md` § Architectural direction, the
skill's prose, the column *the same responsibility elsewhere* of its mapping
table, `REPORT_pre_aws_minimalism.md` — the seats reviewed for excess; and, at
the edge of a local rule, the one seat paragraph of
`module_skills/skill_asset_containers.md`, `module_skills/skill_determinism.md`
(its last bullet, the skill having no headings),
`module_data/skills/skill_candle_canonicalisation.md` § 15 and
`module_monitoring/skills/skill_devops_panel.md`, each naming the primitive in
the table's words and citing the skill for the rest. Never in a make target, a
compose service, an environment variable, a payload key, a code comment, an
identifier, or a tracked path but the `pre_aws` stem. The non-goals, the twelve
classes, the review of what stays local and the mapping table are
`module_skills/skill_pre_aws_solution.md` — a cross-cutting skill of the kind
§ The default choice names, beside `skill_asset_containers.md`.

## Canonical vocabulary

**Names must be self-explanatory before they are project-specific. Prefer
established software-engineering terminology over project-specific synonyms: if
a concept already has a widely recognised name, use that name — in code, in
documentation, in the skills and in the interface alike — and do not invent
local terminology for a standard concept. A glossary confirms meaning; it must
not be required to decode an obscure name.**

One concept, one name — in the code, in the artifacts, in the interface, in the
Makefile, in docker compose and in the documents. The
register is `module_skills/glossary.md`, and a new name enters it in the same
commit that introduces it. The word "test" never names a fold.

And one name, one concept. A name that could denote two things **in the same
scope** is renamed until it denotes one. The scopes are enumerated so the rule
applies without argument: make targets, compose services, container environment
variables, tracked paths, and Python symbols within a module. A name shared across *different* scopes is not a
collision.

**Derived, never drafted.** A derived artifact is generated from source and
config and never hand-edited: `<TICKER>_parameters.json`,
`<TICKER>_coordinate_search.json`, `<TICKER>_README.md`, `<TICKER>_catalogue.json`
and the four snapshots. A hand edit to one is a violation.

**Drafted, never derived.** A drafted artifact is a hand's decision written down
and never computed from another file: `to_crawl.md`, the paths a hand lists and
the skills it marks for them; `<TICKER>_coordinate_search_profile.json`, the
columns a hand admits to a search, the state it starts from, the grid of each
coordinate and the loops of a round; and, once a hand has promoted one,
`<TICKER>_feature_set.json` and `<TICKER>_barriers.json`. Each is written by one
program — its sub-module's TUI, or the promotion — and each may equally be
edited in the file, because the same decisions write the same bytes and a rewrite
that changes nothing leaves `git status` clean. A stage that derives one is a
violation.

**Rule-derived structure over repeated project knowledge.** When a family —
assets, venues, timeframes, paths, artifact files, payload keys, pipeline stages
— is governed by one definition, derive the repeated representations from it
rather than copying the same list into several files: `TICKERS` in the
orchestration `Makefile` — the launcher — is the one definition the fan-out and
every `--tickers` derive from; a module is told its assets and never defines
them.
The limit is equally binding: no generator,
no metaprogramming, no abstraction layer for a one-off value — and none for a
file whose whole value is being read.

Every layer has a closed grammar, the way CSS has BEM. A name is **derived**
from its layer's grammar, never invented:

| layer | grammar | in this repo | what it forbids |
|---|---|---|---|
| constants | `<OBJECT>_<ROLE>_<PARAMETER>_<UNIT>` | `ATR_WILDER_SMOOTHING_PERIOD_BARS` | `RSI_N` |
| constant comments | a comment that explains a Python module-level constant takes one of PEP 8's two forms, by what it explains: an inline comment on the line of the one constant it explains; a block comment directly above the lines it explains when they are several constants, or one constant whose value spans several lines; the `# twice by extraction` marker explains nothing and stands where D14 places it; a file that departs moves its comments with its next change | `BYBIT_KLINE_REQUEST_LIMIT = 1000   # < 1440 -> …`; the block comments above `BINANCE_KLINE_URL` and above `VENUE_SCAN` | a block comment above a one-line constant it alone explains; an inline comment that explains the lines under it |
| external I/O functions | `<verb>_<object>`, verb from the closed list `fetch_` (network), `load_` (storage → memory), `write_` (persist), `parse_` (bytes → values) | `fetch_klines`, `load_xy`, `write_parquet`, `parse_zip` | `get_`, `process_`, `handle_` |
| conversions | `to_<representation>` | `to_class`, `to_json_safe` | ambiguous `convert` |
| composite constructors | `build_<object>` | `build_x` | `make_stuff` |
| functions that *are* a quantity | no verb — the name is what it returns | `rsi`, `atr`, `sharpe_annualised`, `triple_barrier` | `calculate_rsi` |
| pure descriptors | a noun phrase naming the returned object; a descriptor does no I/O — the moment it fetches, loads or writes it takes that verb, the moment it assembles it takes `build_` | `symbol`, `artifact_dir`, `fold_bounds` | `get_fold_bounds`, `fetch_symbol` |
| populations of rows | `<population>_set` / `_window` | `training_set`, `scoring_set`, `prediction_window` | `get_train_indices` |
| report fragments | `<section>_block` | `sample_block`, `strategy_block`, `hyperparameter_search_result_block` | `make_sample_dict` |
| statement constants (SQL text) | `<OBJECT>_<KIND>`, kind from the closed list `DDL`, `INSERT`, `SCAN`, `PREDICATE`, `COLUMNS` | `CANONICAL_DDL`, `BAR_INSERT`, `VENUE_SCAN`, `OHLC_INTACT_PREDICATE`, `Y_COLUMNS` | `SOURCE_SWITCHES`, `QUERY_1` |
| conversion factors | `<UNIT>_PER_<UNIT>` | `MILLISECONDS_PER_MINUTE`, `MINUTES_PER_DAY` | `MS_MIN`, `60_000` inline |
| module-private helpers | a leading `_` on the name its layer's grammar gives, for a helper no other module may import | `_pnl_block`, `_classification_block` | an `_` name imported by another module |
| gum calls | `gum_<subcommand>`, the subcommand from gum's own closed list — `table`, `style`, `choose`, `filter` — for the one function that speaks it, and `_gum`, the one private call that runs a prompt and returns its answer, in the `tui.py` of a sub-module that draws a TUI and nowhere else — today `module_skills/sub_module_scalability_crawler/tui.py`, and a second copy is registered, never a second spelling (`module_skills/glossary.md` § Twice by extraction) | `gum_table`, `gum_choose`, `_gum` | `render_table`, `show_menu`, `print_block`, `draw_`; a gum command line outside `tui.py`; a second spelling of `tui.py` |
| CLI entry | `main()` — one per stage module, returning the exit code | `main` | `run`, `cli`, `entrypoint` |
| quantities | `<what>_<unit>` | `fold_start_ms`, `equity_1m`, `returns_15m` | `n_min`, `off` |
| index arrays | `<population>_rows` | `training_rows`, `window_rows`, `scoring_rows` | `tr`, `wi`, `oi` |
| booleans | `<subject>_<predicate>`, stating the condition that is true; a function that asks takes `is_`, `has_` or `requires_` — state, possession, obligation | `entry_observable`, `label_valid`, `is_full_utc_day()`, `is_artifact_set_complete()` | `flag`, `ok`, `check`; `should_`, `check_`, `needs_`, a bare `trigger` |
| artifact keys | snake_case, the same word as the identifier that produced it; a count is `<what>_count`, a quantity with a unit `<what>_<unit>`, a share `_pct`, a formatted UTC string `_utc`, epoch milliseconds `_ms` | `scored_row_count`, `ffill_bars`, `coverage_pct`, `generated_at_utc` | a separate vocabulary for JSON; a bare plural (`gaps`) or an adjective (`ambiguous`) as a count; `n_`; `ret` for return |
| features | `[<normaliser>_]<term>{_<operator>_<term>}_<timeframe>`, a term `[<series>_]<indicator><parameter>` or a bare series, read off the catalogue record — the rest is `module_features/skills/skill_feature_taxonomy.md` | `ema20_minus_ema50_over_atr14_4h`, `centered_rsi14_1h`, `range_position20_15m`, `close_minus_sma200_over_atr14_4h` | `feature_3`, `f_rsi`, `rsi_14`, `sma_200`, `trend_4h` |
| stored columns | the quantity for OHLCV, `<what>_<unit>` for anything derived, `<subject>_<predicate>` for a boolean — and a column and the key that publishes it carry **one** name | `timestamp_ms`, `ffill_bars`, `zero_volume_bars`, `binance_valid` | `n_ffill`, a column and key that disagree |
| Makefile targets | `<module>-<stage>` for a stage of a runtime module — run in a one-off container of that module's runner — and `<module>-all` for its chain; `tmux-<module>-<stage>` for the detached twin of a stage that outlives the terminal — only a stage that resumes may have one; a sub-module's own TUI takes `<module>-<what it opens>` and is run by `python3` on the host, never in a container — gum asks a hand in the terminal it was started from, and a TUI does not resume, so it has no `tmux-` twin — `features-coordinate-search-terminal`; `skills-crawl` and `skills-status` for the canon's crawler and its snapshot, run that way for the second reason too, the canon having no runner; only the lifecycle targets go bare (`all`, `build`, `help`, `on`, `off`, `all-record`), `on` / `off` being the presentation switch, and a ticker alias of a lifecycle target carries its own sunset note | `data-ingest`, `ml-hpo`, `features-all`, `tmux-ml-coordinate-search`, `features-coordinate-search-terminal`, `skills-status`, `on` | a bare stage (`ingest`), a `docker-` twin of a stage (there is one way to run a stage), a target named after the tool (`docker-run`), a detached twin of a stage that cannot resume, a second switch pair (`start` / `stop`, `up` / `down`), a second Makefile carrying stage order of its own |
| directories | `<category>_<detail>/` for a module; the stores are one folder `store/` whose children are `<content>/` — the container's `/store/<content>` read back onto the host; a raw store names its granularity with the compact timeframe token, `store/raw_<timeframe>/` | `module_*`, `store/`, `store/raw_1m` | a kind scattered through the alphabet, a store spelling its timeframe in sorting slots, `repository_module_<domain>/`, `store_<content>/` at the root, a child that repeats its parent's token (`store/store_raw_1m/`) |
| sub-modules | `sub_module_<domain>/` inside the module, or the canon, that owns it — its own `config.py`, its own `main()`, no part in the chain's dataflow (§ The default choice) | `module_monitoring/sub_module_devops/`, `module_skills/sub_module_scalability_crawler/`, `module_features/sub_module_coordinate_search_terminal/` | a sub-module at the root; a sub-module of a sub-module; a sub-module that imports another module (D02) |
| images | `liora-1m-pipeline`, one for the tree, built from the root `Dockerfile` | `liora-1m-pipeline` | compose's `<project>-<service>` default, an image per service, an image per asset, an image per module |
| compose services | a runtime role, never an image or a ticker — the runners `data`, `features`, `ml`, the residents `dashboard`, `devops` | `ml`, `dashboard` | `pipeline`, a service named for an image or a tool, a service per asset stage |
| store paths | `store/<content>/` on the host, `/store/<content>` inside a container, `STORE_<CONTENT>_DIR` the variable that names the one to the other | `store/raw_1m/`, `/store/raw_1m`, `STORE_RAW_1M_DIR` | a path derived from `__file__`, `/app/store/<content>` as an address, a store literal at the point of use |
| a module's own skills | `module_<name>/skills/`, holding every rule about that module and nothing else | `module_data/skills/`, `module_features/skills/`, `module_ml/skills/`, `module_monitoring/skills/` | a single module's rule kept in `module_skills/`; a second copy of one rule in both; a module's rule in `module_skills/` |
| a module's orientation | `README_module_<name>.md`, the name derived from the module directory it sits in | `module_data/README_module_data.md`, `module_features/README_module_features.md`, `module_ml/README_module_ml.md`, `module_monitoring/README_module_monitoring.md` | `module_data/README.md`; an orientation file that restates a skill |
| artifact files of one timeframe family | `<asset>_<artifact>_<timeframe-slot>.<ext>`, slots per the standard `ss-mm-hh-dd-MM` (`module_skills/skill_sorting_files_naming_standard.md`) | `BTC_features_ss-15-hh-dd-MM.parquet`, `BTC_features_ss-mm-04-dd-MM.parquet` | `BTC_features_15m.parquet` — siblings that no listing orders by granularity |
| CSS | BEM `block__element--modifier`, the class named for what it marks | `frame__head`, `pill--active`, `final-holdout` | `.red`, `.diag` |
| JavaScript functions at file scope | lowerCamelCase, verb from the closed list `build<Object>` (returns a DOM node), `render<Section>` (writes into the page), `format<Value>` (value → string), `append<Child>` (mutates a parent), `select<Target>`, `init<Component>`, `fetch<Object>` (network, returns a promise); a quantity or a descriptor carries no verb | `buildMeter`, `renderStrategy`, `formatBytes`, `appendCell`, `fetchRunRecord`, `mean`, `validationFolds` | `makeTable`, a bare noun for a builder (`cell()`, `sparkline()`) |

Constants that carry a numeric quantity — a count, a rate, a duration, a
size, an interval — are named `<OBJECT>_<ROLE>_<PARAMETER>_<UNIT>`, and the
unit is explicit — `_BARS`, `_MINUTES`, `_MS`, `_SECONDS`, `_DAYS`, `_ROWS`,
`_FOLD_ID`, `_RATE`, `_COUNT` — unless the name already says what is counted
(`MINIMUM_TRADES_PER_VALIDATION_FOLD`); a setting handed to a tool as text carries its unit in the value, not in the
name (`DUCKDB_MEMORY_LIMIT = "4GB"`). Enumerations, paths and names carry no
unit; a collection whose values are quantities keeps theirs
(`TIMEFRAME_DURATION_MS`, `FOLD_BOUNDS_MS`, `VALIDATION_FOLD_IDS`). No name is
invented just to satisfy the schema. The parameter word follows the mechanics
— `SPAN` for an EMA,
`SMOOTHING_PERIOD` for a Wilder recursion, `LOOKBACK` for a real rolling
window, `HORIZON` for the future of a label, `INTERVAL` for a sampling step. A
parameter carried by a term of the feature catalogue (`("ema", 20)`) is the
descriptor's own and is never copied into a named constant: the record is the
one place the number lives.
A compact timeframe token inside an identifier (`ANNUALISATION_PERIOD_15M_BARS`, `equity_15m`,
`ohlcv_15m_canonical`) is the timeframe vocabulary of code and schema; the slot
standard governs filesystem names only.
Domain abbreviations (ATR, RSI, EMA, OHLCV, UTC, OOS, HPO, XGBoost) stay
and are spelled out on first use in the documentation; local ones (`N`, `W`,
`TF`, `MIN`, `MAX`, `K`, `XGB`) never cross a function boundary. A one-letter
name is legal because of its semantic role, never merely because it is local:
loop indices, the symbols of a published equation inside its tight kernel, and
SVG geometry may stay short — a domain object (a ticker, an asset, a status
payload, a strategy, a metrics block) carries its semantic name even inside a
function. Write
"QuantConnect Lean" on its first use in a file, code comments included, and "Lean" afterwards. British spelling
throughout the prose (`-ise`, `-isation`); language keywords keep their own spelling. At an
external-format or external-library boundary the external vocabulary wins
inside the call that speaks it, and project names begin at the return value.
The boundaries, each with the file that owns it: the Lean tree
(`module_data/lean.py`), the Binance and Bybit REST parameters
(`download_binance.py`, `download_bybit.py`, and `module_data/config.py` for the venue constants that carry the REST word `KLINE`), xgboost and optuna
(`module_ml/model.py`, `module_ml/hpo.py`), mlflow (`module_ml/hpo.py`), numpy (every module that computes),
argparse (`module_data/config.py`, `module_features/config.py`, `module_ml/config.py` — the one parser, twice by extraction —,
`module_ml/coordinate_search_promote.py`, `module_skills/sub_module_scalability_crawler/crawl.py` and `module_features/sub_module_coordinate_search_terminal/terminal.py`, for their `-h`, `--help` and, in the terminal's case, the asset the launcher names), DuckDB SQL (every module that queries), the SVG
and DOM attributes (every `*.js` of `module_monitoring`, its sub-module included), docker compose (`Makefile`,
`docker-compose.yml`), tmux (`Makefile`), `urllib` (`module_monitoring/serve.py`,
`module_monitoring/sub_module_devops/config.py` and both downloaders), a stage's
command line over `subprocess` (`record.py`), the git command line over `subprocess` (`module_skills/sub_module_scalability_crawler/config.py`, for the root, and `module_skills/sub_module_scalability_crawler/crawl.py`, for the paths an add offers and the commit a report entry names), each vendor's command line over `subprocess` (`module_skills/sub_module_scalability_crawler/crawl.py`, named in `module_skills/sub_module_scalability_crawler/vendors_for_crawling.toml`), the gum command line over `subprocess` (`module_skills/sub_module_scalability_crawler/tui.py` and `module_features/sub_module_coordinate_search_terminal/tui.py`, the two TUIs' one file), the terminal's `NO_COLOR` and `TERM` (`module_skills/sub_module_scalability_crawler/config.py` and `module_features/sub_module_coordinate_search_terminal/config.py`, plain output), `http.server` (`module_monitoring/serve.py` and the panel's own),
`socket` and the Docker Engine API over its
unix socket (`module_monitoring/sub_module_devops/`), the `make` command line over `subprocess` (`module_features/sub_module_coordinate_search_terminal/terminal.py`, the two targets its actions start — the Makefile alone speaks tmux and docker compose), and the file listing of the four pipeline stores
(`record.py`). A
boundary is an exception the conventions name, not an inconsistency they
tolerate.

## Rejected vocabulary

The rejected vocabulary stays as a list of words that steers the repository
toward a lower level of vectors, guiding AI agents toward useful embeddings for
solving problems in a concrete and minimally correct way. No check gates
it. The last column of the grammar table holds the forms bound to one
rule and the register's `never` columns the synonyms bound to one concept; this
list gathers the words bound to neither, and repeats the few the register
already binds that are worth steering away from on sight.

- **directories and path segments:** `src`, `core`, `lib`, `common`, `utils`,
  `helpers`, `manager`, `service`, `assets`, `artifacts`, `data`, `db`,
  `database`, `raw_data`, a lowercase ticker folder, a venue symbol as a folder;
  `repository_module_<domain>`, a numbered package directory
- **module and file stems:** `module_compose`, `module_docker`,
  `module_capsule`, `module_asset`, `module_viz`; `dashboard.py`, `proxy.py`,
  `server.py` beside `serve.py`; a strategy file per asset, a parameters file
  per stage, an `export` stage, a per-asset OHLCV parquet; a module named for
  a cloud resource (`module_s3`, `module_ecs`, `module_eventbridge`); `worker`,
  `processor`; `common`, `shared`, `lib` as a repository or a package for what
  two modules share
- **function verbs:** `read_`, `probe_`, `spool_`, `iter_`, `run_`, `compute_`,
  `_factory`; in JavaScript `load`, `poll`. The stem is rejected as a **verb**: a
  function named for a domain noun the register carries is not one, which is why
  `run_dir()` and `run_payload()` stand — a run is the object of
  `module_skills/glossary.md` § Run record — and why `write_venue_spool()` stands, its
  verb being `write` and its spool the CSV the register names
- **key names:** bare `lag`, `age`, `usage` — without the subject and the unit —
  `mem`, `cpu_pct`, a bare duration for how long a container has been up, a
  hash, `weight` as a Y column, `_ts` on a UTC string
- **interface words:** `online` / `offline`, `alive`, `healthy`, `running` for
  an endpoint, `RAM`, `RSS`, `load`, `utilisation`, `freshness`, `boot`;
  `pill`, `chip`, `tile`, `stat` for a badge; `badge--off`, `status--red`, a
  coloured row; `mobile`, `tablet`, `phone`, `responsive`, `breakpoint`
- **tool and process words:** `-f` or `COMPOSE_FILE` on the compose line, a
  second compose file, `/var/run/docker.sock` in any container other than
  `devops` — the one service whose responsibility is docker management, and
  which publishes no port (`module_skills/skill_asset_containers.md`); `8900` as the
  page's address in a document, a command or a comment — the host port is measured, the
  page's address the one `make on` prints (`module_skills/skill_asset_containers.md`
  § The topology). `CONTAINER_PORT` is a different fact and may be written as itself: the
  port a server listens on inside its own namespace, and the left-hand side of a
  reader's own forward; `TODO`, `FIXME`,
  `XXX`, `HACK`; test suite, linter, coverage gate, CI, workflow, hook,
  generator, framework; `authority`, `single source of truth`; `one-shot` for a
  one-off — an external API's own parameter spelling is that API's, not ours
  (§ Canonical vocabulary, the external-vocabulary boundary); `cloud-ready`, `AWS-ready`, `cloud-native`; `s3://` in a path
  constant, an adapter for a cloud that is not there; a second compose file, a
  second Makefile, a hand-edited derived artifact

## The default choice

For every new change, prefer **the smallest, most modular and most obvious
implementation that correctly closes the full pipeline.**

**A skill belongs to the module whose responsibility it describes.** A rule
about one module lives in `module_<name>/skills/`; a rule that crosses modules or
governs the project lives in `module_skills/` — the canon; a module's orientation
is its `README_module_<name>.md`. Each is written exactly once, the location
follows ownership, and there is no second copy to drift.
`module_skills/README.md` is the index — it links to every skill, cross-cutting
and module-owned alike, and restates none of them.

`module_skills/skill_asset_containers.md` is the worked example of the cross-cutting
boundary: the one image, the five services — the three runners, `dashboard`
and `devops` — the Makefile fan-out, the ceilings and the store mounts each service is given
are a contract between the infrastructure and all four runtime modules at once, so it belongs
to none of them and stays in the canon.

A **sub-module** is the one boundary in this shape: `sub_module_<domain>/` inside
the module, or the canon, that owns it, with its own `config.py`, its own `main()`
and no part in the chain's dataflow. It exists three times, so it is a convention:
the directory grammar above carries its row, and a fourth is written to it rather
than argued again. The DevOps panel is
`module_monitoring/sub_module_devops/`, nested rather than promoted because the
dashboard serves its own directory — a top-level module would have to be given a
route, and the page reaches the browser as a static file instead; the panel adds
one route for its API alone, because an API is not a file, and the socket it holds
is the reason it is a service of its own rather than a role of `serve.py`. The
scalability crawler is `module_skills/sub_module_scalability_crawler/`, nested in
the canon because it reads files against the canon, and owned by no
runtime module because a hand may list a file of any of them. The coordinate
search terminal is `module_features/sub_module_coordinate_search_terminal/`,
nested in the feature layer because the coordinates a search moves are that
layer's own — the catalogue generates the columns a profile admits — and outside
`module_ml` because it computes nothing and may import neither that module (D02)
nor this one's `config.py`, which imports numpy at its thirteenth line: it runs
on the host's `python3` and gum, and starts every stage through `make`. The two
that draw a terminal share one `tui.py`, twice by extraction, and one skill,
`module_skills/skill_tui_designer.md`, which crosses them and therefore sits in
the canon.

## The shape — what holds the project together

The shape is four modules and a launcher: one image, the stores explicit and
outside compute, the orchestration outside the modules, the contracts between
modules as files, the asset as a parameter, the recorder measuring what a stage
wrote — and nothing of a cloud
(`module_skills/skill_pre_aws_solution.md` § What the shape holds, and what it
does not). The conditions below hold at every commit; a change that breaks one
is wrong.

| # | holds |
|---|---|
| D01 | the root holds no data, feature or ML logic: its only Python is `record.py`, which describes the assembled project, and the canon's only Python is its sub-module, which measures it |
| D02 | `git grep "from module_"` inside a module package finds only that package: no module imports another |
| D03 | a module's skills live under that module and nowhere else; a rule that crosses modules lives in `module_skills/` |
| D04 | a fresh `git clone` followed by `make all` and `make on` is a working project |
| D05 | one `docker-compose.yml` carries the whole topology, and one `Makefile` the stage order and the fan-out |
| D06 | no module writes into another's source tree: what a stage writes lands in a store |
| D07 | an asset is `ASSET` on the make line and `--tickers` at the process boundary — never an image or a service definition of its own |
| D08 | no sub-module is a module: `module_monitoring/sub_module_devops/` is the monitoring module's, `module_skills/sub_module_scalability_crawler/` the canon's, `module_features/sub_module_coordinate_search_terminal/` the feature layer's — each with its own `config.py` and `main()`, none in the chain's dataflow |
| D09 | artifact names and keys move only with the register: every key of every payload has a row in `module_skills/glossary.md`, and a key added, dropped or renamed moves that row in the same commit. The feature layer's contract file `<TICKER>_catalogue.json`, the `catalogue` block in `features_status.json` beside `assets[].row_count_by_timeframe`, the `ticker` key in every row of `data_status.json`, and that snapshot's own measurement set — which `REPORT_dashboard_data_minimalism.md` argues field by field — are each registered there |
| D10 | determinism is unchanged: the caps, the seed, the pinned orders (`module_skills/skill_determinism.md`) |
| D11 | parity: the chain on the frozen raw store reproduces the nine BTC artifacts and the three computational snapshots, normalised, byte for byte against the reference list `README.md` § Parity. The three snapshots are identical under the same raw-store fingerprint; `data_status.json` describes the whole canonical series and moves with every top-up by design, so a reference list carries the fingerprint of the store it was taken on as its first line and a differing fingerprint re-bases that one file and no other. The files a hand drafts — `<TICKER>_coordinate_search_profile.json` and, once promoted, `<TICKER>_feature_set.json` and `<TICKER>_barriers.json` — stand outside it: no stage derives them. So do the coordinate search's two, a hand's stage rather than the chain's: `<TICKER>_coordinate_search.json`, where the search stands at a round boundary, and `<TICKER>_coordinate_search_trials.jsonl`, its ledger of scored states — their proof is that two runs of one profile, and a run interrupted and resumed, give the same bytes in both. A change that reshapes one of the nine re-bases its line and no other — the gate is then a field-level before/after comparison, every kept field byte-identical, beside the lines held fixed |
| D12 | zero cloud mechanisms: nothing in the tree reaches a service off this host but two calls — the venues' public endpoints the two downloaders read, and the command line of a vendor of the crawler, chosen in its TUI, in its user's own login, outside the chain and gating nothing — and `mlflow` writes only into the ledger `trials_sqlite()` builds in `module_ml/config.py` under `STORE_TRIALS_DIR`, a local file `module_ml/hpo.py` addresses as `sqlite:///`, never a network location; the five pins of `requirements.txt` are the project's, and a sixth moves this line in the commit that adds it |
| D13 | `features_status.json` is written by `module_features.status` |
| D14 | every object of `module_skills/glossary.md` § Twice by extraction is marked `# twice by extraction` directly above its own definition — one marker per object, never one above a block of objects — and changed on every side at once |
| D15 | the tracked remnant of the artifacts store — `<TICKER>_README.md`, `<TICKER>_parameters.json`, once drafted `<TICKER>_coordinate_search_profile.json` and, once promoted, `<TICKER>_feature_set.json` and `<TICKER>_barriers.json` — and the four snapshots are tracked, so a fresh clone opens on real numbers and on the profile the last search was run under |
| D16 | the fan-out and the detached search run through `docker compose run --rm`; nothing is `exec`'d into a resident |
| D17 | `skills_status.json` is written by `module_skills.sub_module_scalability_crawler.status` alone, a function of the skill matrix's paths and the reports; the reports by `module_skills.sub_module_scalability_crawler.crawl` alone, and `to_crawl.md` — its entries and its marks — by a hand, in the file or through that module's TUI, its header read off the tree |
| D18 | the crawler gates nothing: no target of the chain, no service and no merge depends on it; it writes only its skill matrix, its reports and its snapshot, and a hand alone runs it |
| D19 | the coordinate search terminal imports the standard library and its own package alone, and starts every stage through `make`: its import lines name no module of this tree but `from . import`, and no third-party package — `module_features/config.py` imports numpy at its thirteenth line and is never imported here — and neither `tmux` nor `docker` appears anywhere in it. It writes the one file `<TICKER>_coordinate_search_profile.json`, a hand alone runs it, one action per run, and it gates nothing |

## Skills absent here, described

Skills the Pre-AWS seats imply and this tree does not hold: each placed by
ownership as § The default choice places every skill, described today where its
last column says, and written when its one condition holds. Two rows this shape
answered are no longer here: the status prefix — the snapshots live in
`store/status/`, the one store tracked whole (`module_skills/glossary.md` § Stores) —
and the image contents — the `Dockerfile` carries the pins and each service
mounts the stores it touches — the `dashboard` those it
reads, read-only
(`module_skills/skill_asset_containers.md` § The topology).

| skill | owner | governs | written when | described today in |
|---|---|---|---|---|
| `skill_task_host_volume.md` | `module_skills/` | the one Linux host every asset's runs share and the volume mounted where the `./store/<content>` mounts are today — every asset's folder and the other `store/<content>/` folders at the same `/store/<content>` paths, and what a task may leave on it | the first run whose `store/<content>/` folders sit on a volume that is not this host's disk | `module_skills/skill_pre_aws_solution.md` § The volume is the home, the store is the copy; `module_skills/skill_asset_containers.md` § The topology |
| `skill_object_storage_layout.md` | `module_skills/` | the prefixes of the copy — `raw/<venue>/<symbol>/<day>` written once, `artifacts/<ticker>/<version>/`, `runs/<run_id>/`, `status/`, `trials/<ticker>/` — and the one discipline: a whole file copied after the last stage of a run has exited, never a path a stage writes | the first whole file copied off the host | `module_skills/skill_pre_aws_solution.md` § The volume is the home, the store is the copy; `module_skills/skill_pre_aws_solution.md` § The asset folder is a prefix, read forward |
| `skill_stage_state_machine.md` | `module_skills/` | one state per stage in the order of `all:`, `data-all:`, `features-all:` and `ml-all:`, a Map over `TICKERS` whose width is `JOBS`, the execution named by `run_id`, the whole-file copy as the state after the last stage, and the schedule that starts it | the first stage launched by something other than `make` | `module_skills/skill_pre_aws_solution.md` § The Makefile is the developer interface; `module_skills/skill_pre_aws_solution.md` § The retrain runtime is a ladder |
| `skill_rebuild_condition.md` | `module_skills/` | the four `has_` / `requires_` predicates — read-only, per asset, in the module that owns what they compare — and the condition state that reads them; never a function that both detects and trains | the first freshness predicate is written, `has_new_market_data(ticker)` in `module_data` | `module_skills/skill_pre_aws_solution.md` § The rebuild condition stays separable; `module_skills/glossary.md` § Pre-AWS direction |
| `skill_artifact_versioning.md` | `module_skills/` | `<version>` = `run_id` under the asset prefix, which version is the active one and how a reader resolves it; no version inside an artifact | the second version of one asset's artifacts exists off the host | `module_skills/skill_pre_aws_solution.md` § Correlatable artifacts, without a version scheme; `module_ml/skills/methodology_ml.md` § 10 |
| `skill_dashboard_front.md` | `module_monitoring/skills/` | the page files and the snapshots as static objects behind a content-delivery front, the run and proxy routes staying a reader process; until then the tunnel of `README.md` § Quickstart | the first reader the tunnel does not serve | `module_skills/skill_pre_aws_solution.md` § The mapping table, the static dashboard and reader rows; `module_skills/skill_pre_aws_solution.md` § What stays as it is, and why, the `module_monitoring/` row |
| `skill_strategy_execution.md` | `module_trading/skills/` | `module_trading/` — a fifth module beside `module_ml`, with its own container, reading the Lean-exact raw tree and the asset artifacts from the copy, its brokerage credentials read once at start from a secrets store | `module_trading/` is created — the first strategy that consumes an artifact | `module_skills/skill_pre_aws_solution.md` § Module boundaries are extraction boundaries; `module_skills/skill_pre_aws_solution.md` § Every object is classified before it is placed, STRATEGY EXECUTION; `module_skills/skill_pre_aws_solution.md` § The mapping table, the two STRATEGY EXECUTION rows |
| `skill_per_asset_status.md` | `module_skills/` | one status object per asset, written by that asset's own status run, and the fold the reader does over them — never a lock, never a basket-wide writer fanned out | a status stage is fanned out for the first time | `module_skills/skill_pre_aws_solution.md` § The resident container is a local mechanism; `module_skills/skill_pre_aws_solution.md` § What stays as it is, and why, the `module_data.status` row |
| `skill_database_promotion.md` | `module_data/skills/` | the threshold past which an asset's embedded file becomes a managed database — a second concurrent writer, or a query across assets | the first writer or query one embedded file cannot serve | `module_data/skills/skill_candle_canonicalisation.md` § 13, § 15; `module_skills/skill_pre_aws_solution.md` § The databases |
