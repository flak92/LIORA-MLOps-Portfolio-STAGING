# module_data — venue candles in, one canonical market object out

The front door of this module: what it is, where its responsibility stops, how
to run it, and what comes out. The rules themselves live in `skills/` and are
not repeated here — this file orients, the skills bind. *The repository shows
the destination, not the road*.

`module_data` turns two public exchange APIs into **one complete,
provenance-aware canonical 1m market object per asset**. It downloads Binance
USDS-M and Bybit Linear one-minute klines into a QuantConnect Lean-exact ZIP
tree, materialises both venues into the asset's own DuckDB file, and rebuilds a
canonical minute series in which every printed price is one venue's candle
copied verbatim — or an explicitly flagged forward fill.

## Where the responsibility stops

```
external market API → raw venue candles → venue validation
    → per-asset market database → canonical 1m market object
```

Everything above that last arrow is this module. The feature catalogue belongs
to `module_features`; labels, hyper-parameter search, XGBoost, strategy
selection, research simulation and every trading decision belong to
`module_ml`. So do the aggregations on every timeframe of the register: they
live in the same database file but are written by `module_features/bars.py`,
downstream of this module's contract.

Downstream code is source-neutral. No stage below the canonical object knows
which venue printed a given minute, and none needs venue-specific gap handling.

That boundary is also the storage seam the repository is prepared for: the raw
tree is written once and never restated, the asset's database is a pure function
of its two raw leaves, and `module_features` reads the finished canonical object —
never a venue. Raw storage, canonical storage and the research compute could
later become three separate places without a rule of this module moving. The
direction:
[module_skills/skill_pre_aws_solution.md](../module_skills/skill_pre_aws_solution.md).

## Stages

Three stages, in order. Each is idempotent and each runs in a one-off container of the `data` runner.

| stage | target | does |
|---|---|---|
| download | `make data-download` | both venues' 1m klines → Lean day ZIPs; skips a day whose ZIP exists |
| ingest | `make data-ingest` | both ZIP trees → the asset's DuckDB, then rebuilds the canonical series |
| status | `make data-status` | read-only scans → stdout tables + `store/status/data_status.json` |

Every stage module exposes `main()` and shares one CLI, so a single asset can be
addressed directly:

```
python -m module_data.ingest --tickers BTC
```

In a shell no launcher set up, export the three `STORE_*_DIR` this module reads — `STORE_RAW_1M_DIR`,
`STORE_ASSETS_ARTIFACTS_DIR`, `STORE_STATUS_DIR` — first; `make` and compose do it for
you (`module_skills/glossary.md` § Stores).

`module_data.status` takes `--tickers` like every stage and reports the assets it
was told; the launcher names the whole basket.

## What it reads and writes

```
store/raw_1m/cryptofuture/<venue>/minute/<symbol>/YYYYMMDD_trade.zip   the Lean day ZIP — skills/skill_candle_canonicalisation.md § 3

store/assets_artifacts/<TICKER>/<TICKER>_research_ohlcv.duckdb
    ├── ohlcv_1m_binance      written here
    ├── ohlcv_1m_bybit        written here
    ├── ohlcv_1m_canonical    written here — the product
    ├── ohlcv_15m_canonical   written by module_features/bars.py
    ├── ohlcv_1h_canonical    written by module_features/bars.py
    └── ohlcv_4h_canonical    written by module_features/bars.py

store/status/data_status.json   the status snapshot the dashboard reads
```

One asset is one database file; the file names the asset and no table inside
repeats it. The raw tree keeps the venues separate for good — raw data is the
evidence of what a *specific* venue observed.

Each `module_data` path is built in `config.py` and nowhere else; the one
exception is the Lean tree's own file names, which belong to `lean.py`, the
module's single external-format boundary.

## What you get for a given minute

The four questions a reader asks, each answered in `skills/skill_candle_canonicalisation.md`:

- **Both venues printed a candle** — § 6 (the decision table) and § 7 (the volume cases);
- **Only one venue printed a candle** — § 9;
- **Neither venue printed a usable candle** — § 10 (the forward fill);
- **Both venues printed a candle that traded nothing** — § 7, the case where neither venue traded.

What makes a candle eligible at all is § 4; the two absolutes that hold across every answer are § 5.

## What the status stage measures

`make data-status` scans each database read-only and publishes per venue and for the canonical
series — the candles only: a ZIP is an intermediate file, not data, and a short or empty one
appears as a deficit in `row_count`, `coverage_pct` and `gap_count`. Which numbers are
invariants and which are observations is § 16 of
`skills/skill_candle_canonicalisation.md`; `module_skills/glossary.md` § Data quality
registers the measurement keys and § Payload structure the containers, the envelope and
the per-row facts — between them every key the snapshot carries.

