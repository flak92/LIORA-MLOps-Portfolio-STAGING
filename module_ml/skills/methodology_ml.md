# Methodology — the research layer on the 1-minute series

Per asset, independently, and all of it on one market object — the canonical
research series: the feature catalogue of `module_features` as X — the fifteen
columns of the default set until a promotion — a triple-barrier label resolved
on the canonical 1-minute path, a purged walk-forward protocol
with Optuna hyper-parameter search, a historical final out-of-sample fold, and a
top-down gated strategy evaluation. The experiment is described by its research
window and seed. The guards in the code are the mathematics' own — the seven
named in `AGENTS.md`; *The repository shows the destination, not the road*.

## 1. The nine rules the code implements

1. `X` is a function of **closed** historical OHLCV only.
2. The decision is taken at a 15m bar close; **execution happens one minute later**.
3. `Y` comes from the **canonical research series** only — the same object as `X`.
4. `Y` is a first-touch triple barrier on the 1m path; **ambiguity is not a class**.
5. Overlapping labels carry **average-uniqueness** weights, measured on the
   population that uses them.
6. A training event may **not cross the start of its OOS block**.
7. HPO, the entry edge threshold `τ` and, once a set is promoted, the feature set
   see **F2–F4 only**.
8. **F5 changes no decision** — not a feature, not a hyper-parameter, not the
   entry edge threshold, not a rule.
9. PnL is **linear fixed-quantity research PnL on canonical prices**, with an
   explicit cost and without funding.

Everything below is these nine rules written out.

Why this shape: the label is a **decision indication**, not a price forecast —
the triple barrier [4] asks "which barrier does the market touch first from
here: profit, stop, or neither within the horizon?", which is exactly the
question a rule-based exit answers. Tree ensembles are the strongest
general-purpose learner for tabular financial features [3][9], short-horizon
crypto predictability from technical features is documented in [1][2], and the
top-down multi-timeframe gate follows the classic triple-screen hierarchy
[10]. The protocol as a whole is built against backtest overfitting [8]:
parameters frozen before the first run, and selection statistics kept strictly
apart from the final report.

## 2. One series, one object

```
market source A ──┐
                  ├── canonical 1m series (M) ──┬── 15m / 1h / 4h bars ──► X   (M up to t)
market source B ──┘                             │
                                                └── triple barrier ─────► Y   (M after t)
X + Y ──► purged walk-forward ──► XGBoost
                                      │
                              class probabilities
                                      │
                             fixed strategy rules
                                      │
                            canonical research path
                                      │
                                 equity / PnL ──► monitoring
```

The providers end at the ingest boundary. What crosses it is one continuous
series whose every candle is a real observation of one of them (bar an explicit
forward fill), and the research layer studies that series and nothing else:

```
X_t = f(M_{<=t})        Y_t = g(M_{t+1 : t+H})        M = canonical series
```

Features and target therefore describe the same canonical research object by
construction, and nothing here simulates trading on a named exchange: it
simulates a strategy on a canonical market model, with the costs stated.
`module_data/skills/skill_candle_canonicalisation.md` § 5 and § 6 carry the construction rule and why verbatim candles
beat an average.

## 3. Time semantics

```
… ─┤ 12:45 ── 15M bar ── 13:00 ├─ 13:00 ── 15M bar ── 13:15 ├─ …
                                ▲ t_d = decision_ts = 13:00
features: bars with close_ts <= 13:00  (15M 12:45–13:00, 1H 12:00–13:00, 4H 08:00–12:00)
entry:    t_0 = 13:01, on the first observed trade of that minute — its OPEN
event:    [t_0, t_v) = [13:01, 17:01)  — the barrier examines minutes 13:01 … 17:00
```

`t_0 = t_d + 1 min` is the **one-minute decision-to-entry latency assumption**:
a signal computed at the close of a bar cannot be filled at that same close.

`t_0` names a one-minute bucket, not an instant. **Entry occurs on the first
observed trade of the minute beginning at `t_0`, and its price is that minute's
`open`** — which is what the open of a 1m bar is. If the minute contains no
trade there is no entry. The exact intra-minute execution time is unobserved at
1-minute resolution, and `volume(t_0) > 0` is not future knowledge used to buy
at an earlier price: it is the statement that the trade whose price is `open`
happened at all.
`event_end_ts` is the **exclusive** end of the event, which is what makes the
purge rule exactly `event_end_ts <= oos_start` — an event ending at the first
minute of the OOS block does not overlap it.

Higher-timeframe features come from the last **closed** bar of their timeframe
(`asof_index`: `searchsorted` on close times, causality asserted in code, not
assumed). Bars are exact UTC-aligned aggregations of the canonical 1m series
(O first, H max, L min, C last, V sum; `arg_min` / `arg_max` by timestamp for
determinism).

## 4. Features — the catalogue, and the feature set per asset

The features are `module_features`'s: the names are
`module_features/skills/skill_feature_taxonomy.md`, the definitions, their
histories and their warm-ups `module_features/skills/methodology_features.md`,
and neither is repeated here. The catalogue holds eight feature definitions on
the timeframes of the register, twenty-two columns; every asset's parquets carry
all of them.

What the model sees is the asset's **feature set**: the definitions marked as
the default set on every timeframe they are offered on — the fifteen columns of
the frozen experiment, in the order it stacks them — until a promotion writes
`<TICKER>_feature_set.json`. The set is chosen per asset, on F2–F4 only, by the
coordinate search below; F5 is evaluated under it and never chooses it.
Warm-up: `WARMUP_TOP_TIMEFRAME_BARS` = 200 bars of the top timeframe —
decision rows before `2021-02-03 08:00 UTC` are excluded everywhere; no NaN
survives the warm-up (asserted, in `catalogue.build_catalogue`).

