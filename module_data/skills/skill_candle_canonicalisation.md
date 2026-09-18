# Skill: candle canonicalisation — one venue's candle, chosen whole

The normative contract for what a canonical minute is, which venue's candle
becomes it, and what is stored beside it as evidence. It belongs to
`module_data` and travels with it: a reader who has only this directory can
answer every candle question without leaving it. *The repository shows the
destination, not the road* — the rules below are the destination, and
`ingest.py` is the road that reaches it.

## 1. What this module owns

```
external market API
        ↓
raw venue candles
        ↓
venue validation
        ↓
per-asset market database
        ↓
canonical 1m market object
```

The product of `module_data` is **one complete, provenance-aware canonical
market object per asset**: every minute of the grid present, every printed
price traceable to the venue that printed it.

`module_data` does not own feature engineering, labels, hyper-parameter search,
XGBoost, strategy selection, research simulation or any trading decision. In
this project it does not own the 15m/1h/4h aggregations either — those
tables live in the same database file but are written by `module_features/bars.py`,
downstream of this contract (§ 13, § 14).

Everything below the canonical object is source-neutral: no downstream stage
knows which venue printed a given minute, and none needs venue-specific
gap handling.

## 2. The two venues

Both are public keyless REST endpoints over USDT-margined perpetuals. The
operational detail — retries, backoff, the listing probe, the day-completeness
abort — is `methodology_data.md`; what matters here is that the two differ in
transport and agree in meaning.

| property | Binance | Bybit |
|---|---|---|
| market | USDS-M perpetual | Linear perpetual |
| symbol example | `BTCUSDT` | `BTCUSDT` |
| interval | 1m | 1m (`interval=1`) |
| API | REST, `fapi/v1/klines` | REST v5, `v5/market/kline` |
| authentication | public, keyless | public, keyless |
| candle fields kept | columns 0–5: open time, O, H, L, C, V | columns 0–5: start, O, H, L, C, V |
| volume semantic | base-asset volume | base-asset volume (contract multiplier 1) |
| daily request layout | one request per UTC day (`limit=1500`) | two 720-minute windows (`limit=1000` < 1440) |
| API ordering | chronological, used as returned | newest-first, therefore sorted ascending before writing |
| durable raw contract | Lean-compatible day ZIP | the same Lean-compatible day ZIP |

**After the downloaders both venues carry one logical candle schema.** A
difference in transport, paging or ordering is resolved inside the downloader
that speaks it and never reaches the selection rule. Nothing downstream of the
raw tree may branch on which venue it is reading.

## 3. Raw storage contract

Raw candles are kept as the evidence of one venue's observation, in a
Lean-exact tree, one leaf per venue and symbol:

```
store/raw_1m/cryptofuture/<venue>/minute/<symbol lowercase>/YYYYMMDD_trade.zip
    └── YYYYMMDD_<symbol lowercase>_minute_trade_perp.csv
        headerless: offset_ms_from_utc_midnight,open,high,low,close,volume
```

The folder and the file carry the symbol in lower case because Lean demands it; the
artifact folder is the ticker in capitals — a boundary, not an inconsistency to tidy
away (`AGENTS.md` § Architecture shape).

Two units, deliberately distinct:

| unit | what it is | value now |
|---|---|---|
| ingestion unit | the quantum of download work, written once and never restated | 1 UTC day = 1 ZIP |
| long-term archive unit | the quantum a future compaction may choose | the same, until a compaction is written |

A future compaction may fold whole years, **per venue**:

```
binance/archive_2021.zip        allowed
bybit/archive_2021.zip          allowed
BTC_all_venues_2021.zip         forbidden
```

The venues stay logically separated at every archive granularity. Binance raw
and Bybit raw are never combined into one raw dataset before canonicalisation,
because raw data is the proof of what a *specific* venue observed; a combined
raw file destroys the only thing it was kept for.

## 4. Candle validity