## Extending

Every extension is one edit in the file that owns the fact, and the documents that
name the fact move in the same commit.

| what you add | where, and how much | the gate |
|---|---|---|
| a venue | `download_<venue>.py` beside its siblings, in their shape — `lean.py` writes the day, the probe and the day-completeness abort stay as they are; `SOURCE_VENUES` and the venue's URL, limit and delay constants in `config.py`; in `ingest.py` its raw table, its CTE, its tier and `chosen` branch in `CANONICAL_INSERT`, its `<venue>_valid` column in `CANONICAL_DDL` and its table in the grid-end `UNION ALL`; nothing in `status.py` — its scans, aliases, shares and stdout columns are all derived from `SOURCE_VENUES`; the venue-named sections of `skills/skill_candle_canonicalisation.md` rewritten for the new tier order — § 2, the decision table of § 6, § 8, the scenarios of § 9, the provenance table of § 11, § 12, § 17 and the reference observation of § 18; nothing in `module_skills/glossary.md`, which registers the venue-keyed families rather than the venues; then outside this module: nothing in `module_monitoring/`, whose page builds one section, one column and one share cell per entry of `source_venues`, and one more `basket` line in the Makefile's `data-download` | the existing venues' raw tables untouched, and the canonical series byte-identical for every minute the new venue does not win |
| an observation of the snapshot | one alias in a scan of `status.py` — the alias is the key — its row in `skills/skill_candle_canonicalisation.md` § 16 and in `module_skills/glossary.md` — § Data quality for a measurement, § Payload structure for a container or an envelope fact — and the cell that shows it in the monitoring module's `data.js` | the existing keys unchanged; the artifacts untouched |
| a day of the raw tree | never by hand: delete the day's ZIP and rerun `data-download` (`skills/methodology_data.md` § 4) | the canonical series rebuilt by `data-ingest`, byte-identical where the day did not change |

A new asset is not an extension of this module: it is a ticker in `TICKERS` of the Makefile (`README.md` § Extending); nothing changes here.

## Docker does not own the database

A container is compute, never the owner of the database; what Docker does and does not define
is § 15 of the same skill.

## Design rationale

Why each object of this module sits where it does — the answers of
`module_skills/skill_self_explaining_naming.md` § The naming review written
down, one row per object, analogous pair or the module's documents; the mapping
row it answers to is `module_skills/skill_pre_aws_solution.md` § The mapping
table, cited by its *responsibility* column and never repeated.

