# module_ml — the catalogue and the canonical series in, a research result out

The front door of this module: what it is, where its responsibility stops, and
how to run it. The method itself — every equation, every fold, every citation —
is `skills/methodology_ml.md` and is not repeated here. *The repository shows
the destination, not the road*.

`module_ml` reads one asset's feature catalogue and canonical 1m series and
produces a research result: the feature set the model sees, triple-barrier
labels, a hyper-parameter search, purged walk-forward XGBoost predictions and a
gated strategy simulation, each persisted as a file in that asset's own folder.

## Where the responsibility stops

It begins at the feature layer's contract, `<TICKER>_catalogue.json`, the
catalogue parquets it names, and `ohlcv_1m_canonical` with the aggregate tables the contract names, and asks nothing about where a minute came from or how a
column was computed. Downloading, venue selection, forward fill and provenance
belong to `module_data`; the bars of the register and the catalogue belong to
`module_features`; presentation of the results belongs to `module_monitoring`.
Every stage here opens the asset's database read-only.

Every stage here is a one-off process addressed as
`python -m module_ml.<stage> --tickers <TICKER>` (under `make` or compose, which set the three `STORE_*_DIR` this module reads — the artifacts store, the status store and the trials store): it reads files, writes files
and holds nothing between runs, so the four stages of `ml-all` above `status`,
and the coordinate search and the promotion outside the chain, already have
the shape of asset-scoped compute that receives a finished catalogue and leaves
artifacts in the asset's folder, while `status` is the basket-wide fold over
them. The
direction: `module_skills/skill_pre_aws_solution.md`.

`ANNUALISATION_PERIOD_15M_BARS` in `config.py` is the one timeframe fact this module
does not read through the contract: it is bound to the decision timeframe being `15m`,
and moving the decision timeframe means moving it in the same commit.

## Stages

Run in order; `make ml-all` runs them, each stage in a one-off container of the
`ml` runner, and a single stage is its own `ml-<stage>` target in the same
runner, or the one-off process above run by hand in a shell that exports those
variables (`module_skills/glossary.md` § Stores). The four stages above `status`
fan out one process per asset with its threads pinned to one; `status` runs once
and aggregates the assets the launcher names — the whole basket.

| stage | target | writes |
|---|---|---|
| labels | `make ml-labels` | the triple-barrier label events parquet |
| hyper-parameter search | `make ml-hpo` | `<TICKER>_parameters.json` |
| training | `make ml-train` | `<TICKER>_model_evaluation.json`, the out-of-sample predictions parquet |
| strategy | `make ml-strategy` | `<TICKER>_strategy_evaluation.json` |
| status | `make ml-status` | `store/status/ml_status.json`, `<TICKER>_README.md` |
| coordinate search — outside the chain, by a hand | `make ml-coordinate-search`, one process per asset of the basket, `ASSET=<TICKER>` narrowing it to one — detached on the host through the Makefile's `tmux-` twin `tmux-ml-coordinate-search`, which requires `ASSET`, or in the foreground; `make ml-status` after it | `<TICKER>_coordinate_search.json` and its ledger `<TICKER>_coordinate_search_trials.jsonl`; the studies of its `hpo` loop in the trial ledger |
| promotion — outside the chain, by a hand, one asset at a time | `make ml-coordinate-search-promote ASSET=<TICKER> PROPOSAL=<n>` | `<TICKER>_feature_set.json` and `<TICKER>_barriers.json`, then the chain's files anew |

Every stage runs in a one-off container of the `ml` runner: a fanned-out
per-asset stage one container per asset; `status`, and the promotion — a hand's
one-off for one asset — once. Each stage takes `--tickers`; `status` takes it
too and folds the assets it was told — the launcher passes the whole basket, and
every complete asset among them gets its `<TICKER>_README.md`.

## What it writes

```
store/assets_artifacts/<TICKER>/
store/status/ml_status.json            the status snapshot the dashboard reads
store/trials/<TICKER>/<TICKER>_hyperparameter_search_trials.jsonl   the trial ledger, written by hpo.py alone
```