Before a candle may be selected it must be **valid**. Validity is a property of
one venue's candle alone; it never consults the other venue.

| field | condition |
|---|---|
| `open` | finite, `> 0` |
| `high` | finite, `> 0` |
| `low` | finite, `> 0` |
| `close` | finite, `> 0` |
| `volume` | finite, `>= 0` |
| geometry | `low <= min(open, close)` |
| geometry | `high >= max(open, close)` |

```
valid =
    finite(O, H, L, C, V)
    AND O > 0 AND H > 0 AND L > 0 AND C > 0
    AND V >= 0
    AND L <= min(O, C)
    AND H >= max(O, C)
```

A candle that fails any line is **invalid**, and for the selection rule an
invalid candle and an absent candle are the same thing. A minute with no row
at all is likewise invalid, not NULL: `ingest.py` folds absence into `false`
at the join, so the decision table below never has to distinguish them.

## 5. A candle is chosen whole

**The selection unit is the whole candle.** When Binance wins, all five values
come from Binance; when Bybit wins, all five come from Bybit:

```
canonical.O = winner.O
canonical.H = winner.H
canonical.L = winner.L
canonical.C = winner.C
canonical.V = winner.V
```

Field-level selection is forbidden. None of these is a legal canonical candle:

```
O = Binance,  H = Binance,  L = Binance,  C = Binance,  V = Bybit
H = max(Binance.H, Bybit.H)
L = min(Binance.L, Bybit.L)
C = average(Binance.C, Bybit.C)
```

A canonical candle is **one candle that a single venue actually observed, or an
explicitly flagged `ffill`** — never a composite and never a derived quantity.
No canonical price is an average of two sources, because an average prints
quotes that existed nowhere: a per-minute index weighted by the two venues'
notional moves the printed price whenever the weights shift, which on this
window reaches 7.8 % in a single minute — a move no venue made.

Prices and volume are copied verbatim: no weighting, no averaging, no rounding
at any layer.

## 6. The primary-failover decision table

Binance is the primary venue, Bybit the secondary. For every minute of the
grid exactly one row below applies. This is the normative decision table; no
other document keeps a copy of it.

| Binance | Bybit | O | H | L | C | V | `source` | `zero_volume` |
|---|---|---|---|---|---|---|---|---|
| valid, V>0 | valid, V>0 | Binance | Binance | Binance | Binance | Binance | `binance` | false |
| valid, V>0 | valid, V=0 | Binance | Binance | Binance | Binance | Binance | `binance` | false |
| valid, V=0 | valid, V>0 | **Bybit** | **Bybit** | **Bybit** | **Bybit** | **Bybit** | `bybit` | false |
| valid, V=0 | valid, V=0 | Binance | Binance | Binance | Binance | 0 | `binance` | **true** |
| valid | missing / invalid | Binance | Binance | Binance | Binance | Binance | `binance` | `V = 0` |
| missing / invalid | valid | Bybit | Bybit | Bybit | Bybit | Bybit | `bybit` | `V = 0` |
| missing / invalid | missing / invalid | prev C | prev C | prev C | prev C | 0 | `ffill` | false |

Read as a priority ladder, the same table is four tiers and a fallback: a
traded Binance candle, then a traded Bybit candle, then a valid no-trade
candle from either venue in the same order, then forward fill. A traded candle
on either venue outranks a no-trade candle — an exchange maintenance
placeholder on Binance never outranks a real Bybit minute — and a valid
no-trade candle still outranks fabrication.

`zero_volume` is `true` exactly when the **winning** candle has `V = 0`. It is
therefore false on every `ffill` row: `ffill_bars` and `zero_volume_bars` count
disjoint sets of minutes, and neither is a subset of the other.

## 7. Volume, and why it chooses the venue

Volume is load-bearing: it is the only field that can move the choice away from
the primary venue. Four cases, exhaustive when both candles are valid.

### Case A — both venues traded

