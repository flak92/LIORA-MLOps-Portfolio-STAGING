# LIORA — 1m Crypto Research Pipeline

**Deterministic multi-venue OHLCV research pipeline with purged walk-forward
validation, a frozen final out-of-sample holdout, and a static results dashboard
— one `make all`.**

*The repository shows the destination, not the road*.

Public market observations → QuantConnect Lean-compatible raw data → one
deterministic canonical DuckDB per asset → the feature catalogue and labels →
purged walk-forward XGBoost → research strategy simulation → monitoring.

The four modules of the chain sit at the root beside what none of them owns: the
Makefile and the compose file that run them, the recorder, the five stores, one folder each under `store/`, and
the canon of rules that cross them, with the one sub-module that reads each listed file against the skills a hand marks for it. The governing contract — minimalism, minimum requirements,
KISS/YAGNI/DRY/SOLID, UCAS, pipeline-first, and what holds the project
together — is [AGENTS.md](AGENTS.md). Each module carries its own rules in its
`skills/` and its front door in `README_module_<name>.md`; the naming register
and the rules that cross modules are in [module_skills/](module_skills/), indexed
by [module_skills/README.md](module_skills/README.md). The working path through
the project is `AGENTS.md → module names → README_module_<name>.md → the
module's own skills → code`; this README is the general overview.

## Quickstart

```bash
git clone https://github.com/flak92/LIORA-MLOps-Portfolio.git
cd LIORA-MLOps-Portfolio
make all                   # the whole chain from a fresh clone, every stage in a one-off container: build -> data-all -> features-all -> ml-all
make on                    # build the image if needed, start the dashboard and the DevOps panel, print the page's address and open it
make off                   # stop and remove every container of this project
make help                  # every target with its one-line purpose
```

`git`, `docker`, `make` and Python 3 — standard library only, for `record.py`,
`make skills-crawl`, `make skills-status` and the opener `make on` prints through — are the whole requirement of the host;
`tmux` joins them for the detached search, and gum 2 for the crawler's text-based user interface (TUI) beside at least one command line
of `module_skills/sub_module_scalability_crawler/vendors_for_crawling.toml`, installed and logged in, for the crawler's agent.
Everything runs through the Makefile. `on` and `off` are the presentation switch,
the one switch pair the target grammar admits ([AGENTS.md](AGENTS.md) § Canonical
vocabulary): two words for a presenter to remember.

The chain, and the record it leaves:

```bash
make all-record            # the same chain, every stage measured from outside by record.py into store/run_records/<run_id>/ — the Lifecycle tab
```

The coordinate search, outside the chain, one asset at a time:

```bash
make tmux-ml-coordinate-search ASSET=BTC   # the search detached in tmux session coordinate-search-btc; it outlives the terminal and ends with the search, resumes if rerun
tmux attach -t coordinate-search-btc        # watch it; Ctrl-C stops it
make ml-status                              # the finished search's proposals into the snapshot — the page reads nothing else
```

Its proposals are the *Feature set* view and the PROPOSALS frame of *ML
Assets*; a hand promotes one — one asset at a time — and the chain reruns:

```bash
make ml-coordinate-search-promote ASSET=BTC PROPOSAL=1   # copy proposal 1 into BTC_feature_set.json and BTC_barriers.json, then ml-all for BTC
```

The canon's crawler, outside the chain, by hand in a terminal (`module_skills/skill_scalability_crawler.md`):

```bash
make skills-crawl     # the TUI in gum: the listed paths and the skill matrix, then one action — crawl (vendor, model, effort, permissions, files, then the plan — each first option, every file and crawl preselected), add a path (its skills chosen, previewed), mark skills (the changes shown) or remove a path (confirmed) — then it closes; Esc writes nothing
make skills-status    # the snapshot of the listed files' reports, without the TUI — the Scalability tab reads it
```

Its skill matrix, vendors and mission are `to_crawl.md`, `vendors_for_crawling.toml` and `crawlers_mission.md` in
`module_skills/sub_module_scalability_crawler/`, each kept by hand — a row per path, an `X` under each skill it is read against; a vendor is one table whose forms are data, its CLI installed and logged in.