One folder per asset, one file per artifact responsibility; the manifest and
what each file holds are in `module_skills/glossary.md` § Artifacts.
`<TICKER>_README.md`, `<TICKER>_parameters.json`, once a hand has drafted one
`<TICKER>_coordinate_search_profile.json`, once a search has run
`<TICKER>_coordinate_search.json` and `<TICKER>_coordinate_search_trials.jsonl`,
and, once a hand has promoted one, `<TICKER>_feature_set.json` and
`<TICKER>_barriers.json` are tracked so a folder reads — and rebuilds — without a
run; the parameters are tuned for the state, so they travel together, and
`ml_status.json` and the README read the search's two. The README, the parameters
and the search's state are derived and never hand-edited — the ledger only ever
appended to by the search; the profile, the feature set and the barriers are a
hand's decisions, drafted and never derived (`AGENTS.md` § Canonical vocabulary).

## Extending

| what you add | where, and how much | what it changes | the gate |
|---|---|---|---|
| a coordinate of the search | one line per family in `ROUND_SCHEDULE` (`config.py`), one module beside `barrier_search.py` with a `moves()` that answers which moves are legal from a state and what a child of each must build again — `backtest`, `fits` or `labels` — one entry in `LOOP_MODULES` (`coordinate_search.py`), and its grid in the profile | nothing of the state's format, the gate, the ranking, the beam, the resume, the proposals or the terminal: a trial already carries the whole of Θ, and every one of those reads the row rather than the coordinate | a profile that names the new loop searches it; a profile that does not is byte-identical to a run without it; `coordinate_search.py` still names no coordinate of its own |
| a hyper-parameter | one entry in `HYPERPARAMETER_SEARCH_SPACE` (`config.py`), in xgboost's own spelling | the search space, `best_params` and every artifact downstream of a retune | `ml-labels` and the feature parquets byte-identical; the register's `best_params` row lists the space |

## Design rationale

Why each object of this module sits where it does — the answers of
`module_skills/skill_self_explaining_naming.md` § The naming review written
down, one row per object, analogous pair or the module's documents; the mapping
row it answers to is `module_skills/skill_pre_aws_solution.md` § The mapping
table, cited by its *responsibility* column and never repeated.