```
Binance V > 0
Bybit   V > 0
```

Result: **the whole Binance candle**. The primary venue wins whenever it traded.

### Case B — only the primary traded

```
Binance V > 0
Bybit   V = 0
```

Result: **the whole Binance candle**. Bybit's no-trade minute changes nothing.

### Case C — only the secondary traded

```
Binance V = 0
Bybit   V > 0
```

Result: **the whole Bybit candle**, `source = bybit`.

This is the load-bearing failover of the whole contract. A secondary venue with
real trading takes precedence over a zero-volume candle on the primary venue,
because a no-trade placeholder carries no information about the minute while a
traded candle does.

### Case D — neither venue traded

```
Binance V = 0
Bybit   V = 0
```

Result: **the whole Binance candle**, `V = 0`, `zero_volume = true`. Both
venues agree that nothing traded; the primary venue's own quotes are kept, and
the minute is flagged so that downstream monitoring can count it.

## 8. Scenario — a candle on both venues

Both candles valid. The decision is entirely § 7: every case keeps the whole
Binance candle but the one where only the secondary traded, which takes the
whole Bybit candle. Whichever wins, `binance_valid` and `bybit_valid` are both
`true` on the stored row, and `rel_divergence` is measured (§ 10) — the losing
venue is recorded as having been present, never as having contributed a value.

## 9. Scenario — a candle on one venue

### Only Binance

```
Binance valid
Bybit   missing / invalid
```

```
O = Binance O          V = Binance V
H = Binance H          source = binance
L = Binance L          zero_volume = (Binance V = 0)
C = Binance C          rel_divergence = NULL
```

### Only Bybit

```
Binance missing / invalid
Bybit   valid
```

```
O = Bybit O            V = Bybit V
H = Bybit H            source = bybit
L = Bybit L            zero_volume = (Bybit V = 0)
C = Bybit C            rel_divergence = NULL
```

A single-venue minute has nothing to fail over to. If that venue prints a
no-trade candle the canonical bar is that candle, flagged `zero_volume`; if it
prints nothing at all the minute falls through to § 10.

## 10. Scenario — no candle on either venue

```
Binance missing / invalid
AND
Bybit   missing / invalid
```

The minute is a canonical gap and is closed deterministically by forward fill.
With `P` the previous canonical close:

| field | value |
|---|---|
| `open` | `P` |
| `high` | `P` |
| `low` | `P` |
| `close` | `P` |
| `volume` | `0` |
| `source` | `ffill` |
| `zero_volume` | `false` |

```
O = H = L = C = previous canonical close
V = 0
source = ffill
```

**An `ffill` row is not an exchange observation.** It is the mechanism that
keeps the minute grid complete, and it stays unambiguously marked by its
provenance so that no reader can mistake it for a printed candle. It carries
the previous *close* only — never the previous high or low, which would invent
a range that no venue quoted.

Boundary: before the first valid candle on either venue there is no previous
canonical close, so such a minute carries NULL prices with `source = ffill`.
The Binance listing probe pins this to zero by aborting the download when a
symbol's history starts after the window (`methodology_data.md`).

## 11. Provenance

The canonical table stores the chosen candle together with the evidence for the
choice. Eleven columns, and the last five are provenance and data quality —
**never model inputs**:

| column | type | meaning |
|---|---|---|
| `timestamp_ms` | BIGINT | bar OPEN, UTC epoch ms, strict 60 000 ms grid, no missing minutes |
| `open`, `high`, `low`, `close` | DOUBLE | verbatim venue prices; previous canonical close on `ffill` rows |
| `volume` | DOUBLE | verbatim venue volume; `0` on `ffill` rows |
| `source` | VARCHAR | `binance` / `bybit` / `ffill` — the normative provenance of the minute |
| `zero_volume` | BOOLEAN | the winning candle was valid and traded nothing |
| `binance_valid` | BOOLEAN | a Binance candle was present with intact OHLC |
| `bybit_valid` | BOOLEAN | a Bybit candle was present with intact OHLC |
| `rel_divergence` | DOUBLE | cross-venue close divergence when both are valid |