`tmux` is a tool of the host beside `docker` and `git`, never of an image.

Two personas, two doors, both behind `make on`:

- **business** — the status page at `http://127.0.0.1:<port>/`, the address
  `make on` prints: *Pipeline*, *Data
  Quality*, *ML Research*, *ML Assets*, *Scalability* and *Lifecycle* — the results,
  the tree counted against its contract and the cost of producing them (§ Dashboard below);
- **DevOps** — the **DevOps** control opens the panel: every container on the host with its ports, the
  networks, volumes, bind mounts, the image and the engine's events, with
  start / stop / restart offered for this project's own containers alone.

A single stage runs by name in a one-off container of its module's runner — `make features-catalogue`
is `docker compose run --rm -T features python -m module_features.catalogue --tickers <TICKER>`, one container per asset of the
basket — and `data-all`, `features-all`, `ml-all` and `all` are the chains. The stage order is the
Makefile's `all:`, `data-all:`, `features-all:` and `ml-all:`; every document points there. The host port is measured
at invocation — the port the dashboard already publishes, else the first free port from 8900 upward
(`module_skills/skill_asset_containers.md` § The topology) — and `PORT=8902 make on` overrides
it; `JOBS=2 make ml-hpo` sets the fan-out width, and every stage is idempotent in what it
derives, so a rerun fetches and rebuilds only what its contract says — the trial
ledger alone grows, one search more per `ml-hpo`, and beside the chain the crawler's reports
grow one entry per file crawled. The dashboard is
docker-only and reachable on loopback alone; on a remote machine tunnel with
`ssh -L 8900:127.0.0.1:<port> <host>`, `<port>` the one `make on` printed there.
Four direct dependencies across
the four modules and nothing else — `duckdb` (storage and query: data, features, ml),
`numpy` (mathematics: features, ml), `optuna` (hyper-parameter search: ml) and `xgboost-cpu`
(model: ml); `module_monitoring` is standard library only. The CPU wheel is deliberate, because the research layer trains with `tree_method=hist` and `nthread=1`.

```
                 ┌── market source A ──┐
MARKET DATA ─────┤                     ├──► NORMALISED RAW 1m OHLCV  (Lean ZIPs)
                 └── market source B ──┘              │
                                                      ▼
                                          ONE DuckDB PER ASSET
                                       (primary-failover, full grid)
                                                      │
                                    ┌─────────────────┼─────────────────┐
                                    ▼                 ▼                 ▼
                                   15m                1h                4h
                                    └─────────────────┬─────────────────┘
                                                      ▼
                                                  FEATURES X
                                                      │
                   canonical 1m ───────────────────── ┼──► TRIPLE BARRIER Y
                                                      ▼
                                            PURGED WALK-FORWARD
                                                      ▼
                                                   XGBOOST
                                                      ▼
                                                PROBABILITIES
                                                      ▼
                                               STRATEGY RULES
                                                      ▼
                                            RESEARCH PnL / EQUITY
                                                      ▼
                                                  MONITORING
```

Providers deliver observations; the canonical database defines the research
object. Everything below it describes the method, not the data provider.

## The stores

