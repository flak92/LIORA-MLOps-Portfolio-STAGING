# Skill: feature taxonomy — names built from their terms

A feature name is derived, never invented: it is read off the computation, term by term, from the
smallest part upward. Every number in a name is a count of bars of one timeframe, and that
timeframe is written in the name. Nothing else is encoded — not the decision grid, not the label
horizon, not the asset, not a category word, not a wall-clock span. *The repository shows the
destination, not the road*: the grammar below is read off the catalogue record in
`module_features/config.py`, and no check stands behind it. Tunable values live in the catalogue
record, an indicator's invariants once in its register record beside its kernel, and the evaluator
knows nothing neither says.

The chain, smallest part first: a series or an indicator with its one parameter (a **term**), the
terms composed into a **feature definition**, the definition bound to a timeframe as a **feature**,
the features an asset selects as its **feature set**, the set as the columns the model sees. The
smallest part has one meaning; every larger structure is composed deterministically from smaller
ones, so any column of a feature parquet can be taken apart and made to answer: what information,
from which bars, over what history, with which parameters.

## The timeframe register — one definition

A timeframe token is `<integer><unit>`, unit in `m`, `h`, `d`. The register is the experiment's
hierarchy, a literal: `HIERARCHY_TIMEFRAMES` in `module_features/config.py`, finest first, and
`DECISION_TIMEFRAME` beside it. Duration and slot derive from the token — `timeframe_duration_ms`
reads the number and the unit, `timeframe_slot` writes the number, zero-padded, into its unit's
field of the five slots of `module_skills/skill_sorting_files_naming_standard.md` — so
`TIMEFRAME_DURATION_MS` and `TIMEFRAME_SLOT` are read off the hierarchy and never written by hand.
Every timeframe is built from the canonical 1m series by `bars.py`, one loop over the hierarchy —
the venue's own 4h candle would be the same aggregation, so an aggregate here is a native bar, not
a resample.

The hierarchy is a literal because everything that reads it is the experiment: the decision grid
is its first entry, the trend gate's timeframe its last, the count the strategy's agreement
compares its length. A token enters when its duration is an integer multiple of the decision
timeframe and divides one UTC day, so bar boundaries land on UTC midnight (`30m`, `2h`, `6h`, `12h`, `1d`
qualify; a token finer than the decision timeframe would have to move `DECISION_TIMEFRAME` with it, and a week or a
month needs an anchor the token does not carry).
Adjacent entries keep a ratio of at least three — below that two levels sample the same price
movement (the triple-screen hierarchy, `module_ml/skills/methodology_ml.md` § 13 [10]).
Today: `15m`, `1h`, `4h`, ratios 4× and 4×. A new token is one line in the hierarchy and a new
experiment; the bars, the parquets and the catalogue's offered timeframes follow from it.

## Series and indicators — the terms

A **series** is a column of one timeframe's bars, with no parameter: `open`, `high`, `low`,
`close`, `volume`, `log_volume` (= log1p(volume)) — a bar column, or `log_volume`, the one series with a
kernel (`SERIES_KERNELS` in `catalogue.py`).

An **indicator** is one computation over series of one timeframe with exactly one integer
parameter, written glued to the indicator token, as the trade writes RSI14 and SMA200. The
register is one record per token beside its kernel — `INDICATORS` at the end of
`module_features/indicators.py`: the kernel, the word its parameter carries, the warm-up it needs
in multiples of that parameter, the bar columns it reads when its inputs are fixed, and the range
it outputs when that range is bounded:

| indicator | `inputs` | `parameter_word` | `warmup_multiple` | `output_range` |
|---|---|---|---|---|
| `ema<n>` | any series, `close` by default | `SPAN` | 4 — a recursion is finite from its first bar and settles in four spans by convention | — unbounded |
| `sma<n>` | any series, `close` by default | `LOOKBACK` | 1 — a window is NaN inside its lookback | — unbounded |
| `rsi<n>` | `close` — fixed | `SMOOTHING_PERIOD` (Wilder) | 4 | 0 to 100 |
| `atr<n>` | `high`, `low`, `close` — fixed | `SMOOTHING_PERIOD` (Wilder) | 4 | — unbounded |
| `zscore<n>` | any series, `close` by default | `LOOKBACK` | 1 | — unbounded |
| `range_position<n>` | `close`, `high`, `low` — fixed | `LOOKBACK` | 1 | 0 to 1 |