The asset itself is not a column: the database file names it once,
`<TICKER>_research_ohlcv.duckdb`, and no table inside repeats it.

`source` is what makes a source switch visible. Within a minute nothing is
combined, so no averaging artifact exists to measure; between two minutes the
series may change venue and carry the cross-venue basis, which is why
`source_switch_count` and `max_abs_return_at_switch` are monitored (§ 16) rather
than smoothed away.

## 12. Relative divergence

When both venues have a valid candle:

```
                abs(binance_close - bybit_close)
rel_divergence = -------------------------------
                (binance_close + bybit_close) / 2
```

It is computed whenever both candles are valid — regardless of which venue won
and regardless of volume. It measures the pair, not the choice, and it is NULL
on single-venue minutes.

**`rel_divergence` is a quality-control measurement, never a selection rule.**
Under this contract a large divergence may not be used to:

- average the two prices,
- change which venue is primary,
- drop the minute,
- synthesise a replacement candle.

Strongly diverging minutes are real market dislocations, and the distribution
is exposed as `relative_divergence_p99` / `_max`. Introducing any
divergence policy is a change to this contract, not a tuning decision.

## 13. Physical storage

```
1 asset = 1 DuckDB file
```

```
store/assets_artifacts/BTC/BTC_research_ohlcv.duckdb
```

Inside it, tables — not separate database servers, not separate files:

| table | written by | holds |
|---|---|---|
| `ohlcv_1m_binance` | `module_data/ingest.py` | the Binance raw tree, materialised verbatim |
| `ohlcv_1m_bybit` | `module_data/ingest.py` | the Bybit raw tree, materialised verbatim |
| `ohlcv_1m_canonical` | `module_data/ingest.py` | this contract's product: the full grid with provenance |
| `ohlcv_15m_canonical` | `module_features/bars.py` | downstream aggregation, outside this contract |
| `ohlcv_1h_canonical` | `module_features/bars.py` | downstream aggregation, outside this contract |
| `ohlcv_4h_canonical` | `module_features/bars.py` | downstream aggregation, outside this contract |

The canonical series and its aggregations live **only** in the asset's own
database; the folder's parquets carry feature columns, not prices. For Lean
backtests use the per-venue raw ZIP trees. Each database is a pure function of
the asset's two raw leaves, and its grid ends at that asset's own last raw
minute over both venues.

## 14. Stage transformations

| stage | input | output | responsibility | owner |
|---|---|---|---|---|
| download Binance | Binance REST API | raw Lean day ZIP | preserve venue evidence | `module_data` |
| download Bybit | Bybit REST API | raw Lean day ZIP | preserve venue evidence | `module_data` |
| ingest Binance | Binance raw tree | `ohlcv_1m_binance` | relational materialisation | `module_data` |
| ingest Bybit | Bybit raw tree | `ohlcv_1m_bybit` | relational materialisation | `module_data` |
| canonicalisation | the two venue tables | `ohlcv_1m_canonical` | primary-failover selection | `module_data` |
| aggregation | canonical 1m | `ohlcv_15m_canonical` | deterministic OHLC aggregation | `module_features` |
| aggregation | canonical 1m | `ohlcv_1h_canonical` | deterministic OHLC aggregation | `module_features` |
| aggregation | canonical 1m | `ohlcv_4h_canonical` | deterministic OHLC aggregation | `module_features` |

Ingest is idempotent: each venue table is emptied and reloaded from the ZIP
tree, and the canonical table is rebuilt from the two venue tables on every
run. The same raw tree reproduces the same database.

## 15. Docker does not own the database

DuckDB here is an **embedded database**, not a service. There is no

```
container → network → DuckDB server
```

There is