| store | variable | in a container | tracked |
|---|---|---|---|
| `store/raw_1m/` | `STORE_RAW_1M_DIR` | `/store/raw_1m` | no — the Lean-exact raw ZIPs, one per venue, symbol and UTC day |
| `store/assets_artifacts/` | `STORE_ASSETS_ARTIFACTS_DIR` | `/store/assets_artifacts` | the remnant only: `<TICKER>_README.md`, `<TICKER>_parameters.json`, `<TICKER>_coordinate_search_profile.json` once drafted, the coordinate search's own two files — `<TICKER>_coordinate_search.json` and its ledger `<TICKER>_coordinate_search_trials.jsonl` — once a search has run, and `<TICKER>_feature_set.json` and `<TICKER>_barriers.json` once promoted |
| `store/run_records/` | `STORE_RUN_RECORDS_DIR` | `/store/run_records` | no |
| `store/trials/` | `STORE_TRIALS_DIR` | `/store/trials` | no — `<TICKER>_hyperparameter_search_trials.jsonl`, one JSON object a line, appended and never rewritten: every point every study drew, the stage's and the coordinate search's alike, a rerun appending a study of its own; `module_ml/hpo.py` alone writes it, the `ml` runner the one service that mounts it, and a hand clears it. It carries no run id, no timestamp and no host name, so two studies over an empty store leave the same bytes. **One writer per asset at a time**: a study's place in the file is read off the file before its lines are appended, so `ml-hpo` and a search of the same asset run one after the other, never together. It is one of two ledgers — one technique, `dataset.append_jsonl`, and two lifecycles: the coordinate search's ledger lies beside its state in the asset's folder, is tracked, and is deleted when the search starts another experiment; this one lies here, is not tracked, and only grows until a hand clears it — a round a resumed search replays runs its studies again, and they are lines again |
| `store/status/` | `STORE_STATUS_DIR` | `/store/status` | yes — the four snapshots, so a fresh clone opens on real numbers |

The store is the boundary between compute and state (`module_skills/glossary.md`
§ Stores). Every stage reads and writes only these five and learns where they
are from its environment — the Makefile exports the host paths, the compose file
sets the container paths — and no module writes into another's tree. The image
carries the pins and nothing else; the code and the state arrive as mounts, and
a container addresses a store only at `/store/<content>`.

## The chain

`data-all → features-all → ml-all`, each `<module>-<stage>` a one-off container of
its module's runner, `docker compose run --rm -T <runner> python -m <module>.<stage> --tickers <TICKER>`
— the `fanout` macro once per asset of `TICKERS`, `JOBS` wide, the `basket` macro
once for the whole basket (the three status stages and the download). `ASSET=<TICKER>`
on the make line narrows every per-asset stage to one asset and never a
basket-wide one; `make all-record` wraps every stage of `RECORDED_STAGES` in
`record.py`, which lists the four pipeline stores — every store but
`store/trials/`, a search's own account of itself — before and after and writes
`store/run_records/<run_id>/<stage>.json`. The residents are `liora-dashboard-1` and
`liora-devops-1`: the compose project is named
`liora` in the file, so two checkouts of the project on one host share the name —
run one at a time, or set `COMPOSE_PROJECT_NAME`.

| Stage     | Command                | Input → Output                                              | Property                          |
|-----------|------------------------|-------------------------------------------------------------|-----------------------------------|
| download  | `make data-download`   | both APIs → `store/raw_1m/.../*_trade.zip`        | idempotent; one file per UTC calendar day; post-listing days complete; one process per venue for the whole basket |
| ingest    | `make data-ingest`     | ZIPs → raw tables → `ohlcv_1m_canonical` (failover)         | idempotent; deterministic rebuild, one asset at a time |
| status    | `make data-status`     | DuckDB → stdout + `store/status/data_status.json`           | read-only; per asset, five scans of its one database, the venue scan run once per venue |
| catalogue | `make features-catalogue` | the bars → one feature parquet per timeframe and `<TICKER>_catalogue.json`, the contract the ML layer reads | deterministic; the existing columns byte-identical after an extension |
| features status | `make features-status` | the parquets → `store/status/features_status.json` | read-only; the catalogue's facts and each asset's row counts |
| coordinate search | `make ml-coordinate-search` | the profile a hand drafted, the catalogue parquets, Y and the frozen parameters → `<TICKER>_coordinate_search.json` and its ledger `<TICKER>_coordinate_search_trials.jsonl` | a beam over the coordinates of a state, on the validation folds only, a move kept only where every fold agrees; resumes; promotes nothing; `make ml-status` after it puts the proposals on the page; its detached twin `make tmux-ml-coordinate-search ASSET=<TICKER>` outlives the terminal and ends with the search |
| promotion | `make ml-coordinate-search-promote ASSET=<TICKER> PROPOSAL=<n>` | one proposal's columns → `<TICKER>_feature_set.json` and its barrier geometry → `<TICKER>_barriers.json`, then `ml-all` for that asset | a hand's choice, one asset at a time; the same proposal twice changes nothing; the commit history is the record |
| lifecycle | `make all-record` | one recorded run of the whole chain → `store/run_records/<run_id>/` | one record for the whole basket; every stage measured from outside by `record.py` — its time, its exit code and what it wrote to the four pipeline stores |
| dashboard | `make on`              | snapshots → six-tab page on `127.0.0.1:<port>`, the address `make on` prints, plus the DevOps panel behind its jump, served by `module_monitoring/serve.py` in the `dashboard` container with the run, snapshot and `/devops` routes | no external resources |