The kernel carries the token's name (`ema`, `sma`, `rsi`, `atr`, `range_position`; `zscore` is
`rolling_zscore`, the one kernel named for its family), and the record is the one place its
invariants are written: the name grammar, the warm-up, the evaluator and the catalogue block of the
snapshot all read it. A second parameter, when an indicator needs one, extends the record and this
grammar in the same commit — derived names do not change. The parameter word is the one
`../../AGENTS.md` § Canonical vocabulary gives a constant — `SPAN` for an EMA, `SMOOTHING_PERIOD`
for a Wilder recursion, `LOOKBACK` for a real rolling window — and it names the mechanics, not the
number: the number lives in the term of the catalogue record and nowhere else. A parameter carried
by a catalogue term is the descriptor's own and is never copied into a named constant; a constant
with a unit names a quantity the experiment fixes outside the catalogue
(`WARMUP_TOP_TIMEFRAME_BARS`, `ATR_WILDER_SMOOTHING_PERIOD_BARS` of the label).

A term is written in the record as `("<indicator>", <parameter_bars>)` on the default series
`close`, `("<series>", "<indicator>", <parameter_bars>)` on another series, or `("<series>",)` for
a bare series. Its name follows: a bare series is its token (`close`); an indicator on `close`, or
with fixed inputs, is the token glued to its parameter (`ema20`, `atr14`, `range_position20`); an
indicator on another series takes the series as a prefix (`log_volume_zscore50`, `volume_sma20`).

## Feature definitions