```
Python process in a container → mounted filesystem → .duckdb file
```

The store is mounted by name — `STORE_ASSETS_ARTIFACTS_DIR` on either side — so the path is a
prefix swap:

| host | container |
|---|---|
| `store/assets_artifacts/BTC/BTC_research_ohlcv.duckdb` | `/store/assets_artifacts/BTC/BTC_research_ohlcv.duckdb` |

Docker may start the process, give it a filesystem, cap its memory, cap its
CPU and set its permissions. Docker may not define candle validity, the
primary-failover order, OHLC semantics, volume semantics or `ffill` semantics.
Those belong to this document, and they hold identically when the same stage is
run outside a container.

**The seat.** On the one Linux container instance (Amazon ECS on Amazon EC2) the
file sits at the same path under `/store`, on the volume mounted where the
`./store_<content>` mounts are today; the whole-file lock holds because that volume is a block device, not a
network filesystem. After the run the file is copied whole to the asset's prefix
in object storage (Amazon S3) — a copy, never a mount. The promotion threshold
is `module_skills/skill_pre_aws_solution.md` § The databases.

The rule this section instantiates for the database — a container is compute
and never the owner of an asset's state — is project-wide and lives in
`module_skills/skill_pre_aws_solution.md`, the canon beside the modules; this section stays its one
statement for the market object.

## 16. Data-quality invariants

`module_data/status.py` scans each database read-only and publishes what it
finds. Three numbers are invariants — a non-zero value is a defect:

```
duplicate_count      == 0     per venue
invalid_row_count    == 0     per venue
ohlc_violation_count == 0     on the canonical series
```

`invalid_row_count` counts what `ingest.py` will not join, with `ingest.py`'s own
`OHLC_INTACT_PREDICATE` imported rather than restated (§ 4): a row whose fields are
not finite, whose price is not above zero or whose volume is negative is rejected at
the join and would otherwise be counted nowhere — `coverage_pct` and `gap_count` are
built from timestamps present, not from rows usable. On the page an invariant column
is marked as such: after a change of provider these must still be zero, while the
observations beside them are expected to move.

The rest are **observations**. They describe the market and the venues, and no
value of them is by itself a failure:

| observation | what a non-zero value means |
|---|---|
| `gap_count` | minutes a venue never printed; the canonical grid closes them |
| `zero_volume_bars` | candles that traded nothing — on a venue row the raw test `volume = 0`, on the canonical row the stored `zero_volume` flag, which § 6 sets only when the **winning** candle traded nothing. One name, two objects, and on the canonical series it is false on every forward-filled minute |
| `ffill_bars` | minutes neither venue printed |
| `source_share_pct_by_venue` | the share of minutes each venue won, keyed by venue in the tier order of `source_venues`; a share below the primary's is evidence the failover works, not a fault |
| `source_switch_count` | places the cross-venue basis can enter a return |
| `relative_divergence_p99`, `relative_divergence_max` | the 99th percentile and the largest of the cross-venue close distance |
| `flat_bars` | a venue's own minutes that traded nothing and quoted one price — `volume = 0` and `open = high = low = close`, tested on the raw table and consulting no validity predicate; a subset of that venue's `zero_volume_bars` |
| `longest_flat_run_minutes` | the longest unbroken run of flat minutes **on the canonical series** — the same geometry as the venue row above, on a different object. A forward-filled row satisfies that geometry too (§ 10) and is **not** one of them: a canonical minute is forward-filled, flat, or traded, decided in that order, or fabrication would be reported as a quiet market |
| `longest_ffill_run_minutes` | the longest unbroken run of forward fill. `ffill_bars` alone cannot tell a provider dark for three days from one dropping scattered minutes over four years; the first is a fabricated regime, the second is noise |
| `repeated_candle_count` | canonical minutes repeating the previous candle verbatim **while volume was printed** — a feed frozen on its last bar. No flatness count can see it: the timestamps differ, the geometry is intact and the volume is not zero |
| `last_close` | a venue's last printed close. Every other number here is dimensionless, so nothing else in the snapshot would notice a delivery under the wrong symbol |
| `max_abs_return_1m` | the largest one-minute absolute return on the canonical series |
| `max_abs_return_at_switch` | the largest one-minute absolute return at a source switch — the basis a switch let in |
| `gap_count_after_first_observation` | a venue's gaps counted from its first printed minute, so a listing inside the window is not a gap |
| `coverage_pct` | the share of the grid a venue printed. The real-data and forward-fill shares are the page's arithmetic over `row_count` and `ffill_bars`, not keys |