## Extending

| to add | change | where |
|---|---|---|
| an asset | one ticker in `TICKERS`; every stage is told its assets by `--tickers` | this repository; nothing changes in any module |
| a stage of a module | the stage in its module and one `<module>-<stage>` target here — a `fanout` or a `basket` line — and, if a run should record it, its name in `RECORDED_STAGES` | `module_<domain>/`, then here |
| a timeframe | one token in `HIERARCHY_TIMEFRAMES` of `module_features/config.py`, carried to ML by `<TICKER>_catalogue.json` — a different experiment | `module_features/` |
| a feature | one record of `FEATURE_CATALOGUE` in the same file (`module_features/README_module_features.md` § Extending) | `module_features/` |
| a coordinate of the search | one line per family in `ROUND_SCHEDULE`, one module beside `barrier_search.py` answering which moves are legal and what a child must build again, one entry in `LOOP_MODULES`, and its grid in the profile — the state's format, the gate, the ranking, the beam and the terminal are untouched (`module_ml/README_module_ml.md` § Extending) | `module_ml/` |
| a venue | `download_<venue>.py` beside its sibling and the failover order in `ingest.py` (`module_data/README_module_data.md`) | `module_data/` |
| a module | a package `module_<domain>/` with a runner service on the one image | `module_<domain>/` beside the others, then here |

## Working in a module

A module is a directory: its package, its orientation `README_module_<name>.md`
and its own `skills/`. Edit it in place and run the stage it owns — nothing has
to be built first, because the code is mounted into the container it runs in:

```bash
make ml-all ASSET=BTC        # one module's chain, one asset
make data-status             # a single stage, basket-wide
make help                    # every target with its one-line purpose
```

`git grep "from module_"` inside a package finds only that package: no module
imports another, and what would cross the boundary as an import crosses it as a
file in a store instead (`AGENTS.md` § Architecture shape).

## Skills

`AGENTS.md` and `module_skills/` are the canon: the contract, the naming register
and the rules that cross modules, and the one sub-module that reads each listed file
against the skills a hand marks for it — `make skills-crawl` opens the crawler's TUI, where a hand chooses one action — crawl, which sends the files it chooses from the skill matrix to an agent after the plan, each with the skills its row marks, and appends each answer to that file's report; add a path with its skills; mark a path's skills; or remove a path — and
`make skills-status` dates the reports in `store/status/skills_status.json`; it gates nothing (`module_skills/skill_scalability_crawler.md`). How any of this tree's terminals draws a screen is the canon's too,
`module_skills/skill_tui_designer.md`, because two sub-modules now draw one: the crawler and
`make features-coordinate-search-terminal`, the feature layer's instrument over the coordinate search. A module's own rules live under that module, in
`module_<domain>/skills/`, and the index `module_skills/README.md` links to all of
them. Each rule is written exactly once, where it is owned, and no document
restates another (`AGENTS.md` § The default choice).

## Parity

Every number here is reproducible. The proof, repeatable on any host:

1. a fresh `git clone` of this repository, and a frozen copy
   of the raw store hardlinked into `store/raw_1m/` — the downloaders never
   overwrite an existing ZIP — fingerprinted **before** the chain runs, so the
   fingerprint names the store the hashes came out of:
   `find store/raw_1m -name '*.zip' -printf '%P %s\n' | sort | md5sum`;