A **feature definition** composes terms of **one** timeframe with operators from a closed list,
left to right:

    definition = [ normaliser "_" ] term { "_" operator "_" term }
    term       = series | [ series "_" ] indicator parameter
    operator   = minus | over            (difference; ratio, 0 where the denominator is 0)
    normaliser = centered                (a bounded term mapped to [-1, 1] from its indicator's own
                                          `output_range`: (x − mid) / half, so RSI's 0 to 100 gives (x − 50) / 50)

`ema20_minus_ema50_over_atr14` reads: EMA(20) minus EMA(50), over ATR(14) — three terms, one
timeframe, two operators. `close_minus_sma50_over_atr14` reads: close minus SMA(50), over ATR(14)
— the bare series is written, because it is a term, not the input of an indicator. A definition
never mixes timeframes; its range is stated in its record (`range`: dimensionless, bounded, > 0).
The operators and the normalisers are `OPERATORS` and `NORMALISERS` in `catalogue.py`, each beside
its kernels; `catalogue.py` evaluates a record by folding its terms through them and nothing else,
so what the record says is what the column holds. A normaliser is written on a definition of one
bounded term and reads that indicator's `output_range`; on an unbounded one the lookup fails, which
is the whole check. A register of the taxonomy — the indicators, the operators, the normalisers —
is a dict of records keyed by token, kernel first, even when the record holds one fact: the shape
is the convention, not the fact count, so the first new invariant is a key rather than a second
table. `SERIES_KERNELS` is not one of them: it is the dispatch table of the one series that is not
a bar column.

## Features

A **feature** is a definition aligned to the decision grid: `<definition>_<timeframe>`, the value
of the definition on the last closed bar of that timeframe at the decision
(`indicators.asof_index`). The suffix is the timeframe of **every** term in the definition. The
decision timeframe, the alignment and the label horizon are experiment constants and never appear
in a name.

    centered_rsi14_1h                 close_minus_sma200_over_atr14_4h
    log_volume_zscore50_15m           zscore20_15m

The feature id is the column of X and the key of every importance. A feature parquet's columns
carry no timeframe — the file name carries it, in slots
(`module_skills/skill_sorting_files_naming_standard.md` § The timeframe slot standard) — so a
stored column reads `centered_rsi14` while its importance key reads `centered_rsi14_1h`.

Reserved, not written today: a cross-timeframe definition would carry a timeframe on every term
and no suffix — `close_15m_minus_sma200_4h_over_atr14_4h` — and be composed on the decision grid
after each term is aligned. Until one exists, cross-timeframe relations stay strategy rules
(`module_ml/skills/methodology_ml.md` § 9).

## The catalogue and the feature set

The **catalogue** is the register of feature definitions the repository can compute, each with the
timeframes it is offered on: `FEATURE_CATALOGUE` in `module_features/config.py`, one record per
definition — its terms, operators and normaliser, its range, the timeframes offered, and whether it
belongs to the default set. The catalogue is drafted (source, like the rest of `config.py`); the
column set of a timeframe's parquet is the catalogue restricted to that timeframe
(`catalogue_columns`). As of this commit the catalogue holds eight definitions on twenty-two
columns; the table with histories and warm-ups is `methodology_features.md` § The catalogue.

One record of `FEATURE_CATALOGUE`, field by field:

| field | required | what it holds | what fails when it is wrong |
|---|---|---|---|
| `terms` | yes | a tuple of terms — `("<indicator>", <parameter_bars>)` on the default series `close`, `("<series>", "<indicator>", <parameter_bars>)` on another series, `("<series>",)` a bare series; the first term names the definition and, through its indicator's `output_range`, is what `centered` reads | an indicator or series outside `INDICATORS` and `SERIES_KERNELS` is a `KeyError` in `catalogue.py` |
| `operators` | when there is more than one term | one operator of `OPERATORS` between each pair of terms, one fewer than the terms; `zip` folds them, so a missing operator silently drops the terms after it from the computation while the name still lists them | a name that says more than the column computes |
| `normaliser` | no | one of `NORMALISERS`, applied last; `centered` reads the first term's indicator `output_range` | a first term without an `output_range` under `centered` is a `KeyError` |
| `range` | yes | the words the page shows for the definition's range; `status.py` reads it with no default | `features-status` fails on a record without it |
| `timeframes` | yes | the tokens of `HIERARCHY_TIMEFRAMES` the definition is offered on — the whole hierarchy or a subset, § Scope nesting deciding which | a token outside the hierarchy has no bars to read |
| `definition_in_default_set` | yes | `True` puts the column into every asset's X where no feature set is promoted — a different experiment; `False` offers it to the search alone | — |

A **feature set** is one asset's selection from the catalogue, per timeframe:
`<TICKER>_feature_set.json`, written only by the promotion stage of `module_ml` and never by hand —
a choice, not a derivation, and tracked, because the asset's parameters are tuned for it. No file = the default set, the definitions marked
`definition_in_default_set` on every timeframe they are offered on
(`DEFAULT_FEATURE_COLUMNS_BY_TIMEFRAME`) — the fifteen columns of the frozen experiment, in the
order it stacks them. The order is load-bearing: the model samples columns by position, so the
default definitions lead the catalogue in that order. How a set is searched and promoted is
`module_ml/skills/methodology_ml.md` § 4.

The strategy reads one definition on every timeframe whatever the set holds —
`TREND_GATE_FEATURE_DEFINITION`, the first of the catalogue — because the hierarchy gate is a
strategy rule, not a feature the model chose.

## Scope nesting — one level, one domain of time

Every parameter has an effective history: `bars × timeframe`. A window's effective history is the
window; a recursion's is its span or period — the bars carrying most of the weight, about 86 % of
an EMA's and 63 % of a Wilder's — and its settling is the warm-up. Effective histories are derived
and shown (`definition_effective_history_hours`; the catalogue block of
`store/status/features_status.json`), never written into a name. The catalogue keeps the effective
histories of adjacent levels nested: **the longest effective history offered on a level stays
shorter than the shortest offered on the level above.**
A 200-bar average on 15m spans fifty hours — a 4h-domain quantity fitted with four times the
parameters, which is how a level smuggles in another level's regime. So `sma200` is offered on
`4h` only; `sma50` on every level. Today: 15m at most 12.5 h, 1h at least 14 h; 1h at most 50 h, 4h
at least 56 h. The catalogue author decides what to offer; the importance tables tell what it was
worth.

## Warm-up — a literal, and what each term needs

The warm-up of the research window is an experiment constant, `WARMUP_TOP_TIMEFRAME_BARS = 200`,
in bars of the top timeframe of the register; `WARMUP_END_MS` follows from it, and the first
decision of every asset sits there. What each term needs is derived and shown beside it —
`term_warmup_bars`, `definition_warmup_bars`: four spans for a recursion, the lookback for a
window — so a definition whose term needs more than the experiment grants is seen before it is
committed. It is not asserted from the table: the one guard is the finiteness assert of
`catalogue.build_catalogue`, which stops the stage when a value inside the research window is not
finite. Changing the literal moves the window, the labels and every artifact, F5 included — a
different experiment, decided by a hand and recorded by the commit.

The boundary is inclusive: a window of n bars is finite from its n-th bar, `asof_index` takes the
last bar closed at or before the decision, and the first decision falls exactly on the close of the
200th top-timeframe bar. `sma200` on `4h` is finite from the first decision with no slack.

## Migration of the frozen contract

| before | after | why |
|---|---|---|
| `range_position_20` | `range_position20` | parameter glued to its indicator, one rule for every term |
| `log_volume_zscore_50` | `log_volume_zscore50` | same rule; the series prefix stays |
| `ema20_minus_ema50_over_atr14`, `centered_rsi14`, `atr14_over_close` | unchanged | already read off the grammar |

A rename changes parquet column names and importance keys; the model is invariant to names, so
the search result and the strategy report do not change by a byte.

## Never

`feature_3`, `f_rsi`, `rsi_14`, `sma_200` (a separated parameter), `trend_4h` (a category as a
name — `trend`, `momentum`, `volatility`, `structure`, `activity` name what a reader thinks a
column measures, and the importance tables say what it measured), `rsi14_240m` (a history as a
timeframe), `sma800_15m` for a 4h quantity, `rsi14_1h_btc` (an asset in a name), `bb20` (an
abbreviation the register does not hold — the computation is `zscore20`; the trade's label
Bollinger %b lives in the glossary), `atom` or `molecule` as an identifier (the words of this
skill's prose; the identifiers are `term` and `feature definition`), `palette`, `family` for a
definition.