| object | why here | why beside these | why this boundary | answers to |
|---|---|---|---|---|
| `config.py` | The frozen experiment of the research layer — the fold bounds, the label, search and strategy parameters — and one descriptor per artifact file of this module — the ones on the decision grid taking the feature layer's contract, `cat`, as an argument and doing no I/O — carrying its own copies of the units, the DuckDB ceiling, the two store reads and their descriptors, `to_utc_ms()`, the `--tickers` parser and `rounded()` — twice by extraction, each copy as its row in `module_skills/glossary.md` § Twice by extraction says; it imports nothing of another module: the register, the grid and the warm-up arrive per asset as `<TICKER>_catalogue.json`. | Every stage of the module imports it, nothing else names an artifact path of this module, and `is_artifact_set_complete()` is what `status.py` asks before it folds an asset. | A stage reaches an artifact by descriptor (`module_skills/skill_pre_aws_solution.md` § Correlatable artifacts, without a version scheme), so the asset folder keeps the same path under `/store` on whatever disk is mounted there. | STORAGE — research artifacts |
| `dataset.py` | The shared IO of the layer — `load_catalogue()`, the one read of the feature layer's contract per stage, `load_xy()` with `load_feature_columns()` and `build_x()`, `write_json()` and `load_json()` — the canonical JSON writer and the parquet writer of this module, both twice by extraction, identical in `module_features/dataset.py` (its docstring). | `labels.py`, `hpo.py`, `train.py`, `strategy.py`, `coordinate_search.py`, `coordinate_search_promote.py` and `status.py` import it, and it imports `config.py` alone. | It writes to the descriptor it is handed and builds no path of its own, so an artifact lands where `config.py` says on whatever disk is mounted at `/store`. | STORAGE — research artifacts |
| `labels.py` | LABEL — Y: the triple-barrier events on the canonical 1m path, per asset (its docstring; `skills/methodology_ml.md` § 5). | It imports `config.py` and `dataset.py`, carries its own copies of `wilder_smoothing()`, `atr()` and `asof_index()` (twice by extraction, identical in `module_features/indicators.py` — the label defines its own barrier scale), reads the canonical tables read-only and never the catalogue parquets, and writes the events parquet `load_xy()` joins to X by position. | X and Y are built by two stages and joined by position at the read, in `load_xy()`, so the join happens at the same descriptor paths whatever disk holds them. | COMPUTE — one stage for one asset |
| `model.py` | The xgboost boundary (`AGENTS.md` § Canonical vocabulary): the class mapping, the search space, fit, predict and the two importances the booster gives — total gain and the SHAP contributions — as pure functions over numpy arrays (its docstring). | `hpo.py` and `train.py`, the two stages that fit, and `coordinate_search.py`, which fits through `train.fold_evaluation()` and maps the classes with `to_class()`, import it; it imports `config.py` alone. | It reads nothing and writes nothing — `train.py` persists the numbers and not the model — so the same fit under `nthread=1` and a fixed seed runs in whichever container the stage takes (`module_skills/skill_determinism.md`). | COMPUTE — one stage for one asset |
| `validation.py` | The fold contract — warm-up, train, purge, out-of-sample, final holdout — and the metrics, pure numpy (its docstring; `skills/methodology_ml.md` § 6, § 8). | `hpo.py`, `train.py` and `strategy.py` import it, and a population and its weights leave it together (its docstring). | Its folds are fixed bounds from `config.py` and its arithmetic touches no file, so the same folds gate the same numbers in whichever container runs the stage. | COMPUTE — one stage for one asset |
| `hpo.py` | The hyper-parameter search: one sequential, seeded study per asset over the frozen space, its objective the CAGR of the validation path — the quantity the coordinate search selects on — and, inside a coordinate search, one candidate per beam member — the best admissible point of a study run on that member's own X and Y — under one gate, the thresholds at which every fold so far clears the trade floor and beats the champion's Calmar, read off one sweep of the threshold grid per fold (its docstring; `skills/methodology_ml.md` § 7). | It imports `config.py`, `dataset.py`, `model.py`, `strategy.py`, `train.py` and `validation.py` — the fit, the predictions and the threshold sweep are the stages' own functions — reads X and Y through `load_xy()` and writes `<TICKER>_parameters.json`, the one file `train.py` takes from it, and leaves every point the study drew in the asset's trial ledger through `log_trials()` — this module's one ledger boundary — `dataset.append_jsonl` and nothing else — written by `ml-hpo` and by the search's `hpo` loop. | It fans out `JOBS` at a time with threads pinned to one (§ Stages) and writes at `parameters_json()`, a tracked file with no timestamp (§ What it writes) — the same path on any host, the same bytes being the claim of `module_skills/skill_determinism.md`. | COMPUTE — one stage for one asset |
| `train.py` | Out-of-fold predictions per validation fold with the two importances of that fold's booster — gain and mean absolute SHAP — and the final-holdout report, under the frozen parameters `hpo.py` chose (its docstring; `skills/methodology_ml.md` § 8). | It imports `config.py`, `dataset.py`, `model.py` and `validation.py`, reads `<TICKER>_parameters.json` and writes the evaluation JSON and the predictions parquet `strategy.py` reads. | The numbers are persisted and the model is not (its docstring), so nothing of a run outlives its two files at `oos_predictions_parquet()` and `model_evaluation_json()` — the same paths on any disk mounted at `/store/assets_artifacts`. | COMPUTE — one stage for one asset |
| `strategy.py` | STRATEGY — the research evaluation of the predictions on the canonical path, with explicit costs (`skills/methodology_ml.md` § 9), and it opens no connection to a venue; its threshold selection is one function the stage and the coordinate search both run. | The last stage of `ml-all` before `status`, importing `config.py`, `dataset.py`, `labels.py` and `validation.py` and reading the predictions `train.py` wrote, and the trend definition on every timeframe from the catalogue columns `load_xy()` carries. | It writes `<TICKER>_strategy_evaluation.json` and trades nothing — the host that would is `module_skills/skill_pre_aws_solution.md` § Module boundaries are extraction boundaries — so its one output keeps the path `strategy_evaluation_json()` builds. | COMPUTE — one stage for one asset |
| `barrier_search.py` | The barrier coordinate: the geometry of an event moved one grid point at a time, in two families — the trade's own exit, whose children reuse their parent's fits and predictions, then the label's geometry, whose children are Y written again (its docstring; `skills/methodology_ml.md` § 4, § 9). | It imports `config.py` alone: it scores nothing and names no file. | It answers which moves are legal from one state and what a child of each must build again; `coordinate_search.py` decides which are kept. | COMPUTE — one stage for one asset |
| `coordinate_search.py` | The coordinate search: a beam over the coordinates of a state on the validation folds, under the profile a hand drafted and the frozen parameters, a move kept only where every fold agrees; the strategy's numbers reported beside every trial. It keeps what it knows in two files, because they are two responsibilities that grow differently: `<TICKER>_coordinate_search_trials.jsonl`, the ledger, gains one line per scored state and is never rewritten; `<TICKER>_coordinate_search.json`, where the search stands at a round boundary, is a fixed handful of keys written at the top of each round and nowhere else, so it exists before the ledger's first line — and its path and proposals name their trials by index and copy none of their numbers (its docstring; `skills/methodology_ml.md` § 4). A state file of an older shape is not migrated: where it lacks a key the code reads, the search fails on that key, and a hand deletes both files so the search writes new ones. | It imports `config.py`, `dataset.py`, `labels.py`, `model.py`, `strategy.py` and `train.py` — the labels, the fit, the predictions and the selection are the stages' own functions, called as a library — one module per coordinate, `barrier_search.py`, `feature_set_search.py` and `hpo.py`, and writes the two files `status.py` reads as `coordinate_search`. | It runs one asset per process, resumes by comparing its recorded inputs with the run's by equality, and writes `coordinate_search_json()` once a round, at its top — the same path and the same bytes on any host, whether in the `ml` runner's container or detached on the host through the Makefile. | COMPUTE — one stage for one asset |
| `coordinate_search_promote.py` | The promotion: a hand's choice copied into the asset's own state — the proposal's columns into `<TICKER>_feature_set.json` and its barrier geometry into `<TICKER>_barriers.json`, and nothing else, the commit history the record of every promotion — and nothing computed (its docstring; `skills/methodology_ml.md` § 4). | It imports `config.py`, `dataset.py` and `feature_set_search.py` — the column differences are the search's own algebra, called as a library — reads the proposal's trial index from the coordinate search result and that trial's line from its ledger, and writes the two files `load_feature_columns()` and `load_barriers()` read before every fit. | It takes `--tickers` and `--proposal` and is never fanned out — one asset per hand, a one-off of the `ml` runner in the shape of `status` — and `ml-coordinate-search-promote` reruns `ml-all` for that asset on its next recipe line, so the promoted set is re-tuned at the same paths on any host. | COMPUTE — one stage, one one-off process |
| `feature_set_search.py` | The feature-set coordinate: the algebra of a set of columns and the two families a pass expands one by — a column of the catalogue in, a column of the set out (its docstring; `skills/methodology_ml.md` § 4). | It imports `config.py` alone, beside `barrier_search.py`, which answers the same two questions for the geometry. | It scores nothing and runs nothing: it has no `main()`, and the promotion borrows its column algebra. | COMPUTE — one stage for one asset |
| `status.py` | The stage that measures this module's own artifacts — the basket snapshot and each asset's README, assembled from the three result files and computing nothing of their own (its docstring) — placed by `AGENTS.md` § Architecture shape. | It imports `config.py`, `dataset.py`, `hpo.py` and `strategy.py` for the keys they publish under, `coordinate_search.py`, whose `build_search_inputs()` is the one definition of what a search is conditioned on, and `feature_set_search.py`, whose column differences say what a proposal moves; it reads what `hpo.py`, `train.py`, `strategy.py`, `coordinate_search.py` and `coordinate_search_promote.py` wrote — a proposal joined to its line of the search's ledger by `trial_index` — and writes `store/status/ml_status.json` for `ml.js` to fetch and `<TICKER>_README.md` into the asset's folder. | It runs once in a one-off container of the `ml` runner and folds the tickers `--tickers` names — the launcher passes the whole basket (§ Stages; `module_skills/skill_pre_aws_solution.md` § The resident container is a local mechanism), the snapshot at the one path `ML_STATUS_JSON_PATH` builds, under the `STORE_STATUS_DIR` the launcher names. | COMPUTE — one stage, one one-off process |
| `__init__.py` | The package that makes `python -m module_ml.<stage>` a command (§ Stages), its docstring the module's responsibility in one line. | It names the feature set, the labels, the walk-forward, the model, the strategy simulation and the two reports, and imports nothing. | The same `python -m module_ml.<stage> --tickers <TICKER>` runs in a one-off container of the `ml` runner (§ Stages) — the launcher setting the three `STORE_*_DIR` this module reads — the command `docker compose run --rm -T ml` carries unchanged whichever host starts it. | COMPUTE — one stage, one one-off process |
| `sub_module_terminal/` | The module's own terminal: each asset's artifacts and the search recorded for it, then one action — a stage of the chain, or the coordinate search's draft, search, recorded search and promotion — started through `make` (`sub_module_terminal/skill_ml_terminal.md` § Design rationale, row by row). | It imports `config.py` for every descriptor it reads, the search's frozen geometry and the loops of a round, and carries the readers and the writer `dataset.py` cannot lend a host without duckdb and numpy — `load_json()`, `load_jsonl()`, `write_json()`, twice by extraction — beside its own `tui.py`, one file with every other terminal's. | It computes nothing and writes one file, `<TICKER>_coordinate_search_profile.json`, a hand's decision; every stage it names runs through `make`, so the terminal stays on the host's `python3` and gum while the stages keep their one-off container of the `ml` runner. | no row — the hand's instrument over the module's targets, seated beside its module (`AGENTS.md` § Canonical vocabulary, the sub-module row) |
| the module's documents — `README_module_ml.md` and `skills/` | This orientation and the normative documents of `skills/`, filed by ownership (`AGENTS.md` § The default choice). | The orientation points at the documents beside it (§ Its normative skills), and every rule about this module sits in `skills/` (`AGENTS.md` § Canonical vocabulary, the row *a module's own skills*). | Tracked files under `module_ml/` that no stage and no route reads, travelling with the code beside them — the same paths beside the code wherever the code is. | no row — a document that travels with the task's code, seated beside its module |