**The coordinate search** (`make ml-coordinate-search`) is a beam over the
coordinates of a state Θ, run under the profile a hand drafted and the asset's
frozen `best_params`, and selecting on what the strategy realised rather than on
what the model predicted. The coordinates are the asset's feature set, its
barrier geometry — the multiplier its label barriers stand at, the horizon they
stand for, and the take-profit and stop its **trades** leave at — and, in its own
loop, the hyper-parameters. A trial is one whole state: three boosters fitted
before F2, F3 and F4 as § 6 fits them, scored as § 8 scores them, and then the
threshold selection of § 9 on their predictions, which gives the fold's realised
CAGR, its maximum drawdown, its Calmar ratio, its profit factor and its trade
count.

**The goal is the validation path, the unit of robustness is the fold.** The
three out-of-fold equity curves are chained into one walk-forward path — each
scaled by what the folds before it settled at — and `validation_path.cagr`, the
growth rate of that path, is what a move has to raise. A position never crosses a
fold boundary (§ 9's eligibility requires the whole horizon inside the fold), so
the chaining is exact, and a drawdown that begins in December and ends in January
is counted as it happened. The **gate** is separate and is per fold: a move is
considered only where the Calmar ratio of **every** validation fold is higher
than its parent's — no worse, for a move that shrinks the state — and only where
the chosen threshold cleared the trade floor in every fold. The gate has no goal
of its own; it says which moves may be ranked at all, and the ranking is then
`validation_path.cagr`, its Calmar ratio, its profit factor, the smaller state,
the earlier trial. What the gate guarantees is that drawdown **relative to
growth** never worsens on any of the three years; it does not guarantee a smaller
drawdown in absolute terms.

A **round** is `ROUND_SCHEDULE` read in order — a table of (loop, family) pairs,
one line per expansion the round makes, and the search's only notion of what
happens when. Each **family** expands the beam once and is seeded by the beam the
line before it left: the `barrier` loop's trade geometry first and its label
geometry second, because a move of the trade's exit changes neither a fit nor a
prediction and can be scored on the material its parent is still holding, while a
move of the label's geometry writes Y again; then the `feature_set` loop's
forward move — every state with one more admitted column, in timeframe order and
catalogue order — and its backward move — every state with one column fewer,
never the last of the set; then the `hpo` loop's one study. A profile searches
the loops it names and the round skips the rest. The beam keeps the best
`COORDINATE_SEARCH_BEAM_WIDTH` **distinct** qualifying children of each family;
two parents can reach one state, and it is one member. A round that keeps nothing
is convergence — `search_converged` — and the state it stops at is
*coordinate-wise locally optimal*: no single legal move improves it. That is not
a global optimum and the file does not claim one.

A state scored once is looked up, never fitted twice, and no booster is kept.
Two files hold what the search knows, and the split is what keeps its own record
proportional to what it learns: `<TICKER>_coordinate_search_trials.jsonl` is the
ledger — one scored state a line, appended, never rewritten, so writing a trial
costs that trial and not the trials before it — and
`<TICKER>_coordinate_search.json` is where the search stands at a round
boundary, written at the top of each round and nowhere else, so its size does not
grow with the search at all. It names trials and holds none of their numbers: an
entry of `path` is the round, the loop, the family, the move, the beam and the
index of the trial it landed on, and a proposal is its rank and that index. Every
reader — `ml-status`, the terminal, the promotion — reads a trial's columns, its
geometry and every number measured on it off its line of the ledger, so a number
stands in one file and two files cannot disagree about it. The round's own work follows that one write, so the
one call leaves both the state a round starts from and the state the last round
left, and the file exists before the ledger's first line: every line the ledger
holds has a state that owns it. That is a guarantee of the order the loop is
written in, not a property of where a run happens to stop. An interrupted run
resumes at the top of the round the state records, the ledger lines that round
already wrote being cache hits — during the baseline trial as much as at a
boundary, because there the state is on disk and the ledger has not been created
yet. A finished run is read, not rewritten. The state's `inputs` — the window
with its warm-up and seed, `best_params`, the catalogue's columns, the asset's
own state, the profile and the selection the experiment froze — are the one copy
of other files' content an artifact carries, compared by equality when the stage
is rerun and again by `ml-status`, which publishes `inputs_current`. The
selection is in there because flipping the objective is a different experiment,
not a different mood: without it a rerun under the other objective would resume
this one's trials under rules they were not scored by. A promotion, a retuning,
a catalogue change or an edited profile leaves a recorded search describing a
state that has gone, and the page then states that instead of comparing against
a baseline it no longer has.

**What a round costs is a function of the hyper-parameters it is measured under.**
The numbers below are BTC with a beam of three, all three loops and the whole
catalogue admitted — the search that converged in two rounds and 59 scored
states, 250.5 s in all — under

```
max_depth 3 · num_boost_round 100 · eta 0.2537 · min_child_weight 37
subsample 0.7993 · colsample_bytree 0.5780 · lambda 0.2051 · alpha 0.01307
```

which is a small model: depth 3 and a hundred rounds fit in about two seconds a
fold, so `make ml-hpo` is ten seconds and `make ml-all` twenty-four. A state's
cost is three such fits plus a replay of the threshold grid, and the fits are the
part that moves: under a depth-8, thousand-round point the same round is hours,
not minutes. Read the table as a shape, not as a duration, and re-measure it
whenever `best_params` moves:

| round | loop / family | children | seconds | s / child |
|---|---|---|---|---|
| 1 | `barrier` / trade | 4 | 9.3 | 2.32 |
| 1 | `barrier` / label | 4 | 18.3 | 4.56 |
| 1 | `feature_set` / forward | 7 | 32.1 | 4.59 |
| 1 | `feature_set` / backward | 15 | 66.9 | 4.46 |
| 2 | `barrier` / trade | 3 | 12.3 | 4.10 |
| 2 | `barrier` / label | 4 | 18.6 | 4.65 |
| 2 | `feature_set` / forward | 8 | 31.7 | 3.96 |
| 2 | `feature_set` / backward | 14 | 61.5 | 4.39 |

A child that only moved the trade's exit costs **about half a full state, not a
tenth**: three fits are saved, but the threshold grid — 61 points over three
folds — is replayed either way and is what a child of that family mostly is.
Under a larger model the same child would be far cheaper than half, because the
fits it skips would then dominate; half is the figure for a model this small, and
it is the conservative one. The `hpo` loop appears in neither round because its
study kept nothing: its one candidate starts from the point the state already
holds, and here that point won.

**One row, one schema.** A trial's row carries the whole of Θ and every quantity
measured on it — each fold's skill, Calmar ratio, CAGR, drawdown, profit factor
and trade count, and the path they chain into — under one set of key names, and
the selection reads some of them. The model's own skill is among the measured and
among the reported; nothing selects on it. There was for two commits a second
objective that did, and a constant that chose between them: it existed to prove
that the refactor of the search changed no number, it proved it, and it is in the
history rather than in the code. Keeping a branch alive for a token with one
value is how the branch nobody runs stops being true.

**Why the resume was written at a round boundary, and not sooner.** The first
implementation moved `champion_trial_index` and the research path inside the round, and
wrote the state file after every scored trial, so a run stopped with Ctrl-C
resumed its round from the beam the round had already reached and appended each
accepted expansion a second time — 61 scored states where an uninterrupted run
scored 59. The round is the unit of resume precisely because a replay must begin
where the interrupted run's round began; both quantities now move only when the
round ends, and the gate that caught it is the one that compares an interrupted
run with an uninterrupted one byte for byte.

**What a loop drew, against what it kept.** `trial_count_by_loop` is each loop's
whole exposure, not the part that survived: for a loop that enumerates a grid it
is the ledger's lines, and for the `hpo` loop it is every point the sampler drew
in every study it ran, pruned and completed alike — the study is handed no point,
so there is nothing to subtract. The two are added once, by the search, at a round
boundary; `status.py` and the terminal copy the number and neither recomputes it,
because two readers adding the same two things is two places for them to disagree. The two are added where the snapshot is composed,
so the page and the terminal read one number and do no arithmetic. Without it the
`hpo` loop is invisible whenever it keeps nothing: it offers at most one candidate
per beam member per round and none at all when the incumbent wins, so a search
that drew a study on every member of every round can leave no trace of having
searched at all, and the multiple-testing exposure a proposal should be read
against would be understated by exactly the points it cost the most to draw.

The proposals are the states a hand may promote: every trial no validation fold
scores below the state the search started from, by the ranking above, and the
champion the search accepted first among them.
A state worse on any validation fold is never proposed, so the default
`PROPOSAL=1` promotes the search's own answer. The model's own skill is reported
beside them and was not selected on. A promotion
(`make ml-coordinate-search-promote ASSET=<TICKER> PROPOSAL=<n>`, one asset at a
time, never fanned out) copies a proposal's columns into
`<TICKER>_feature_set.json` and its barrier geometry into
`<TICKER>_barriers.json` — those and nothing else; the commit history is the
record of every promotion — and reruns the chain, `ml-hpo` included, so the
promoted state is re-tuned, its realised result differs from the search's, and
the next search starts from trial 1. The same proposal promoted twice changes
nothing.

Selection overfitting is bounded and exposed, never absent: a move is accepted
only by every one of three independent years, under a trade floor that keeps a
fold's CAGR and Calmar from standing on a handful of trades, the catalogue is
small, and the trial count — in all and per loop — stands on the page beside
every proposal. Two things are worth saying plainly rather than guarding
against. The objective is now a strategy number measured on 30 to a few hundred
trades a fold, where the model's own skill stood on some 10⁴ decisions, so it is
the noisier quantity; the per-fold gate and the floor are what hold that in
check, and the skill is reported beside it so a state that wins on CAGR while
losing skill is visible in `path[]` by eye. And a move of the label's horizon
changes the supervised population itself — a longer horizon drops more of each
fold's tail and moves the purge — so parent and child are scored on row sets that
differ at the edges; the difference is bounded by the horizon and the purge
width, the comparison is still made on the same calendar window and the same
capital, and that is a property of the coordinate rather than an accident of the
code.

**The warm-up is read off the catalogue, not written beside it.** Every feature
column is evaluated only after `WARMUP_TOP_TIMEFRAME_BARS` bars of the top
timeframe, and that number is `max(definition_warmup_bars(d))` over the catalogue
rather than a constant a hand keeps in step. Written down it was a number to
remember: a definition with a longer memory than the one it was set for is
evaluated before its own value has settled, and nothing says so, because the rows
are there and finite. Today the widest are `ema50` (four times fifty) and `sma200`
(one times two hundred), so the derived value is 200 — the number that had been
written. `catalogue.py` asserts that the contract it writes covers its own widest
definition, which cannot fire while the value is derived and fires loudly the day
someone writes it back by hand.

## 5. Labels

Triple barrier [4] on every 15m boundary after the warm-up. Entry
`P₀ = entry_price = canonical 1m open(t_0)`; horizontal barriers
`P₀ ± m × ATR14` of the last closed **canonical** 1h bar; vertical barrier the
asset's horizon, `"4h"` = 240 minutes = 16 × 15m bars by default. Both are
coordinates of § 4's search and are promoted into `<TICKER>_barriers.json`; the
frozen defaults `ATR_BARRIER_MULTIPLIER` and `LABEL_HORIZON` are what an asset
holds until one is. Resolution walks
the canonical 1m path: the first minute whose high touches `upper_barrier`
gives `y = +1`, whose low touches `lower_barrier` gives `y = −1`, neither gives
`y = 0` with the exit at the close of the last event minute.

**A touch requires a trade.** `volume = 0` means no observed trade in that
minute, so both hit conditions are gated on `volume > 0`. Whether such a minute
is a provider candle that printed nothing or a synthesised continuity row is a
provenance question, answered in the canonical table and in
`module_data/skills/skill_candle_canonicalisation.md`,
not here:

```
upper_hit = (volume > 0) & (high >= upper_barrier)
lower_hit = (volume > 0) & (low  <= lower_barrier)
```

**The horizon travels as a duration token and becomes a number once.**
`HORIZON_TOKEN_MINUTES` maps `"1h" … "1d"` to minutes and
`dataset.load_barriers()` resolves the asset's token there and nowhere else, so
a search that moves the coordinate moves one number. Four places compute with
that number, and each is handed it:

| reader | what it decides with the horizon |
|---|---|
| `labels.label_events()` | which decisions are labelled at all — the grid keeps only those whose whole horizon fits inside the research window |
| `labels.triple_barrier()` | how far down the 1m path a walk goes, and where a vertical exit is marked |
| `validation.scoring_set()` | which supervised rows a fold scores — those whose maximum horizon fits the block, decided at t₀ |
| `strategy.signals_for_fold()` | which entries are eligible in a fold — the same test, on the trade's side |

`validation.training_set()` is **not** among them: the purge is
`event_end_ts <= oos_start`, and `event_end_ts` is a column of Y that already
carries the horizon the labels were written with. A fifth reader is prose —
`status.py` states the horizon and the tail it costs in `<TICKER>_README.md`.
`LABEL_HORIZON_MS` had no reader left once the four took a parameter and is gone.

If the vertical-barrier minute contains no trade, its canonical close is a
**last-observed-price mark** used by the research simulation, not an observed
execution fill: the volume gate applies to barrier touches and to the entry,
not to the mark that closes an unresolved event.

A minute touching **both** barriers leaves their order unknowable from OHLC, so
the row is `label_valid = false` — never relabelled `0`; the `y` column carries 0 for such a row because no barrier ordered the touch, and `label_valid` is what removes it from every population — `y` is never read without it. Ambiguity is a missing
observation, not a third outcome.

**Two conditions that look alike and must not be merged:**

```
entry_observable = volume(entry_ts) > 0   known at t_0        MAY gate an entry
label_valid      = event classifiable     known afterwards    NEVER gates an entry
sample_valid     = entry_observable & label_valid             the supervised population
```

Whether the entry minute traded at all is visible at the time, so the strategy
may refuse it. Whether the event will resolve ambiguously is not, so using
`label_valid` as an entry condition would be look-ahead: a signal whose event
later turns out ambiguous **is a trade**, settled at the barrier adverse to the
position.

Supervision uses both. An unobservable entry gives `P₀ = open` of a minute that
printed no trade, so its barriers are anchored to a quote nothing traded at: not an executable decision and not a sound
measurement. `sample_valid` therefore governs the training rows, the HPO
objective and the classification metrics — and, through them, the populations
the uniqueness weights are measured on — while the strategy gates on
`entry_observable` alone.

Sample weight = **average uniqueness** [4, ch. 4]: the mean over the event's
minutes of `1 / (concurrently open events)`, exact via prefix sums. It is the
XGBoost sample weight, with no additional class re-weighting. Rows whose
vertical barrier would cross the research end are dropped.

**The weight is a property of a population, not of an event**, so it is
measured where it is used, in `validation.py`, and never stored in `Y`.
Concurrency is counted inside the population that carries the weights: the
**purged training rows** of a fold, and separately the **scored rows** of that
fold. Counting it once over the whole research window would let a purged
event — or an event inside the block being evaluated — raise the concurrency
of a training row, so the future would help decide how much that row counts.
The training weights therefore feed `model.fit` and the class prior, the
scoring weights feed the log-losses of that same fold, and neither can be
used in place of the other.

`<TICKER>_label_events_ss-15-hh-dd-MM.parquet` also carries the prices the backtest needs —
`entry_price`, `upper_barrier`, `lower_barrier`, `exit_reference_price` — so the
strategy replays exactly the event that produced the label instead of
recomputing it.

## 6. Folds — WARMUP | TRAIN | PURGE | OOS | final holdout

```
2021-01-01     warmup_end     2022-01-01     2023-01-01     2024-01-01     2025-01-01          2026-08-26
|-- WARMUP --|----- F1 -----|----- F2 -----|----- F3 -----|----- F4 -----|-------- F5 ---------|
                                                                         (final holdout fold)
Fold 2:  TRAIN = F1            | PURGE | OOS = F2
Fold 3:  TRAIN = F1–F2         | PURGE | OOS = F3
Fold 4:  TRAIN = F1–F3         | PURGE | OOS = F4
Holdout: TRAIN = F1–F4         | PURGE | F5   (frozen params, frozen threshold)
```

**Purge** keeps a training row only if `event_end_ts <= oos_start`. Because
`event_end_ts` is exclusive, that inequality *is* "no overlap" — no artificial
gap is added, since a gap wider than the event horizon removes information
without removing leakage. A classical embargo after the evaluated block
[4, ch. 7] is not required in forward chaining: no training observation lies
after the OOS block.

**Scoring** mirrors the purge at the other boundary: a fold scores only the
supervised rows whose maximum horizon fits inside the block
(`entry_ts + the horizon <= oos_end`), decided at t₀ — the real
`event_end_ts` is path-dependent, so admitting by it would let the future
choose the scored population.

**F5 is the historical final holdout fold.** The contract is a sentence, not a
guard, and it is about selection rather than counting: *F5 never participates
in feature definition, hyper-parameter selection, entry-edge-threshold
selection or strategy-rule selection.* F2–F4 carry the data-driven selection —
the hyper-parameters, the entry edge threshold and, once a set is promoted, the
feature set; the barrier width, the horizon and the cost are frozen a priori.
F5 is evaluated against them — a promotion is decided on F2–F4 before F5 is
seen under the new set, and F5 is report-only. Recomputing F5 deterministically — after a refactor, on another
machine, in a later run — changes nothing, because nothing is chosen by
looking at it. What the contract forbids is the loop: read F5, change the
model, call the same fold out-of-sample again.

## 7. Hyper-parameter search

Optuna TPE (`seed = 42`), 20 sequential trials, in-memory study. The objective is
the quantity the search selects on: the CAGR of the validation path at the
threshold § 9's rule would pick, maximised.

**Ten of the twenty are the sampler's random start.** TPE fits its two densities
only once it holds `n_startup_trials` trials — completed and pruned alike, in
this Optuna — and draws at random until then, so a study of ten trials or fewer
is a random search under the sampler's name and reports as a TPE one. The startup
count is `HYPERPARAMETER_SEARCH_STARTUP_TRIAL_COUNT = 10`, written in
`config.py` rather than inherited from the library: a number that decides how the
experiment searches is the experiment's, and a default that moves with a version
bump is not a frozen method. The modelled trials are the ones past the startup count. Both counts were
chosen when the method was frozen; before that the file carried three trials and
said so.

**The sampler's remaining internals are Optuna's, and are pinned as such.** The
quantile that splits good from bad, the number of candidates the acquisition
draws, the prior and its weight, the clipping, the endpoints, `multivariate`,
`group`, `constant_liar` — none of them is written here, and one of them is a
function rather than a number, so copying them into `config.py` would fork the
library's internals into this repo and let the fork drift. They are pinned
instead by `==` in `requirements.txt`. A version bump therefore changes the method
and re-bases the hash in § 12 — it is never a silent drift, which is the property
that was wanted.

**The ledger is a file of this repository, and it is byte-deterministic.** Every
point every study drew is one JSON object on one line of
`store/trials/<TICKER>/<TICKER>_hyperparameter_search_trials.jsonl`, appended by
`dataset.append_jsonl` and never rewritten — the technique the coordinate search's
own ledger uses, and the whole of what a ledger needs. A line carries where it was
drawn — `hpo` for the stage, `coordinate_search` for the search's loop, the module that ran the study — the round when a loop drew it, the study's
place in the file, the trial's place in the study, its state, the point the sampler
drew and what the trial left. It carries **no run id, no timestamp and no host
name**, which is the property that matters: two studies over an empty store leave
the same bytes, so `rm -rf store/trials/<TICKER>` followed by two runs is a
comparison and not an anecdote. A record that cannot be compared is a note; this one
is evidence. The search's own `hpo` studies reach it too — until it was this file
they reached nothing at all, and the only trace of them was a count.

**A pruned trial and a completed one do not share a ledger key.** A completed
trial carries `cagr_validation_path`, the chained path's growth rate at the
threshold the rule chose, and `admissible`, whether that threshold beats the
champion on every fold. A pruned one carries neither, and carries `pruned_at_fold`
instead. Both carry `admissible_threshold_count_by_fold`, one count per fold the
trial reached — what the gate saw, written down rather than inferred from the fact
that the trial survived. A pruned trial's last count is zero and a completed one's
is not, which is the whole of the gate's story on one line.

**The stage draws no point to start from.** It is a function of X, Y and the
frozen constants, so `<TICKER>_parameters.json` is a function of the raw store
and this code and never of its own last value: a derived artifact that read
itself would make the chain a fixed-point iteration, and two runs of `ml-all`
would not have to agree until it settled. A point to start from belongs to the
search's `hpo` loop below, where the round's champion is an input the state file
records in `inputs` and the comparison is against a state the search itself
holds. Space: `max_depth` 2–6, `eta` log 0.01–0.3, `min_child_weight`
1–50, `subsample` 0.5–1, `colsample_bytree` 0.5–1, `lambda` log 0.1–10,
`alpha` log 0.01–1, `num_boost_round` 50–600 step 50. Fixed:
`multi:softprob`, `num_class = 3`, `tree_method = hist`, `nthread = 1`,
`seed = 42`, no early stopping — which is why `num_boost_round` reaches 600 and
not 100: it is a tuned coordinate, and at the bottom of the `eta` range a
hundred rounds cannot converge, so a short ceiling would leave the low end of
`eta` unreachable rather than merely unchosen. The barrier geometry, the costs and the
entry-edge-threshold grid are **never** in the space: the geometry is a
coordinate of § 4's search and is promoted, not tuned. The
`hyperparameter_search_result` section of `<TICKER>_parameters.json` keeps the
chosen point, its value under the frozen objective and the trial count.

Inside a coordinate search the study is itself a coordinate — one candidate per
beam member, drawn on that member's own X and Y. It cannot answer worse than the
member it ran on because a candidate has to beat it: the guarantee is the gate's.
The study used to be handed that member's own parameters as its first trial, and
that trial is stopped by the gate after one fold — equality does not beat a strict
inequality — so it was a fit spent on a point that could not be a candidate, and a
trial pruned before it reports anything tells the sampler nothing. **One** gate stops a trial early, and it is the
state gate's own condition read one fold at a time: after each validation fold, the
thresholds at which every fold so far clears the trade floor **and** beats the
champion's Calmar there. The set only shrinks as folds are added, and the child the
search would keep needs one threshold inside it over all three folds, so a trial
whose set has gone empty cannot produce one however the folds it has not run land.
Nothing admissible is discarded. The count after each fold is written into the
ledger whether or not the gate is armed, so what the gate saw is readable and not
inferred.

**What stood here before asked a different question.** Two gates, each on the best a
fold could still reach over the whole grid — an upper bound, on the Calmar and on the
growth rate, read fold by fold and never jointly. Two bounds, each true of *some*
threshold, say nothing about *one* threshold admissible on every fold — and one
threshold is what the state gate needs. The set is that quantity, so the gate now
stops a trial exactly when it can no longer produce a child the search would keep.
Measured on a full search at the new gate: 80 of 80 points stopped, 74 of them after
the first validation fold, against champions whose fold Calmar stood at +5.68.

A correction belongs here, because it was published the other way round. An earlier
measurement reported that the old gates pruned **none** of 76 points. That reading
was wrong, and its cause is worth keeping: Optuna records the last reported
intermediate value as a *pruned* trial's value, and the ledger derived a trial's
state from `value is None`. Every pruned trial therefore wrote itself down as
completed. The gates had been firing all along; the record could not say so. The
state is now read from `trial.state`, which is the only thing that knows it.

Optuna's median pruner is not a gate here either: it compares a trial's best
intermediate value across all of its steps with the median of other trials at one
step, and with folds as calendar years that is not a comparison of like with like.
When every trial of a study is stopped, the loop keeps nothing that round — which is
an answer, not a failure.

**The loop offers the best admissible point, not the best point.** A study's best
trial by value may be one whose chosen threshold does not beat the champion on every
fold; the state gate refuses that child. Offering it meant the loop answered nothing
while holding, further down its own list, a point the gate would have kept — the
trials are read by value, descending, and the first admissible one that beats the
champion's own path is offered. Whether a trial's chosen threshold was admissible is
decided where the sweeps already are, and carried on its ledger line as `admissible`,
so the loop asks the question without refitting anything.

## 8. Classification metric — relative log-loss skill against the training prior

With `y = 0` dominant, a uniform `ln 3` baseline flatters any model that
merely learns the class frequencies. The baseline is therefore the
**uniqueness-weighted class prior of the fold's own training rows**,
`p_c = Σ wᵢ·1(yᵢ = c) / Σ wᵢ`, and the reported numbers are

```
prior_logloss · model_logloss · relative_logloss_skill = 1 − model/prior
```

`relative_logloss_skill` answers one question — does the model add information beyond knowing
how often each class occurs? — and is **what both searches select on**: the hyper-parameter
search minimises the log-loss behind it (§ 7), and the coordinate search accepts a move only
when it rises, or does not fall, on every validation fold (§ 4). Metrics score the
supervised subset of a fold
whose maximum horizon fits inside it — the same t₀-decidable rule that governs
strategy eligibility (§9); predictions cover the full fold.

**Two importances per validation fold**, each of that fold's own booster, none
of the final holdout's: `gain_importance`, XGBoost's total gain per column;
`mean_abs_shap_importance`, the mean absolute SHAP value [12] per column over
the fold's scoring rows and the three classes, in margin space and unweighted,
because it is a property of the fitted function rather than of a population.
They are results, not gates: the page shows their means over the validation
folds, and nothing selects on them.

## 9. Strategy

```
edge = directional_probability_edge = p_long − p_short;  side = sign(edge)
agreeing_trend_timeframe_count =
    #{timeframe ∈ {15m, 1h, 4h} : sign(ema20_minus_ema50_over_atr14_<timeframe>) = side}
enter = |edge| ≥ τ ∧ max(p_long, p_short) > p_neutral ∧ side ≠ 0
        ∧ side = sign(ema20_minus_ema50_over_atr14_4h)
        ∧ agreeing_trend_timeframe_count ≥ 2
        ∧ entry_observable
```

The **model decides the side; the 4H hierarchy gates it**. One unit position
at a time, new signals ignored while in a position, and a signal is eligible
only where its whole horizon fits inside the fold
(`entry_ts + the horizon <= fold_end`) — decided at t₀, never by where the
trade actually ended.

**PnL — one formula.** The simulation applies USDT-perpetual PnL algebra to the
canonical price path: a position held at a fixed
quantity `Q = s · E₀ / P₀` (notional 1× current equity), so PnL is linear in
price, with the cost `c = 0.0006` charged on entry notional and on exit
notional:

```
R      = s·(P_x/P₀ − 1) − c − c·(P_x/P₀)
E_next = E₀·(1 + R)
E_t    = E₀·(1 − c + s·(P_t/P₀ − 1))      mark-to-market while open
```

A short from 100 to 80 returns exactly +20 %, and the path 100 → 50 → 100
returns 0 %. Compounding per-bar returns instead — `Π(1 + s·r_t)` — returns
−100 % on that path; that is the arithmetic this formula replaces.

**A trade leaves where it chooses, not where the label did.** The label stays
symmetric — `entry ± m·σ`, the same on both sides — because that is how a
direction is learned. A trade has its own exit: for a long the take-profit at
`tp·σ` above the entry and the stop at `sl·σ` below it, mirrored for a short,
with the same vertical barrier. Both are found by the same walk down the 1m path
that wrote Y (§ 5), for the entries the gate admits, so "the first barrier
touched" has one definition in this repository and one guard on `volume > 0`. In
code the trade's barriers are the **label's own half-widths rescaled** —
`entry + (tp/m)·(upper − entry)` and `entry − (sl/m)·(entry − lower)` — and not a
σ recovered from one of them: at `tp = sl = m` the scale is exactly one and the
trade's barriers are the label's to the bit, for every `m`, whereas one recovered
σ reproduces the upper barrier and misses the lower by a unit in the last place
on about 2 % of BTC's rows. A position's occupancy runs to the end of the
**trade's** event, so a tighter stop frees the capital sooner, which is the point
of searching the two multipliers at all.

**Fills acknowledge that 1m OHLC hides the tick path.** A take-profit fills at
the barrier. A stop fills at the *worse* of the barrier and the open of the
minute that touched it (`long: min(lower_barrier, open)`, `short: max(upper_barrier, open)`),
which is also how a minute that touched both is settled — the order inside a
minute is unknowable, so the trade takes the adverse side. Without
that rule a bar-based backtest silently assumes every gap fills at the barrier.

**The entry edge threshold `τ` is chosen on F2–F4 only**, by an explicit rule:

```
τ* = argmax_τ  CAGR( E_F2(τ) ⌢ E_F3(τ) ⌢ E_F4(τ) )
     subject to  trades_f(τ) ≥ MINIMUM_TRADES_PER_VALIDATION_FOLD = 30  for every f ∈ {F2, F3, F4}
     ties → the smaller τ
```

where `⌢` is the chaining of § 4: each fold's 1-minute equity scaled by what the
folds before it settled at, so the three years are one walk-forward path and its
CAGR is the growth of one capital through them. It is the **same function** the
stage and the coordinate search both call, so the chain and the search can never
choose a different threshold for the same predictions. The rule reads what each
fold settled at and nothing else: the path's drawdown and its profit factor need
the folds' curves chained, its growth rate does not, and a selection walks
sixty-one grid points.

The trade floor keeps a threshold from winning on three or five trades with an
accidentally high number. If no threshold on the 0.00–0.60 grid meets it, the run
falls back to `τ = 0` and reports
`entry_edge_threshold_constraint_met = false`; the coordinate search refuses such
a state before it ranks it, because its numbers stand at a threshold nothing
qualified for.

**A fold's own numbers, and the path they chain into.** From the same 1-minute
equity a fold reports its CAGR — `final_equity ** (MINUTES_PER_YEAR / minutes) − 1`,
a 24/7 year of 365 days, so F4 being a leap year makes its exponent slightly
under one rather than being idealised away — its maximum drawdown, their ratio as
the Calmar ratio, its profit factor over the trades it took, and its trade count.
The three validation folds chain into `validation_path`, which carries the same
five for the path as a whole. The path's maximum drawdown is at least the largest
of the folds' own, because a drawdown may run across a year boundary; that is the
point of chaining rather than averaging.

**Sharpe and drawdown come from one equity process sampled two ways.** The
backtest writes a continuous 1-minute equity path starting at `E₀ = 1`; the
Sharpe is annualised (`×√(96·365)`) from that path sampled at **15m bar
closes**, starting from `E₀` itself so the first quarter-hour of a fold is not
silently dropped; the maximum drawdown is measured on the **1m** path, also
from `E₀` — a 15-minute sampling would report a 1.00 → 0.91 → 0.99 excursion as
−1 % instead of −9 %. `exposure` is
`Σ(exit − entry) / fold length`. The reported result is
**execution-cost-adjusted PnL, excluding funding**.

**What the chosen threshold was chosen out of.** The selection is a maximum over
the threshold grid, and a maximum reported alone is a number with no spread beside
it: the same score means one thing as the only point that qualified and another as
the best of eleven. `cleared_point_count`, `median_cagr_over_cleared` and
`max_cagr_over_cleared` ride beside it in `<TICKER>_strategy_evaluation.json`, in
every trial row of the search and in `ml_status.json` — three plain statistics of
the grid, with **no correction applied and none implied**. This layer does not
deflate the score, and saying so is the point: the correction belongs to whoever
reads the number, and it cannot be made at all without the population it was a
maximum over. All three are `null` when nothing qualified and the threshold fell
back to the grid floor, which is itself the loudest thing the three can say.

## 10. Artifacts and modules

Per asset in `store/assets_artifacts/<TICKER>/`, twelve files, registered file by
file in `../../module_skills/glossary.md` § Artifacts: the feature layer's contract
`<TICKER>_catalogue.json`, three per-timeframe catalogue parquets, the
label-events and out-of-sample predictions parquets on the 15m decision grid,
two evaluation JSONs, the one parameters file, the feature set and its search
when a hand has run them, and the README. Beside the
manifest, outside it, lies the asset's own database,
`<TICKER>_research_ohlcv.duckdb` — the market object every stage reads. The data
files are regenerable; `<TICKER>_parameters.json`, `<TICKER>_README.md` and,
once a hand has promoted one, `<TICKER>_feature_set.json` are tracked, because
they are what makes the rest readable — and reproducible: the parameters are
tuned for the set they were searched under, so the two travel together — and
none carries a timestamp, so an unchanged experiment reproduces them byte
for byte. Every JSON is canonical (sorted keys, numpy scalars converted) and
carries **only what it computed** — no provenance envelope, no hashes. The
settings a run used are `module_ml/config.py` at the commit that ran it — the
commit is the record, and the parameters file carries only what the search
chose. The experiment is identified once, globally, in
`store/status/ml_status.json`: research window and seed.
Library versions are pinned once, in `requirements.txt`. Runs are reproducible
by construction — fixed seed, `nthread = 1`, pinned versions — and that claim
is not backed by a hash gate, because a gate proves the metadata, not the
mathematics. No booster is persisted: nothing in this repo performs inference,
so the numbers are the product.

Module layout — four runtime modules, in the order the data moves, and
`module_skills`, the canon, whose one sub-module measures the tree and joins no
dataflow of the chain: `module_data` (sources → normalised
raw 1m → one canonical DuckDB per asset) · `module_features` (the bars of the
register and the feature catalogue — `module_features/skills/`) · `module_ml`
(this document) · `module_monitoring` (presentation of what each module measured
about itself and of the dates of the crawler's reports, and the server). Inside `module_ml`: `module_ml/config.py` (frozen
constants of the research layer — the window and the folds its own, the register
and the grid read per asset from the feature layer's contract,
`<TICKER>_catalogue.json`) · `module_ml/validation.py`,
`module_ml/model.py` (pure numpy / xgboost kernels) · `module_ml/dataset.py` (artifact
IO: X/Y loading, canonical JSON, its own parquet writer — twice by extraction, identical in `module_features/dataset.py`) ·
`module_ml/labels.py`, `module_ml/hpo.py`, `module_ml/train.py`, `module_ml/strategy.py`,
`module_ml/status.py` (CLI stages, `python -m module_ml.<stage> --tickers <TICKERS>`) ·
`module_ml/coordinate_search.py`, `module_ml/coordinate_search_promote.py` (the two hand
stages outside the chain, `python -m module_ml.<stage> --tickers <TICKER>`, the
promotion also `--proposal <n>`).
Constant convention: **experiment-semantic constants live in
`module_features/config.py` and `module_ml/config.py`; implementation
constants** (chunk sizes, the equity-curve stride — daily in the artifact,
weekly on the page: seven daily points) **may stay local to their module**. The canonical series is gated where it is read:
`labels.load_research_1m` asserts the full 1m grid inside the research window,
per asset; the ingest stage rebuilds one asset's database at a time.

## 11. Running the layer: one asset per process

Every stage takes `--tickers`, so the chain parallelises the only way an
experiment with frozen thread caps may — **externally**, one asset per
process. `make features-bars / features-catalogue` and `make ml-labels / ml-hpo /
ml-train / ml-strategy` fan out `JOBS` assets at a time, where
`JOBS = max(1, min(cores, available GiB))` is measured at each invocation rather
than written down (the machine this runs on changes size); override with
`make ml-hpo JOBS=2`. `features-bars` fans out with them — one file per process;
`data-ingest` alone stays sequential, because a memory ceiling is per process
and the sum of the concurrent ceilings is what has to fit the host.

Thread caps stay at one — `nthread = 1`, `OMP_NUM_THREADS = 1` — for the
reason `../../module_skills/skill_determinism.md` states. The search is CPU-bound and one asset's
study is sequential by construction, so the wall-clock floor of `ml-hpo` is the
slowest single asset.

Rerun only what a change actually invalidates — the search is the expensive
stage, and most edits do not touch it:

| what changed | what to rerun |
|---|---|
| the canonical series (`make data-ingest`) | everything, from `features-bars` |
| a feature definition offered but not in the default set | `features-catalogue features-status ml-status`, and `ml-coordinate-search` if its proposals are to stay current |
| a feature definition entering the default set | `features-catalogue features-status ml-hpo ml-train ml-strategy ml-status`, and `ml-coordinate-search` likewise |
| a label or barrier parameter | `ml-labels ml-hpo ml-train ml-strategy ml-status` |
| a fold bound or the fold ids | `ml-hpo ml-train ml-strategy ml-status` |
| the research window — both copies, `module_features/config.py` and `module_ml/config.py` | everything, from `features-bars` |
| the search space or the seed | `ml-hpo ml-train ml-strategy ml-status`, and `ml-coordinate-search` if its proposals are to stay current |
| a strategy rule, the cost, the threshold grid | `ml-strategy ml-status` |
| a coordinate search (`make ml-coordinate-search`) | `ml-status` — its proposals reach the page |
| the promoted feature set (`make ml-coordinate-search-promote`) | `ml-all` — run by the promotion itself |
| the monitoring payload | `ml-status` |

This table is the layer's rebuild condition, held in a document a reader applies
rather than in a stage: what decides that an asset's artifacts are stale stays
separate from the stages that rebuild them —
`../../module_skills/skill_pre_aws_solution.md` § The rebuild condition stays
separable.

## 12. What this is, and what it is not

This is a **bar-based research strategy simulation on the canonical market
series, with explicit execution-cost assumptions** — a canonical-market
research backtest. It is not a realistic simulation of trading on any exchange:
1m OHLCV contains no order book, no latency distribution, no partial fills, no
spread, no queue position and no funding payments. Every one of those would
move the result, and none of them is guessed at here.

One boundary belongs to the market model itself. The canonical series can
change provider between two minutes, and the two providers quote a real basis. A single barrier
touch can therefore come from a source switch rather than from the market
moving. That is a property of a constructed market object, not a defect hidden
by it: `source_switch_count` and `rel_divergence` are monitored per symbol
precisely so the effect is visible and countable.

Known limitations: no regime-conditional gating, a per-asset feature set
chosen by the coordinate search (§ 4) rather than learnt, no CUSUM event sampling, no meta-labelling, no fractional
differentiation, fixed costs, unit position sizing. The class distribution is
dominated by `y = 0` (the 2×ATR barrier is rarely touched within one 4H
block) — reported per asset, not resampled.

**One fold can make the search stand still, and on this asset it does.** The state
gate keeps a move only where it is better on **every** validation fold. BTC's
champion stands at a fold Calmar of **+5.68** on F2 with F3 and F4 both negative, so
a move must beat +5.68 and the two negatives at one threshold. Measured: the
hyper-parameter loop drew 80 points across four studies and every one was stopped —
74 after the first fold — and the whole search accepted a single move, `barrier/trade`
in round 1, before converging. The conjunction over folds and one extreme fold
together make a search that is nearly motionless.

That is a property of this geometry, written down and not solved here. Whether the
answer is a different fold measure, a tolerance, or a champion that is not the beam
leader is a question for the research phase — deciding it now would be choosing a
selection rule by the result it gives on one asset, which is the thing this layer
exists to avoid.

**The phase this layer is in.** What is being built here is the correctness of
the machine, not a result from it: every stage has to answer like a calculator —
the same input to the same bytes, no number arrived at by a path nobody can name,
no constant inherited from a library default. Numbers this layer produces now are
evidence that the machine is right, not findings about the market, and nothing in
them is to be read as one. The palette of features and the compute the search is
given are the next thing to grow, on a larger machine and with the cores opened
up; the artifacts worth keeping are made there, once the machine is right. That
is why a count like § 7's twenty is chosen for what makes the method honest and
not for what makes a run short: the run's length is not the constraint this phase
is under.

## 13. References (DOIs resolve)

| Key | Reference |
|---|---|
| [1] | Jaquart, P., Dann, D., Weinhardt, C. (2021). Short-term bitcoin market prediction via machine learning. *The Journal of Finance and Data Science*, 7, 45–66. doi:10.1016/j.jfds.2021.03.001 |
| [2] | Sebastião, H., Godinho, P. (2021). Forecasting and trading cryptocurrencies with machine learning under changing market conditions. *Financial Innovation*, 7, 3. doi:10.1186/s40854-020-00217-x |
| [3] | Gu, S., Kelly, B., Xiu, D. (2020). Empirical asset pricing via machine learning. *The Review of Financial Studies*, 33(5), 2223–2273. doi:10.1093/rfs/hhaa009 |
| [4] | López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley — ch. 3 (triple barrier), ch. 4 (uniqueness), ch. 7 (purged CV, embargo) |
| [5] | Parkinson, M. (1980); Garman, M., Klass, M. (1980). *Journal of Business*, 53(1) — range-based volatility |
| [6] | Amihud, Y. (2002). Illiquidity and stock returns: cross-section and time-series effects. *Journal of Financial Markets*, 5(1), 31–56 |
| [7] | Wilder, J. W. (1978). *New Concepts in Technical Trading Systems* — RSI, ATR |
| [8] | Bailey, D., Borwein, J., López de Prado, M., Zhu, Q. (2014). Pseudo-mathematics and financial charlatanism: the effects of backtest overfitting on out-of-sample performance. *Notices of the AMS*, 61(5), 458–471. doi:10.1090/noti1105 |
| [9] | Chen, T., Guestrin, C. (2016). XGBoost: a scalable tree boosting system. *KDD 2016* |
| [10] | Elder, A. (1993). *Trading for a Living* — triple-screen multi-timeframe hierarchy |
| [11] | Makarov, I., Schoar, A. (2020). Trading and arbitrage in cryptocurrency markets. *Journal of Financial Economics*, 135(2), 293–319 — why `rel_divergence` stays a data-quality signal |
| [12] | Lundberg, S. M., Erion, G., Chen, H., DeGrave, A., Prutkin, J. M., Nair, B., Katz, R., Himmelfarb, J., Bansal, N., Lee, S.-I. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence*, 2(1), 56–67. doi:10.1038/s42256-019-0138-9 — SHAP values of a tree ensemble |