2. `make build data-ingest data-status features-all ml-all` — the chain without
   `data-download`, whose window ends at today's UTC midnight and would move the
   data snapshot; the download is run separately, its gate an exit code of 0;
3. the nine BTC artifacts — three feature parquets, the label events, the
   parameters, the out-of-fold predictions, the model and strategy evaluations,
   the asset README — byte-identical to the reference list;
   `BTC_catalogue.json`, the one new file, identical between two runs;
4. the three computational snapshots identical after dropping the `generated_at_utc` line —
   `grep -v '^ "generated_at_utc":'`, anchored because it is one top-level key on its own
   line and not a substring to be hunted — under the
   same fingerprint. `data_status.json` carries no `window_end`: it describes the
   whole canonical series, including the minutes past `RESEARCH_END_UTC`, and moves
   with every top-up by design. A differing fingerprint re-bases that one file and
   leaves the other twelve hashes standing.

The files a hand drafts stand outside this proof — `<TICKER>_coordinate_search_profile.json` and, once
promoted, `<TICKER>_feature_set.json` and `<TICKER>_barriers.json`: no stage derives them, and the one
program that writes each writes the same bytes for the same decisions. The coordinate search's own two files are outside it too, being a hand's stage rather than the chain's:
`<TICKER>_coordinate_search.json`, where the search stands at a round boundary, and
`<TICKER>_coordinate_search_trials.jsonl`, its ledger of scored states — one a line, appended and never
rewritten. Their proof is that two runs of one profile, and a run interrupted and resumed, give the same
bytes in both. `<TICKER>_README.md` lists every file of a hand's stage and measures none — listed, not
measured, because its size moves with the hand and not with the chain — so a search leaves the README's bytes
where the chain put them. Both are tracked even so: `ml_status.json` and `<TICKER>_README.md` are inside the proof and
read them, so a clone without them could not reproduce the two files that quote them.

Both sides run in containers from the same pins; `SEED`, `nthread=1`,
`OMP_NUM_THREADS=1`, sequential Optuna and DuckDB's pinned orders are what make
the bytes equal (`module_skills/skill_determinism.md`). The comparison script and
the reference md5 lists live outside this repository.

## One canonical series from two venues

Every market feed has missing minutes. Per minute the highest-priority valid
candle is copied verbatim — traded Binance, traded Bybit, a valid no-trade
candle from either in the same order — and only a minute with no valid candle
on both venues is a canonical gap, forward-filled with the previous close and
zero volume. Downstream code reads one continuous `t,O,H,L,C,V` series whose
every printed price existed on a real market. The rule, the provenance and the
schema:
`module_data/skills/skill_candle_canonicalisation.md`;
the endpoints:
`module_data/skills/methodology_data.md`.

## The basket

One uniform market — USDT-margined perpetual futures. The active basket is a
single asset, `BTC`: one reference asset carries the whole path end to end, and the
basket grows by extending `TICKERS` in the `Makefile` — every stage is told its assets by
`--tickers`, and no module changes.

The window starts at **2021-01-01 00:00 UTC** and ends at the most recent UTC
midnight. Every asset is listed on Binance USDS-M before the window start;
where a Bybit listing falls inside the window, the pre-listing minutes are
Binance-only in the canonical series, which covers the identical full minute
grid.

## Architectural direction

LIORA is an academic, local MLOps research system, not an AWS deployment. Its
module, storage and container boundaries are drawn as a Pre-AWS architecture on
purpose: every local implementation is the smallest that works — one DuckDB file
per asset, Parquet and JSON in the asset's folder, one image for the tree, a
Makefile — and the responsibilities are cut so that a later move onto standard
cloud primitives (an object store, a container runtime, a stage orchestrator)
would replace the local storage, the local Docker execution and the local stage
order without redrawing the domain pipeline. No cloud infrastructure exists here
and none is planned; the mapping is described, not built. Correctness is shown by
the whole chain running end to end on a small representative basket, `BTC`
today, never by production-scale infrastructure: there is no test suite, no
security layer and no guard beyond the seven the mathematics needs (`AGENTS.md`
§ Values). The rule, its non-goals, the mapping table and what the shape holds:
[module_skills/skill_pre_aws_solution.md](module_skills/skill_pre_aws_solution.md).