## Its sub-module

`sub_module_terminal/` is the hand's instrument over this module: it shows, per asset, which
artifacts of the chain stand and where the coordinate search recorded for it stands, then starts
one action through `make` — a stage of the chain, or the search's own: draft the asset's search
profile, start the search (detached in a tmux session, or in the foreground), read the recorded
search, promote one of its proposals. It reads the feature layer's contract, the search's state and
its ledger, and the profile, and looks whether the labels, the parameters, the model evaluation and
the strategy evaluation are there; it reads no snapshot. It computes nothing: it runs on the host's
`python3` and gum, imports the standard library and its own package alone — `config.py` of this
module among them, which is standard library — and writes one file,
`<TICKER>_coordinate_search_profile.json`, in the store. Its orientation is
`sub_module_terminal/README_sub_module_terminal.md`, its rules the skill beside it,
`sub_module_terminal/skill_ml_terminal.md`, and the standards of its screens
`module_skills/skill_tui_designer.md`.

## Its normative skills

| document | answers |
|---|---|
| `skills/methodology_ml.md` | the research layer equation by equation, with its citations |

Project-wide rules are in `module_skills/`, the read-only copy of the canon at this
repository's root, indexed by `module_skills/README.md`; the market object it
reads is defined by
`module_data/skills/skill_candle_canonicalisation.md`,
the catalogue it takes X from by
`module_features/skills/skill_feature_taxonomy.md`.