A non-zero share for a venue below the primary is proof of a working failover. `zero_volume_bars > 0`
in a raw venue is not automatically a fault either — what it means depends on
whether that minute won the canonical selection.

## 17. Known limitations of the canonical series

These are properties of the contract, not defects to be smoothed away. The
limitations of *acquisition* — a short post-listing day, the single listing
probe, idempotence by file presence — are `methodology_data.md` § 4.

- **A single-venue minute has nothing to fail over to.** When only one venue is
  listed and it prints a no-trade candle, the canonical bar is that candle,
  flagged `zero_volume`; when it prints nothing, the bar is a forward fill.
  The failover of § 7 — only the secondary traded — needs two listed venues
  to have anything to choose between.
- **A source switch carries the cross-venue basis.** Changing venue between two
  minutes can move the canonical close by the current Binance–Bybit basis
  without either venue having moved. The count and the largest such move are
  monitored as `source_switch_count` and `max_abs_return_at_switch`. No
  smoothing is applied: the switch is visible, not hidden.
- **A source switch is the only place a basis jump can enter.** Within a minute
  nothing is combined, so no averaging artifact exists to measure; a return
  that *spans* a switch may still carry the basis, which is exactly what those
  two measurements are for.
- **There is no cross-exchange divergence cutoff.** Strongly diverging minutes
  are real market dislocations and are kept. Only the distribution is exposed
  (§ 12); adding a cutoff would be a change to this contract.
- **The grid can begin before the data does.** Minutes before the first valid
  candle on either venue carry NULL prices with `source = ffill` (§ 10). The
  Binance listing probe pins this to zero for the current basket.

## 18. Reference observation

**Example only — an observed run, not an invariant.** These are the numbers of
one BTC run of the window as it stood when this was read, from
`store/status/data_status.json`. Nothing in the system may be coded
against them.

```
Binance     coverage 100 %      zero-volume candles 181
Bybit       coverage 100 %      zero-volume candles  92

Canonical   binance source  99.994 %
            bybit source     0.006 %   (181 minutes)
            ffill                 0    longest run 0
            zero-volume           0    longest flat run 0
            source switches      18
            repeated candles      1
            invalid rows          0 on either venue
```

The one repeated candle is 2025-06-29, where Binance printed the previous minute again
down to its volume of 2.723. It is an observation of this run, not a rule: one minute in
three million says nothing about the venue, and the count exists so that a frozen feed
cannot pass as a market.

The 181 Bybit minutes are exactly Binance's 181 zero-volume minutes: the case
of § 7 where only the secondary traded, firing on every one of them. That
correspondence is a property of this run, not a rule — a later run in which
Bybit also printed no trade on one of those minutes would move it to the case
where neither venue traded.

## 19. Naming

This document uses, and this module writes:

```
raw candle          venue candle        valid candle
canonical candle    primary venue       secondary venue
primary-failover    zero-volume candle  ffill
provenance          relative divergence venue selection
canonicalisation
```

The word **merge** is avoided: it suggests mixing O/H/L/C/V across venues,
which § 5 forbids. Say *venue selection*, *canonicalisation* or *primary-failover
selection* instead. The register's rejected synonyms — *fused series*, *index*,
*blended price* — are in `module_skills/glossary.md` § Market object.