| object | why here | why beside these | why this boundary | answers to |
|---|---|---|---|---|
| `config.py` | The one file that builds a path of this module (§ What it reads and writes) — `raw_symbol_dir()`, `artifact_dir()`, `research_ohlcv_duckdb()` and the snapshot's path — imported by every stage file and by `lean.py`. | `module_features/config.py` and `module_ml/config.py` carry their own copies of `artifact_dir()`, `research_ohlcv_duckdb()`, `to_utc_ms()`, the units they use, the ceiling and the `--tickers` parser — twice by extraction, each copy as its row in `module_skills/glossary.md` § Twice by extraction says — and no module outside this one imports it — `module_monitoring` reads the snapshot's own keys and sizes what lies in the asset folder — so no other module builds a path of this one from anything but a copy of its descriptors. | Every stage reaches a store through a descriptor here, so the raw tree, the asset folder and the snapshot keep the same paths under `/store` whatever disk is mounted there (`module_skills/skill_pre_aws_solution.md` § The volume is the home, the store is the copy). | one row per descriptor: STORAGE — raw, immutable, one object per UTC day; STORAGE — one prefix per asset; STORAGE — status and run objects |
| `lean.py` | The module's one external-format boundary (`AGENTS.md` § Canonical vocabulary): the day-ZIP and CSV names, `is_full_utc_day()`, `write_lean_zip()` and `lean_day_zip_paths()`. | Both downloaders, `ingest.py` and `status.py` import it, and it imports `config.py` alone. | It names only the file inside the venue folder `config.py` builds — the reader that wants this format is seated by `module_skills/skill_pre_aws_solution.md` § Module boundaries are extraction boundaries — so the raw days keep the same names under the same tree on whatever disk holds `store/raw_1m/`. | STRATEGY EXECUTION — absent |
| `download_binance.py` + `download_bybit.py` | SOURCE — the two files of the download stage (§ Stages), each fetching one venue's klines over a keyless public API and writing them as the day ZIPs `lean.py` names (their docstrings). | Twins that differ in the endpoint they speak, both importing `config.py` and `lean.py`, and `ingest.py` reads the trees they leave. | Each writes one ZIP per full UTC day and skips a day whose ZIP exists (§ Stages), so a rerun against the same tree on any disk mounted at `/store/raw_1m` writes only the days that are missing. | STORAGE — raw, immutable, one object per UTC day |
| `ingest.py` | INGEST and CANONICAL in one stage: it writes the two venue tables and the canonical table of one asset's database file (§ What it reads and writes). | It imports `config.py` and `lean.py`, reads the ZIP trees the downloaders wrote and writes the table `module_features/bars.py` reads. | It runs one asset at a time in a one-off container of the `data` runner through the `fanout` macro (`module_skills/skill_asset_containers.md` § The topology), and the file it writes stays at the path `research_ohlcv_duckdb()` builds, under the same whole-file lock, whatever disk holds it. | COMPUTE — one stage for one asset |
| `status.py` | The stage that measures this module's own state — read-only scans of every asset's database, published as one snapshot for the basket (§ What the status stage measures) — placed by `AGENTS.md` § Architecture shape. | It imports `config.py`, `lean.py` for the download cadence and `ingest.py` for the validity predicate it counts the failures of, scans the databases `ingest.py` wrote, and writes `store/status/data_status.json` for `data.js` to fetch. Its per-venue scans, aliases and shares are derived from `SOURCE_VENUES`, which it publishes as `source_venues`. | It takes `--tickers` like every stage — the launcher passes the basket — and runs once in a one-off container of the `data` runner (§ Stages; `module_skills/skill_pre_aws_solution.md` § The resident container is a local mechanism), writing the snapshot at the one path `DATA_STATUS_JSON_PATH` builds, under the `STORE_STATUS_DIR` the launcher names. | COMPUTE — one stage, one one-off process |
| `__init__.py` | The package that makes `python -m module_data.<stage>` a command (§ Stages), its docstring the module's responsibility in one line. | It names the two venues, the Lean ZIPs and the one database per asset, and imports nothing. | The same `python -m module_data.<stage> --tickers <TICKER>` runs in a one-off container of the `data` runner (§ Stages) — the launcher setting the three `STORE_*_DIR` — the command `docker compose run --rm -T data` carries unchanged whichever host starts it. | COMPUTE — one stage, one one-off process |
| `sub_module_terminal/` | The module's own terminal (§ Its sub-module): the hand's instrument over the three targets of § Stages, placed by `AGENTS.md` § Canonical vocabulary, the sub-modules row, and § The default choice — a nesting named rather than promoted. | Inside the module whose targets it starts, beside the stages; it imports `config.py` for the venues and the descriptors and `lean.py` for the day ZIPs — standard library both — and its `tui.py` is one file with every other terminal's and the crawler's, five times by extraction (`module_skills/glossary.md` § Twice by extraction). | It runs on the host's `python3` and gum, in no container and no venv, opens no database, writes no file and starts everything through `make data-<stage>` — the target name the root `Makefile` carries; what its screen holds is `sub_module_terminal/skill_data_terminal.md`. | no row — a hand's instrument on the host, with no part in the chain's dataflow |
| the module's documents — `README_module_data.md` and `skills/` | This orientation and the normative documents of `skills/`, filed by ownership (`AGENTS.md` § The default choice). | The orientation points at the documents beside it (§ Its normative skills), and every rule about this module sits in `skills/` (`AGENTS.md` § Canonical vocabulary, the row *a module's own skills*). | Tracked files under `module_data/` that no stage and no route reads, travelling with the code beside them — the same paths beside the code wherever the code is. | no row — a document that travels with the task's code, seated beside its module |

## Its sub-module

`sub_module_terminal/` is the module's own terminal, the hand's instrument over the three
stages of § Stages: `make data-terminal ASSET=<TICKER>` opens it on each asset's raw days and
its database, and one answer starts one stage — download, ingest or status — through `make`;
then it closes. It reads through this module's own `config.py` and `lean.py` — the venues, the
raw leaf of each and the database's path — opens no database and computes nothing: a count of
day ZIPs and the last day they are named for is presentation, and everything that runs, runs
through the root `Makefile`, under the target name `data-<stage>` it carries. Its orientation
is `sub_module_terminal/README_sub_module_terminal.md`, its rules the skill beside it,
`sub_module_terminal/skill_data_terminal.md`, and the standards of its screens
`module_skills/skill_tui_designer.md`.

## Its normative skills

| document | answers |
|---|---|
| `skills/skill_candle_canonicalisation.md` | what a canonical candle is, which venue's candle becomes it, where it is stored |
| `skills/methodology_data.md` | where raw venue candles come from and how they are fetched |

Project-wide rules — the name register, determinism, the container topology,
the Pre-AWS direction — are in `module_skills/`, indexed by
[module_skills/README.md](../module_skills/README.md).