The same skill seats the four things a move would name first — the host and the
volume where every asset's folder and the other `store/<content>/` folders live, the
one-off task and the state machine over the stages, the asset's one database
file, and the strategy host that is absent; `AGENTS.md` § Skills absent here,
described lists the skills those seats imply, each with its owner, what it
would govern and the one condition under which it is written. Four local skills
carry one seat paragraph each, naming the primitive their object answers to and
citing that skill for the rest. Whether each seat is the cheapest that keeps its
boundary — what could be less, and whether it is — is
[REPORT_pre_aws_minimalism.md](REPORT_pre_aws_minimalism.md).

## Data formats

Raw ZIPs are the Lean `cryptofuture` minute format, one tree per venue,
headerless `offset_ms_from_utc_midnight,open,high,low,close,volume`; timestamps
are bar-open UTC epoch milliseconds on a strict 60 000 ms grid, volume is
base-asset volume. The canonical series and its 15m/1h/4h aggregations live only
in `store/assets_artifacts/<TICKER>/<TICKER>_research_ohlcv.duckdb`; the
folder's parquets are feature columns, not prices. For Lean backtests use the
raw ZIP trees. Schema:
`module_data/skills/skill_candle_canonicalisation.md`
§ 11 and § 13.

## Dashboard

- **Pipeline** — canonical rows, real-data share and forward-filled bars per asset,
  its observation lag and measurement age, each warned past the download cadence;
- **Data Quality** — raw-source coverage, gaps, duplicates, OHLC violations and
  zero-volume bars per provider, then canonical construction: source shares,
  switches, the largest 1m move at a switch, cross-source divergence;
- **ML Research** — the cross-section of every asset's result, and the feature
  catalogue: every definition the repository computes, its terms, the history
  each covers on each timeframe, the warm-up it needs and the nesting of the levels;
- **ML Assets** — one asset at a time in five frames: LABEL, MODEL, STRATEGY, FEATURE SET, PROPOSALS;
- **Scalability** — every file the crawler's skill matrix lists, with its last crawl, its age, its crawl count and its report, from `make skills-status`;
- **Lifecycle** — one recorded run end to end, measured from outside by `record.py`:
  for every stage its start, its time, its exit code and what it added, changed and
  removed in the four pipeline stores, then every file it touched, by store and path. Nothing
  a stage says about itself enters the record.

One control in the top right leaves the page, for the DevOps persona:

- **DevOps** — the panel: every container, network and volume the daemon
  reports, with `start` / `stop` / `restart` offered for this
  project's own containers alone.

## ML research layer

`module_features/` builds, per asset and deterministically, the feature
catalogue from the canonical series — eight feature definitions on the
timeframes of the register, twenty-two columns, each name read off its terms
(`module_features/skills/skill_feature_taxonomy.md`)
— and writes the contract, `<TICKER>_catalogue.json`, that names them to the next
layer; `module_ml/` takes the fifteen columns of the default set as X until a
promotion, triple-barrier labels resolved on the canonical 1-minute path, a
purged walk-forward protocol with average-uniqueness weights and an Optuna
search over XGBoost, a final out-of-sample fold that selects nothing, and a
top-down gated strategy with explicit costs, whose trades leave at their own
take-profit and stop while the label they learned from stays symmetric. Beside
the chain, a coordinate search moves the asset's feature set and its barrier
geometry one step at a time, on the three validation years only: it raises the
CAGR of those years chained into one walk-forward path, and it may only keep a
move that raises the Calmar ratio of every one of them. The decision is taken at
a 15m close and filled one minute later. Every per-asset stage runs `JOBS` assets in
parallel, one process each, thread caps at one. Every asset folder describes
itself in `<TICKER>_README.md`. Full methodology:
`module_ml/skills/methodology_ml.md`.
