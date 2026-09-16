# Glossary — one concept, one name

*The repository shows the destination, not the road*: the register confirms; the crawler reads it and gates nothing.
Every concept below has exactly one name in the code, one key in the artifacts
and one label in the interface. Names that are standard
in the field (`fold`, `purge`, `embargo`, out-of-sample, Sharpe) appear as
confirmation; the rest of the concept column states what the name means.

## Validation and folds

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| one chronological segment of the research window — `F1`, the first, is trained on and never evaluated (`module_ml/skills/methodology_ml.md` § 6) | `fold`, `fold_id` | `fold_2` … `fold_5` | `F2` … `F5` | split, period, chunk |
| the segment boundaries | `fold_bounds()`, `FOLD_BOUNDS_MS` | — | — | split_bounds |
| the folds used for the data-driven selection of model hyper-parameters, the entry edge threshold and, once a set is promoted, the feature set | `VALIDATION_FOLD_IDS` = (2, 3, 4) | `validation` | `F2`–`F4` | test folds, CV folds, "the folds that choose every parameter" |
| the fold that is only ever evaluated | `FINAL_HOLDOUT_FOLD_ID` = 5 | `final_holdout`, `final_holdout_fold_id` | `F5 — final holdout (out-of-sample)` | test, test set, locked test, final OOS |
| the evaluated block of a fold, and which one a prediction belongs to | `oos`, `oos_fold_id` | `oos_fold_id` (parquet column) | out-of-sample | test block, test period |
| dropping training events that overlap the evaluated block | `purge` — `event_end_ts <= oos_start` | — | purged | gap, buffer |
| a forced wait after the evaluated block — **width zero here**, forward chaining needs none | — (the field's term, carried by no identifier, because there is nothing to implement) | — | — | cooldown, post-test embargo |
| bars consumed before the first decision is allowed — the experiment's literal, in bars of the top timeframe of the register; what each term of the catalogue needs is shown beside it, never derived into the window | `WARMUP_TOP_TIMEFRAME_BARS` = 200, `WARMUP_END_MS`; `term_warmup_bars()`, `definition_warmup_bars()` | `warmup_excluded_decision_count`; `warmup.top_timeframe_bars`, `warmup_bars` of a catalogue definition | warm-up excluded; warm-up (bars) | burn-in; `WARMUP_4H_BARS` (a timeframe token in the name lies once the register grows) |

## Market object

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| the external minute-bar format the raw store is byte-compatible with | QuantConnect Lean — `module_data/lean.py` | — (the raw tree only) | — | QC, quantconnect-format, `lean` lower-case mid-sentence; a project-cased spelling of its tree |
| the studied series, and the only series below the ingest boundary | `ohlcv_1m_canonical` and its aggregates | — (tables of the asset's own DuckDB; no copy of the series is published) | canonical dataset | fused series, index, blended price |
| which asset a database holds | the file name, `<TICKER>_research_ohlcv.duckdb`, and nothing inside it | `symbol` — a key of data_status.json only | — | a `symbol` column in any table, a `WHERE symbol = …` predicate, a `GROUP BY symbol` |
| the timeframe hierarchy — the experiment's literal, finest first: every timeframe the repository builds from the canonical 1m series, the one definition the bars, the parquets, the catalogue's offered timeframes, the decision grid and the trend gate derive from (`module_features/skills/skill_feature_taxonomy.md` § The timeframe register) | `HIERARCHY_TIMEFRAMES` = ("15m", "1h", "4h"), `module_features/config.py` | `catalogue.timeframes` — `timeframe`, `duration_ms`, `bars_per_day`, `ratio_to_lower`, `slot` | 15m / 1h / 4h | levels, LEVELS, a hierarchy derived from a dict, a second list of timeframes anywhere |
| the timeframe a decision is taken on — the experiment's literal beside the hierarchy | `DECISION_TIMEFRAME` = "15m" | `catalogue.decision_timeframe` | the decision timeframe (the register box) | DECISION_TF, `HIERARCHY_TIMEFRAMES[0]` written where the literal should be |
| how long one bar of a token lasts, and the token's file-name slot — both read off the token: the number and the unit | `timeframe_duration_ms()`, `timeframe_slot()`, `TIMEFRAME_UNIT_MS`, `TIMEFRAME_SLOT_FIELDS`, `TIMEFRAME_UNIT_SLOT_FIELD` — the unit's duration, the five slots of the sorting standard and the field a unit fills; `TIMEFRAME_DURATION_MS` and `TIMEFRAME_SLOT`, the two read off the hierarchy | `duration_ms`, `slot` | — | TF_MS, a duration or a slot written by hand per token |
| the timeframe whose last closed bar sets the barrier width of a label — an entry of the hierarchy, the label's own literal | `LABEL_BARRIER_ATR_TIMEFRAME` = "1h", `module_ml/config.py` | — | — | `"1h"` in a query or an assert |
| a data provider, above the ingest boundary only | `binance` / `bybit`, in `module_data` | `source_venues`, `venues.*`, `source_share_pct_by_venue.*` | Raw source | venue or exchange used below ingest |
| which provider a canonical minute came from | `source`, `source_switch_count` | `source_switch_count`; `source` is a database column, published only as `source_share_pct_by_venue` and the forward-filled count | one share column per provider, named for it, in the tier order of `source_venues` | — |
| a minute with no observed trade | `volume = 0`, `zero_volume` | `zero_volume_bars`; `zero_volume` is a database column | zero-vol | carried-forward price (true only of forward-filled minutes) |
| a synthesised continuity minute | `source = 'ffill'` | `ffill_bars` | ffill | gap, missing bar |
| quality columns that are never features | `binance_valid`, `bybit_valid`, `rel_divergence` | — (database columns; `rel_divergence` is published only as `relative_divergence_p99` / `relative_divergence_max`; `<venue>_valid` is what `invalid_row_count` counts the failures of) | — | signal, feature |

## Event and sample

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| the moment a decision may be taken — close of the 15m bar | `decision_ts` | `decision_ts` | — | signal time |
| the candidate entry minute after the decision — an entry is permitted here, not guaranteed | `entry_ts` | `entry_ts` | — | fill time, first tradable minute |
| the canonical open of that minute | `entry_price` | `entry_price` | — | `p0` as an identifier (`P₀` stays in the equations) |
| the take-profit price of a long, the stop of a short | `upper_barrier` | `upper_barrier` | upper_barrier | `upper`, ceiling, band |
| the stop of a long, the take-profit of a short | `lower_barrier` | `lower_barrier` | lower_barrier | `lower`, floor, band |
| the vertical barrier, a duration token of the timeframe grammar — `4h` by default, 240 minutes = 16 × 15m bars; one place turns the token into minutes, and every population, purge and eligibility mask is told that number | `LABEL_HORIZON`, `HORIZON_TOKEN_MINUTES`, `LABEL_HORIZON_MINUTES`; `load_barriers()` in `module_ml/dataset.py` | — | 240-minute horizon | HORIZON_BARS, W, H; a horizon in minutes where the token belongs; a second place that resolves a token |
| the exclusive end of the event | `event_end_ts` | `event_end_ts` | — | exit time |
| the price that closes the event | `exit_reference_price` | `exit_reference_price` | — | exit_ref |
| how the event ended | `event_resolution` | `event_resolution`, `exit_counts.*` | upper_barrier / lower_barrier / vertical / ambiguous | reason, exit_reason |
| the four resolutions | `EVENT_RESOLUTION_{UPPER_BARRIER, LOWER_BARRIER, VERTICAL, AMBIGUOUS}` | `event_resolution` | — | bare 1 / −1 / 0 / 9 |
| the entry minute traded at all — knowable at `entry_ts`, may gate an entry | `entry_observable` | `entry_observable`; its complement is counted as `unobservable_entry_count` | unobservable entry | tradable, valid entry |
| the event can be classified — knowable only afterwards, never gates an entry | `label_valid` | `label_valid`; its complement is counted as `ambiguous_event_count` | ambiguous | masked |
| the supervised population: both of the above | `sample_valid` | `trainable_row_count`, `trainable_row_pct` | trainable rows | valid rows |
| how little an event overlaps its neighbours **within one population** — measured after the purge, never stored in Y | `average_uniqueness_weight()`, `train_weight` / `scoring_weight` | — | — | `weight` as a Y column, class weight |

`decision_ts`, `entry_ts` and `event_end_ts` are the three epoch-millisecond
columns spelled `_ts`, a contract with the parquets on disk; every new
epoch-millisecond key is `_ms`.

## Signal and strategy

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| the model's directional lean, `p_long − p_short` | `directional_probability_edge` | — | edge | `edge` as a code name |
| how much of that lean a signal must carry to be traded | `entry_edge_threshold` (τ) | `entry_edge_threshold` | τ (entry edge threshold) | `tau` as an identifier |
| the grid searched for it | `ENTRY_EDGE_THRESHOLD_GRID` | — | — | TAU_GRID |
| whether any threshold on the grid cleared the trade floor | `entry_edge_threshold_constraint_met` | same | `constraint met` (yes / fallback); `!` beside a fallback threshold | `tau_ok`, a name that says a constraint without saying which |
| the trade floor — a selection guardrail, not an acceptance gate | `MINIMUM_TRADES_PER_VALIDATION_FOLD` = 30 | — | — | MIN_TRADES, acceptance gate |
| how many timeframes must agree with the side | `MINIMUM_AGREEING_TREND_TIMEFRAMES`, `agreeing_trend_timeframe_count` | `minimum_agreeing_trend_timeframes` | at least `n` of `m` timeframes agree — both counts from the payload, the hierarchy's length among them | AGREE_MIN, n_agree, level |
| replaying the strategy over the canonical price path | `backtest()` | `<TICKER>_strategy_evaluation.json` | STRATEGY | live execution, exchange execution |
| the execution cost charged on entry and on exit | `EXECUTION_COST_RATE_PER_TRADE_SIDE` = 0.0006 | `execution_cost_rate_per_trade_side` | cost per side | costs_per_side, cost_per_side, fees |

The symbol τ may stay in equations and in table headers; its first use in any
document or on any page spells out `entry edge threshold`.

## Counts

Every count is `<what>_count`; a bare `n`, a bare plural (`gaps`) or an
adjective (`ambiguous`) names no number.

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| decisions on the 15m grid after the warm-up whose horizon still fits the research window — the labelled population, so it is short of the feature grid by the dropped tail | `decision_count` | `decision_count` | decisions | rows, `n` |
| rows a fold's metrics are computed on | `scored_row_count` | `scored_row_count` | scored | `n` |
| rows the model is fitted on, and the events purged before them | `training_row_count`, `purged_event_count` | same | trained on / purged | n_train, n_purged |
| rows in a prediction window | `window_row_count` | `window_row_count` | window | n_window |
| trades a fold produced | `trade_count` | `trade_count` | trades | n_trades |
| trials a search ran — the hyper-parameter search's, or the scored sets of the feature-set search | `HYPERPARAMETER_SEARCH_TRIAL_COUNT` (the ceiling the hyper-parameter search runs to), `trial_count` | `trial_count` | trials | n_trials |
| passes of the feature-set search — one forward move and one backward move over the champion | `pass_count` | `pass_count` | passes | rounds (the boosting rounds' word), iterations (the Map's word) |

## Data quality (data_status.json)

Written by `module_data/status.py`. An alias a scan publishes as a key carries that key's name; an alias the
report only reads on its way to one — a count it turns into a share, a timestamp it formats — stays inside the scan
and is named for what the scan measured.

| concept | artifact key | UI label | never |
|---|---|---|---|
| the two kinds a measured number can be, and the rule for reading them | — (a property of each row of the two tables, not a key) | an **invariant** has one correct value, zero, and its cells are marked `invariant` on the page; an **observation** has no threshold anyone can name and is read by comparing it with its previous reading — on the data views, the previous provider's. After a change of provider the invariants must still be zero and the observations are expected to move. Which key is which is `module_data/skills/skill_candle_canonicalisation.md` § 16; the marking is `module_monitoring/skills/skill_dashboard_conventions.md` | a colour for a magnitude; an invariant named a check, a gate or a guard; an observation called a failure |
| minutes a venue printed / the canonical grid holds | `row_count` | rows (`canonical rows` on the Pipeline tab) | rows, n |
| grid minutes a venue did not print (whole window / since its first observation) | `gap_count`, `gap_count_after_first_observation` | gaps | gaps |
| rows a venue printed beyond one per minute — the surplus, not the minutes it fell on | `duplicate_count` | dups | duplicates |
| candles whose OHLC ordering is broken, on the canonical series | `ohlc_violation_count` | ohlc bad | ohlc_violations |
| venue rows `ingest.py` will not join — the OHLC-intact predicate failed on a value, not only on the ordering | `invalid_row_count` | invalid | rejected, dropped; a second copy of the predicate |
| a venue's last printed close, the one dimensioned number the snapshot carries | `last_close` | last close | `price`, `px` |
| minutes whose source differs from the previous minute | `source_switch_count` | switches | source_switches |
| the largest 1m move at a switch / anywhere on the canonical series | `max_abs_return_at_switch`, `max_abs_return_1m` | max \|ret\| | `*_ret_*` |
| a venue's first and last printed minute | `first_observation_utc`, `last_observation_utc` | first / last | `first_ts` (a `_ts` is epoch ms) |
| the data window | `window_start_utc` | window | `window_start`; a window end, which the newest `last_observation_utc` already is |
| bars of a kind inside a bar or a series (a unit, not a bare count) | `ffill_bars`, `zero_volume_bars`, `flat_bars` | ffill (`ffill bars` on the Pipeline tab) / zero-vol / flat | `n_ffill` |
| canonical minutes repeating the previous candle verbatim while volume was printed — a feed frozen on its last bar, which no flatness count can see | `repeated_candle_count` | repeated | `dupes` (a duplicate is a repeated timestamp, not a repeated candle) |
| shares | `coverage_pct`, `source_share_pct_by_venue` (one share per venue, keyed by it) | coverage / one column per provider, the tier order of `source_venues` | ratio without `_pct`; a `<venue>_pct` key per venue; a share the page can divide out of two published counts (the ffill and real-data shares are its arithmetic) |
| cross-venue close divergence over the canonical series | `relative_divergence_p99`, `relative_divergence_max` | rel. divergence p99 / max (`max` alone on the page, under the p99 it is read against) | `rdiv`; a mean, which the bulk decides and no reading uses |

## Metrics

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| log-loss of the weighted training class prior | `prior_logloss` | `prior_logloss` | prior log-loss (`prior LL` in a cross-section header) | baseline |
| log-loss of the model on the evaluated block | `model_logloss` | `model_logloss` | model log-loss (`model LL` in a cross-section header) | loss |
| information beyond the prior, `1 − model / prior` — the model's objective, and the one the feature-set search selects on | `relative_logloss_skill` | `relative_logloss_skill` | skill (`rel. skill`, `val skill F<n>`, `mean val skill`, `holdout skill`, `skill F<n>` in the tables) | accuracy, edge |
| the search for model hyper-parameters, and the stage that runs it | HPO — `module_ml/hpo.py`, `make ml-hpo` | `hyperparameter_search_result` | search | tuning, optimisation, autoML; `HPO` spelled out mid-document after its first use; `search` alone for the feature-set search |
| the feature-set search — the stepwise choice of an asset's columns on the validation folds under the frozen hyper-parameters, selected on the model's validation skill fold by fold, and the stage that runs it (`module_ml/skills/methodology_ml.md` § 4); its selection overfitting is bounded and exposed, never absent — a move is accepted only by every fold, the catalogue is small, and the trial count stands on the page beside every proposal | `module_ml/feature_set_search.py`, `make ml-feature-set-search` and its detached twin `tmux-ml-feature-set-search` in the tmux session `feature-set-<ticker>` (`FEATURE_SET_SEARCH_SESSION`), one asset per session, gone with the search | `feature_set_search` (a block of ml_status.json), `<TICKER>_feature_set_search.json` | feature-set search | feature selection (as a name), optimisation, the search (HPO's word); a search selected on a strategy number; "no overfitting" |
| one scored set of the feature-set search — its columns, its skill per fold and their mean, what the strategy would do with it, the pass and the move that scored it | a row of `trials` | `trials`, each `columns_by_timeframe`, `validation` (per fold `relative_logloss_skill`, `sharpe`, `trade_count`), `mean_relative_logloss_skill`, `entry_edge_threshold`, `entry_edge_threshold_constraint_met`, `selection_score_mean_sharpe`, `pass`, `move` | trial | candidate (as a key), step |
| the mean over the validation folds of a trial's relative log-loss skill — the search's objective | `mean_relative_logloss_skill` | `mean_relative_logloss_skill` | mean skill; `Δ vs active` for a proposal's mean skill minus the active set's (`best proposal Δ skill` in the cross-section header, the first proposal's), page arithmetic printed in percentage points (`pp`) | score (the strategy's word for its own selection) |
| the set the search stands on — the best accepted so far, the one the next pass starts from | `champion_trial` | `champion_trial` | — | incumbent, current best |
| the two moves of a pass — one column in when every fold's skill rises, one column out at no worse skill on every fold | `FEATURE_SET_SEARCH_MOVE_FORWARD`, `FEATURE_SET_SEARCH_MOVE_BACKWARD` | `move` = `forward` / `backward` | — (the stage's progress line prints them; no page shows a move) | add / drop, greedy, step; a margin, a ceiling or a floor on the count of columns |
| whether a pass accepted nothing — the search is over | `search_converged` | `search_converged` | converged | done, finished, stopped |
| the promotion — a hand copying one proposal's columns into the asset's feature set and rerunning its ML chain, one asset at a time, never fanned out; the promoted set is re-tuned, so its realised result differs from the search's and the next search starts again; the same proposal twice changes nothing, and the commit history is the record of every promotion | `module_ml/feature_set_promote.py`, `make ml-feature-set-promote ASSET=<TICKER> PROPOSAL=<n>` | `<TICKER>_feature_set.json` with `columns_by_timeframe` and nothing else | — (the page shows a promotion only as the set's `source`) | the promotion threshold of `skill_pre_aws_solution.md` § The databases (a database's word); apply, activate, deploy; a promotion of the whole basket; a counter or a rank in the file — git holds the history |
| where an asset's feature set came from — the promoted file when it exists, else the default set of the catalogue | `feature_set_block()` | `feature_set` with `source` = `default` / `promoted`, `columns_by_timeframe` | source; `columns <timeframe>` in the cross-section | origin, provenance, `final_holdout_evaluation_count` (a counter git already records) |
| the sets a hand may promote — every trial no validation fold scores below the active set, by mean skill, ties to the smaller set, and the champion first when a pass accepted one; at most `FEATURE_SET_PROPOSAL_COUNT` | `proposals` | `proposals`, each `proposal`, `trial`, `columns_by_timeframe`, `added_columns_by_timeframe`, `removed_columns_by_timeframe`, `mean_relative_logloss_skill`, `validation`, `entry_edge_threshold`, `entry_edge_threshold_constraint_met`, `selection_score_mean_sharpe` | PROPOSALS — `#` for the rank, `columns added / removed` for the two differences | recommendations, top sets, best features; a set worse on any validation fold; the highest mean without the fold test |
| the inputs a search recorded, compared by equality when it is rerun — equal, it resumes; different, it starts again — the one copy of another file's content an artifact carries, admitted as the key of that comparison | `build_search_inputs()`, `inputs` | `inputs` with `research_window` (`start_utc`, `end_utc`, `seed`, `warmup_top_timeframe_bars`), `best_params`, `catalogue_columns_by_timeframe`, `active_columns_by_timeframe` | — | fingerprint, hash, checksum |
| whether a recorded search's inputs are still the asset's — false after a promotion, a retuning or a catalogue change, and the page then compares nothing | `feature_set_search_block()` | `inputs_current` | the note *the search predates the active set or its parameters*, in place of PROPOSALS and in the cross-section cell | stale, dirty, outdated; a guard that refuses the promotion |
| the HPO objective at one trial — the mean uniqueness-weighted log-loss over F2–F4, of which `best_logloss` is the lowest | `mean_validation_logloss`, the return of `objective()` in `module_ml/hpo.py`, logged per trial by `log_trials()` | — (no artifact carries it; the parameters file keeps the chosen point alone) | — (no page shows it) | a second name for `best_logloss`; a trial's objective in an artifact or a snapshot |
| the HPO objective value at the chosen point | `best_logloss` | `best_logloss` | best mean F2–F4 log-loss (`best LL` in the search table) | best_value, score |
| what the search chose: the point, its objective value and the trial count | `hyperparameter_search_result` | `hyperparameter_search_result` (a section of the parameters file, a block of ml_status.json) | search | a second name for the same block |
| the chosen point itself — the closed set of eight, in xgboost's own spelling because `module_ml/hpo.py` is a named boundary | the keys of `HYPERPARAMETER_SEARCH_SPACE`, `module_ml/config.py` — the one definition the search, the file and the table all derive from | `best_params`: `alpha`, `colsample_bytree`, `eta`, `lambda`, `max_depth`, `min_child_weight`, `num_boost_round`, `subsample` | depth, eta, min child, subsample, colsample, lambda, alpha, rounds — the search table's columns | a project synonym for an xgboost parameter; a second name for any of the eight; registering them one by one |
| what the search never touches — the constants the experiment freezes before it starts | `module_features/config.py`: the research window, `WARMUP_TOP_TIMEFRAME_BARS`, the hierarchy and the catalogue with every parameter in its terms; `module_ml/config.py`: `ATR_BARRIER_MULTIPLIER`, `LABEL_BARRIER_ATR_TIMEFRAME` and `ATR_WILDER_SMOOTHING_PERIOD_BARS` (the barrier's width), `LABEL_HORIZON_MINUTES`, `XGBOOST_FIXED_PARAMETERS`, `HYPERPARAMETER_SEARCH_TRIAL_COUNT`, `ANNUALISATION_PERIOD_15M_BARS`, `EXECUTION_COST_RATE_PER_TRADE_SIDE` | — (they define the experiment, so the git commit publishes them, not a payload) | the values quoted in methodology_ml.md and methodology_features.md | a searched parameter among them; a value changed without a commit that says so; a feature parameter copied out of the catalogue into a named constant |
| annualised Sharpe of the 15m equity path | `sharpe` | `sharpe`, `selection_score_mean_sharpe` | Sharpe; `selection score` for the validation mean, and `degradation` for holdout Sharpe minus the selection score — presentation arithmetic; in a proposal, what the strategy would do — reported, never selected on | return/risk; a deflated Sharpe ratio of nested trials |
| maximum drawdown of the 1m equity path | `max_drawdown` | `max_drawdown` | maxDD | DD |
| share of the fold spent in a position | `exposure` | `exposure` | exposure | utilisation |
| share of a fold's trades that ended positive | `hit_rate` | `hit_rate` | hit | win rate |
| mean cost-adjusted return of a trade | `average_trade_return` | `average_trade_return` | avg trade | expectancy, `avg_trade_ret` |
| equity at the end of the fold, starting from 1.0 | `final_equity` | `final_equity` | final equity | PnL |
| total gain per feature column of a validation fold's booster, zero for a column its trees never split on | `gain_importance()` | `gain_importance` under `validation_importance.fold_<n>` | gain | importance (bare), weight, the final-holdout booster's gain |
| mean absolute SHAP value (SHapley Additive exPlanations, `methodology_ml.md` § 13 [12]) per feature column of a validation fold's booster, over the fold's scoring rows and the three classes, in margin space, unweighted | `mean_abs_shap_importance()` | `mean_abs_shap_importance` | mean \|SHAP\| | `shap` as a key; SHAP importance (a method, not a quantity) |
| the two importances of every validation booster, the block the page takes its cross-fold means from | `validation_importance_block()`; `fold_importance_block()` of `train.py` measures one fold's two | `validation_importance` with `fold_2` … `fold_4`, each holding the two keys above | FEATURE SET — the two importance columns of its tables | an importance of the final-holdout booster; a mean over folds in the payload; a permutation importance (MDA) — a third importance selected on |
| the columns the model saw — the asset's feature set as feature ids, timeframe-major; beside them every catalogue column's values on the decision grid, keyed by feature id | `feature_columns` and `catalogue_values` of `load_xy()` | `feature_columns` | in set ✓ | a column literal in the page; `catalogue_columns` for the values |

## Payload structure

The container and envelope keys of the three computational snapshots, so that every published
key is in this register; the crawler's own are § Scalability crawler.

| concept | artifact key | holds |
|---|---|---|
| when the snapshot is written | `generated_at_utc` | the one timestamp of a payload; the crawler's snapshot carries none |
| the frozen experiment, once, globally | `research_window` with `start_utc`, `end_utc`, `seed` | the window and the seed, published once — no per-asset copy |
| the per-asset reports of ml_status.json | `assets` (a list) with `ticker`, `sample`, `hyperparameter_search_result` (`best_params`, `best_logloss`, `trial_count`), `validation`, `final_holdout`, `feature_columns`, `feature_set` (`source`, `columns_by_timeframe`), `validation_importance`, `feature_set_search` (`null` while no search has run; else `trial_count`, `pass_count`, `search_converged`, `inputs_current`, `proposals`), `strategy` | the experiment flow, sample → search → validation → holdout → attribution → the feature-set search → strategy |
| the classes of the supervised population | `class_counts` with `short`, `neutral`, `long` | counts, named by class |
| the structural facts the page needs beside the assets | `final_holdout_fold_id`, `minimum_agreeing_trend_timeframes`, `trend_gate_feature` | which fold is the final holdout; how many timeframes the gate needs; the feature id the gate reads |
| the feature layer's snapshot | `features_status.json`: `generated_at_utc`, `catalogue`, `assets` (per asset `ticker`, `row_count_by_timeframe`) | the catalogue as the register presents it, and the one run-state fact the feature layer has per asset — the rows of its three parquets, the last line of the register box; written by `module_features/status.py` |
| the catalogue block — of `features_status.json` | `catalogue` with `decision_timeframe`, `timeframes`, `warmup` (`top_timeframe_bars`, `end_utc`), `definitions` (per definition: `feature_definition`, `terms` — `inputs`, `indicator`, `parameter_word`, `parameter_bars`, `output_range` —, `operators`, `normaliser`, `range`, `timeframes`, `effective_history_hours_by_timeframe`, `warmup_bars`, `definition_in_default_set`), `nesting` (per adjacent pair: `lower`, `upper`, `lower_longest_effective_history_hours`, `upper_shortest_effective_history_hours`) | the catalogue as the register presents it — the catalogue frame of the ML Research tab reads nothing else |
| how the trades of a fold ended | `exit_counts` with `upper_barrier`, `lower_barrier`, `vertical`, `ambiguous` | counts, named by `event_resolution` |
| the final-holdout equity path | `equity_curve` with `equity` | the same key at two samplings, each named where it is written: daily in `<TICKER>_strategy_evaluation.json`, re-strided to weekly in `ml_status.json` for the sparkline. The last value is `final_equity` in both |
| the two tables of data_status.json | `venues` (one list per venue), `canonical_source` — lists whose rows carry `ticker`, the asset the row measures, beside `symbol`, derived at the report boundary from `config.symbol(ticker)`; no database column carries either | what each provider delivered, and the object they were merged into; the Pipeline tab reads `canonical_source` too, disjointly |
| the venue set, in tier order | `source_venues` | the one definition every per-provider section, column and share of the page is derived from — a reader takes the order from here and never from a key order, which is alphabetical |
| which asset a snapshot row is about | `ticker` — every row of the two tables, and of the feature snapshot's `assets` | the module names the asset it measured; a reader never derives it from `symbol` |
| the last canonical minute of an asset | `last_observation_utc` (a `canonical_source` row) | the asset's grid end; in a venue row the same key names that venue's last printed minute |
| the unit of download work, and the cadence a measurement's age is judged against | `download_cadence_minutes` | one UTC day; the Pipeline tab warns above it — per asset, `observation lag` (now − `last_observation_utc`) and `measurement age` (now − `generated_at_utc`) on the page, arithmetic, never a key |
| the longest run of each state a canonical minute can be in | `longest_flat_run_minutes`, `longest_ffill_run_minutes` | durations, in minutes — `flat run (min)` and `ffill run (min)` on the page. A minute is forward-filled, flat, or traded, decided in that order: a forward-filled row repeats the previous close with no volume and so satisfies the flat geometry as well, and counting it as flat would report fabrication as a quiet market |

## Stores

**The store is the boundary between compute and state.** Every stage reads and
writes only the five stores, one folder each under `store/`, and learns where
they are from the environment: one variable per store, set by the launcher (the Makefile on the host, the
compose file inside a container) and read by each `config.py` as
`Path(os.environ[...])` — a missing variable is the interpreter's own
`KeyError`, not a guard. A module reads only the stores it touches, and no
module writes into another module's source tree. The image carries the pins and
the mounts carry the code and the stores each service touches, read-only where it
only reads: `/store/<content>` is the one path a
container addresses a store by; `/app` is the checkout, `store/` included, and
`/app/store/<content>` is never an address (`AGENTS.md` § Canonical vocabulary,
the store-paths row).

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| the store contract: one environment variable per store, naming the directory that store is | `STORE_RAW_1M_DIR`, `STORE_ASSETS_ARTIFACTS_DIR`, `STORE_TRIALS_DIR`, `STORE_RUN_RECORDS_DIR`, `STORE_STATUS_DIR`; on the host `$(CURDIR)/store/<content>`, in a container `/store/<content>` | — | — | a path derived from `__file__` two levels up, a store named by a literal at the point of use, a second name for the same directory |
| the status store: where every snapshot lands, tracked so a fresh clone opens on real numbers | `store/status/`, `STORE_STATUS_DIR`; `DATA_STATUS_JSON_PATH`, `FEATURES_STATUS_JSON_PATH`, `ML_STATUS_JSON_PATH` in the configs of the modules that write them, `SKILLS_STATUS_JSON_PATH` in the crawler's | `data_status.json`, `features_status.json`, `ml_status.json`, `skills_status.json` | the page's footer names the four snapshots | a snapshot written into `module_monitoring/` or any other module's directory |
| the trials store: every point the hyper-parameter search drew, one ledger per asset, written by `module_ml/hpo.py` alone — the one file that speaks mlflow — and read by no stage and no route; nothing prunes it, and a hand clears an asset's ledger as it clears the raw store and the run records. The point the search chose stands twice, as `best_params` and `best_logloss` in `<TICKER>_parameters.json` and as one run here — the one copy of an artifact's content this store carries, admitted because the artifact is the contract between stages, read by `train.py` and by `feature_set_search.py`, and this ledger is read by neither: the artifact decides, the ledger records. The feature-set search leaves nothing here — its trials are `<TICKER>_feature_set_search.json`, the stage's resume state and the source of its proposals, and one result has one carrier | `store/trials/`, `STORE_TRIALS_DIR`; `trials_sqlite()` in `module_ml/config.py`, one `trials.sqlite3` per asset as the market object is one file per asset; in a container `/store/trials` | — | — | `mlruns/`, mlflow's own default; an `MLFLOW_TRACKING_URI` in any environment; a tracking server, a model registry, a published port or a UI service; a mount on any service but the `ml` runner; a stage reading it back |
| the name of one trial in the ledger: its place in the search that drew it | `log_trials(ticker, trials)` in `module_ml/hpo.py`, which mints `hpo_<n>` — `hpo` is the one search that writes the ledger and the second half of the make target that runs it, and `n` counts from one | — (no artifact carries it) | — (no page shows it) | mlflow's own minted name, an adjective and an animal; a ticker in the name, the experiment being the ticker; optuna's trial number, which counts from zero |
| the snapshot route: the dashboard serving a status object by its file name | `STORE_STATUS_ROUTE_SEGMENT`, `GET /store_status/<name>` in `serve.py`, mapped onto `store_status_file(name)` under `STORE_STATUS_DIR` | — | — | a snapshot fetched from the page's own directory, a route per snapshot |

## The tree

How the project is laid out, and the names of that shape (`AGENTS.md`
§ Architecture shape, § The default choice, § The shape — what holds the project
together).

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| a module: its package, its orientation and its own skills under one directory | `module_<domain>/` holding `<file>.py`, `README_module_<domain>.md` and `skills/` | — | — | a numbered directory; a package split across two places; a module's rule filed outside it |
| the project's one image | `liora-1m-pipeline`, built by `docker compose build` from the root `Dockerfile` onto `python:3.12-slim` | — | — | an image per module; an image per asset; compose's `<project>-<service>` default |
| a path written `module_<domain>/…` in the contract or a skill | the package as it lies at the root | — | — | a `../module_<x>` relative path; a path built at the point of use |
| a comment that explains a Python module-level constant, placed by what it explains (`AGENTS.md` § Canonical vocabulary, the constant comments row) | inline comment — PEP 8's word for a comment on its statement's own line; block comment — PEP 8's word for the comment lines directly above the code they apply to | — | — | trailing comment, end-of-line comment, side comment |

## Twice by extraction

**No module imports another** — `module_monitoring` included: it reads what the
snapshots publish and what lies in the stores. Each of the objects below
therefore has two or more full owners, identical to the byte unless its row says
equal by value: the copy is registered here, marked on every side
(`# twice by extraction`, placed by `AGENTS.md` § The shape —
what holds the project together, D14), and a change to one copy is a
change to every copy, by hand — the one named exception to `AGENTS.md` § The
default choice, "no second copy to drift". There is no shared package: a `common` for a dozen lines would be a mechanism,
and `AGENTS.md` § Architecture shape admits a new module only for a distinct
responsibility.

| object | owners | why twice |
|---|---|---|
| the units, equal by value, each holder the ones it uses: `MILLISECONDS_PER_SECOND`, `MILLISECONDS_PER_MINUTE`, `MILLISECONDS_PER_DAY` in Python; `MILLISECONDS_PER_SECOND` and `SECONDS_PER_MINUTE` in the page, `MINUTES_PER_HOUR` and `HOURS_PER_DAY` in the Pipeline tab; `SECONDS_PER_MINUTE` in the crawler | `module_data/config.py`, `module_features/config.py`, `module_ml/config.py`, `module_skills/sub_module_scalability_crawler/config.py`; the browser's own in `module_monitoring/page.js` and `module_monitoring/data.js`, which import no config | a unit is a unit; importing one across a boundary would drag the module behind it |
| `BYTES_PER_KIBIBYTE` | `module_data/config.py`, `module_ml/config.py`; the browser's own in `module_monitoring/page.js` | the same |
| `DUCKDB_MEMORY_LIMIT` | `module_data/config.py`, `module_features/config.py`, `module_ml/config.py` | every connection of every module pins the same ceiling beside `threads=1` |
| the store reads `STORE_ASSETS_ARTIFACTS_DIR`, `STORE_STATUS_DIR` | `module_data/config.py`, `module_features/config.py`, `module_ml/config.py`; `STORE_STATUS_DIR` also `module_monitoring/config.py` | the two stores every module of the chain touches, and the one the dashboard serves, each read as `Path(os.environ[...])` where it is used |
| the descriptors `artifact_dir()`, `research_ohlcv_duckdb()` | `module_data/config.py`, `module_features/config.py`, `module_ml/config.py` | the asset folder and the database are the store the chain touches; the path grammar is one and is spelled once per owner |
| `load_json()` | `module_ml/dataset.py`, `module_monitoring/serve.py` | two readers of the same JSON files |
| `to_utc_ms()` | `module_data/config.py`, `module_features/config.py`, `module_ml/config.py` | the window literals of two modules are turned into milliseconds by the same function |
| `build_ticker_parser()`, `parse_tickers()` | `module_data/config.py`, `module_features/config.py`, `module_ml/config.py` | the one CLI every stage shares; `module_monitoring` runs no stage and parses no ticker argument |
| `rounded()` | `module_data/config.py`, `module_ml/config.py` | the snapshots round the same way |
| `RESEARCH_START_UTC`, `RESEARCH_END_UTC` (and their `_MS`) | `module_features/config.py` (the bars and the catalogue), `module_ml/config.py` (the labels and the folds) | the frozen window is the experiment's; each layer that bounds by it owns the literal |
| `catalogue_json()` | `module_features/config.py`, `module_ml/config.py` | the writer names the contract it writes, the reader the contract it reads |
| `feature_id()` | `module_features/config.py`, `module_ml/config.py` | the grammar of `module_features/skills/skill_feature_taxonomy.md`, two lines, restated where X's columns are named |
| `TREND_GATE_FEATURE_DEFINITION`, equal by value | `module_features/config.py` (the first record of the catalogue), `module_ml/config.py` (the same name as a literal) | the strategy reads the trend definition by name from the contract's columns |
| `to_json_safe()`, `write_json()` | `module_features/dataset.py`, `module_ml/dataset.py` | the one canonical JSON form every published object takes — the contract, the snapshots, the artifacts |
| `write_parquet()` | `module_features/dataset.py`, `module_ml/dataset.py` | the repr round-trip that makes a parquet byte-reproducible |
| `wilder_smoothing()`, `atr()`, `asof_index()` | `module_features/indicators.py`, `module_ml/labels.py` | the label defines its own barrier scale, and aligns to the last closed bar the same way the catalogue does |

The gate at every commit: the rows equal by value compare equal as values, the
bodies of every other copy as syntax trees, and `git grep "from module_"` inside any module finds only the module itself.

## Artifacts

**One file per distinct artifact responsibility; no duplicate representations
of the same result.** One directory per ticker under `store/assets_artifacts/`;
every file carries the `<TICKER>_` prefix, a time series carries its grid in
timeframe slots, and paths are built only by the descriptors of
`module_features/config.py` (the feature parquets and the contract beside them) and `module_ml/config.py`
(the rest); whether an asset holds its three result files is asked
once, by `is_artifact_set_complete()` beside them.

The twelve manifest files in `LC_COLLATE=C` listing order — the order
`file_manifest()` in `module_ml/status.py` and the generated README share; the
two a hand's stages write are listed with no size until they exist:

| file | written by | holds |
|---|---|---|
| `<TICKER>_README.md` | `module_ml/status.py` | what the folder holds and what came out of it; no timestamp |
| `<TICKER>_catalogue.json` | `module_features/catalogue.py` | the feature layer's contract the ML layer reads instead of the feature configuration: `decision_timeframe`, `timeframes` (each `timeframe`, `slot`, `duration_ms`), `warmup_top_timeframe_bars`, `warmup_end_ms`, `columns_by_timeframe`, `default_columns_by_timeframe`, `parquet_by_timeframe` |
| `<TICKER>_feature_set.json` | `module_ml/feature_set_promote.py` | `columns_by_timeframe` — the promoted feature set, a hand's choice, and nothing else; absent, the default set is the asset's; tracked, like the parameters it conditions |
| `<TICKER>_feature_set_search.json` | `module_ml/feature_set_search.py` | `inputs`, `trials`, `champion_trial`, `pass_count`, `search_converged`, `proposals` — every scored trial, the search's own state, rewritten after every scored trial; present once a search has run |
| `<TICKER>_features_ss-15-hh-dd-MM.parquet` | `module_features/catalogue.py` | the catalogue on 15m — `decision_ts` and every definition offered on 15m, on the decision grid |
| `<TICKER>_features_ss-mm-01-dd-MM.parquet` | `module_features/catalogue.py` | the catalogue on 1h — `decision_ts` and every definition offered on 1h |
| `<TICKER>_features_ss-mm-04-dd-MM.parquet` | `module_features/catalogue.py` | the catalogue on 4h — `decision_ts` and every definition offered on 4h |
| `<TICKER>_label_events_ss-15-hh-dd-MM.parquet` | `module_ml/labels.py` | Y — an ambiguous event carries `y = 0` with `label_valid = false`, so `y` is never read without `label_valid`; `decision_ts`, `entry_ts`, `y`, `event_end_ts`, `entry_observable`, `label_valid`, `event_resolution`, `entry_price`, `upper_barrier`, `lower_barrier`, `exit_reference_price` |
| `<TICKER>_model_evaluation.json` | `module_ml/train.py` | `validation.fold_2..4` and `final_holdout`, each `prior_logloss`, `model_logloss`, `relative_logloss_skill`, `scored_row_count`; `validation_importance.fold_2..4`, each `gain_importance` and `mean_abs_shap_importance` per column; `feature_columns`; `class_counts`, `labels`, `segments` |
| `<TICKER>_oos_predictions_ss-15-hh-dd-MM.parquet` | `module_ml/train.py` | `decision_ts`, `oos_fold_id`, `p_short`, `p_neutral`, `p_long` — the full windows of F2–F5; metrics score only the supervised subset |
| `<TICKER>_parameters.json` | `module_ml/hpo.py` | `hyperparameter_search_result` (`best_params`, `best_logloss`, `trial_count`) |
| `<TICKER>_strategy_evaluation.json` | `module_ml/strategy.py` | `entry_edge_threshold`, `entry_edge_threshold_constraint_met`, `selection_score_mean_sharpe`, `execution_cost_rate_per_trade_side`; per fold `sharpe`, `max_drawdown`, `trade_count`, `hit_rate`, `average_trade_return`, `exposure`, `exit_counts`, `final_equity`; the final holdout's `equity_curve` |

Three files are tracked — `<TICKER>_README.md`, `<TICKER>_parameters.json` and,
once a hand has promoted one, `<TICKER>_feature_set.json`: together they make a
folder readable, and reproducible, without a run, because the parameters are
tuned for the set they were searched under. The nine others are regenerable —
the eight the chain rebuilds from the database, and the search result a hand
reruns. Beside the manifest, outside it, `<TICKER>_research_ohlcv.duckdb`
holds the canonical series and its aggregations — its size moves with every
top-up, and the README is byte-reproducible for an unchanged experiment.
`<TICKER>_catalogue.json`, the feature layer's contract (§ Features), stands in
the manifest and is regenerable, like the parquets.

## Features

The grammar is `module_features/skills/skill_feature_taxonomy.md`, the definitions
`module_features/skills/methodology_features.md`; this register confirms the words.

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| a series of one timeframe's bars, with no parameter | `open`, `high`, `low`, `close`, `volume` — a bar column — and `log_volume`, the one series with a kernel: `SERIES_KERNELS`, `module_features/catalogue.py` | `inputs` of a term | the series token | a series with a parameter |
| an indicator — one computation with exactly one integer parameter, glued to its token; its kernel carries the token's name in `module_features/indicators.py`, `zscore` alone reading `rolling_zscore` for the family it belongs to, and its invariants — the kernel, the parameter word, the warm-up multiple, the fixed inputs, the output range when it is bounded — are one record of the register beside it | `ema<n>`, `sma<n>`, `rsi<n>`, `atr<n>`, `zscore<n>`, `range_position<n>`; `INDICATORS` — `kernel`, `parameter_word`, `warmup_multiple`, `inputs`, `output_range` of a record, `module_features/indicators.py` | `indicator`, `parameter_word`, `parameter_bars`, `output_range` of a term | the token, and `output 0–100` beside it when the indicator is bounded | `rsi_14`, `sma_200`, `bb20`; a table of indicator facts in `config.py` beside the register; `kernel` for the operating system's accounting — that is the Lifecycle tab's word |
| a term — a series or an indicator inside a feature definition | `("ema", 20)`, `("log_volume", "zscore", 50)`, `("close",)`; `term_name()` | `terms` | terms | atom (the prose word of the skill, never an identifier) |
| a feature definition — terms of one timeframe composed by the operators, with an optional normaliser; the timeframe-less half of a feature | one record of `FEATURE_CATALOGUE`; `feature_definition_name()`; `OPERATORS` = {`minus`, `over`} and `NORMALISERS` = {`centered`}, one record per token beside its kernel in `module_features/catalogue.py` | `feature_definition` | definition | molecule, family, feature family, indicator (for a composite); `trend`, `momentum`, `volatility`, `structure`, `activity` — a category, not a computation |
| a feature — a definition aligned to the decision grid on one timeframe; the column of X and the key of an importance | `feature_id()` = `<definition>_<timeframe>` | `feature_columns`, the keys of an importance | the feature id | a column literal in a page script; a parquet column with a timeframe (the file name carries it) |
| the feature catalogue — every definition the repository can compute, with the timeframes it is offered on; drafted, like the rest of `config.py` | `FEATURE_CATALOGUE`, `catalogue_columns()`, `CATALOGUE_COLUMNS`; the stage `features-catalogue`, `module_features/catalogue.py` | `catalogue` (of `features_status.json`); `<TICKER>_catalogue.json` | CATALOGUE | palette, feature list, feature store |
| the feature layer's contract, per asset — what the ML layer reads instead of this module's configuration | `catalogue_contract()` and `catalogue_json()` in `module_features/config.py`, the descriptor's copy in `module_ml/config.py` (§ Twice by extraction); read once per stage by `load_catalogue()` of `module_ml/dataset.py` and carried as `cat`, the helpers of `module_ml/config.py` reading the dict and building paths from it | `<TICKER>_catalogue.json`: `decision_timeframe`, `timeframes` (`timeframe`, `slot`, `duration_ms`), `warmup_top_timeframe_bars`, `warmup_end_ms`, `columns_by_timeframe`, `default_columns_by_timeframe`, `parquet_by_timeframe` | — | an import of `module_features` from `module_ml`; a token or a slot parsed in the ML layer; a second read of the file inside one stage; a path built from the slot grammar outside `module_features` |
| the effective history a parameter covers on a timeframe, `bars × timeframe` — a window's window, a recursion's span or period, the bars carrying most of its weight — the number the nesting rule compares | `definition_effective_history_hours()` | `effective_history_hours_by_timeframe`; `lower_longest_effective_history_hours`, `upper_shortest_effective_history_hours` of `nesting` | effective history | history (bare — a recursion has no window), span (the EMA parameter word), lookback hours |
| the trade's Bollinger reading of `zscore20` — %b(20, 2σ) = zscore20 / 4 + 0.5, an affine map a tree model is invariant to; no %b column exists | — | — | Bollinger %b, in the definitions table | `bb20`, `%b` as a column, `z / 2 + 0.5` |
| the definitions an asset's model sees until a promotion — the frozen experiment's fifteen columns, in the order it stacks them | `DEFAULT_FEATURE_COLUMNS_BY_TIMEFRAME`; `definition_in_default_set` of a record | `definition_in_default_set` | default set | the frozen fifteen (as a name) |
| the definition the strategy hierarchy reads on every timeframe, set or no set | `TREND_GATE_FEATURE_DEFINITION` = the first of the catalogue in `module_features/config.py`, and the same name as a literal in `module_ml/config.py` (twice by extraction); the gate's timeframe is the top of the contract's hierarchy, `trend_gate_timeframe(cat)` (`TREND_GATE_TIMEFRAME` in the feature layer) | `trend_gate_feature` | the gate | `TREND_FAMILY`; a column literal in `asset.js` |

The strategy hierarchy reads the trend definition through `TREND_GATE_FEATURE_DEFINITION`, so
the name appears once in the code rather than in three string literals; `centered_rsi14` keeps
its American spelling (`skill_pre_aws_solution.md` § What stays as it is, and why).

## Asset containers

The concepts of `docker-compose.yml`. They name
how a stage is run, never what it computes.

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| the one asset a container is run for | `ticker` (code, key, folder), named to a stage by the command's `--tickers`, which has no default — the fan-out passes `--tickers <TICKER>` from `TICKER_LIST`; no container reads `ASSET` | — | — | `TICKER`, `SYMBOL`, `ASSET_TICKER`, a per-asset `.env` |
| the basket, as the launcher defines it | `TICKERS` in the orchestration `Makefile`, the basket's one list; `TICKER_LIST` (`ASSET` narrows it; the `fanout` macro's list), `TICKERS_CSV` (the basket as one `--tickers` argument — the `basket` macro's, for the snapshots and the download, which `ASSET` never narrows) | — | — | a basket in a module's `config.py`, a second list in compose, a stage that defaults to it |
| an asset container: a runner's one-off for one asset, exiting with its stage | the `fanout` macro's `docker compose run --rm -T <runner> python -m <module>.<stage> --tickers <TICKER>`, once per ticker of `TICKER_LIST` | — | — | a compose service per asset; a resident per asset; a `restart:` policy, a published port |
| the one service that holds the docker socket, and the only one | `devops` — the `x-service` anchor plus its own command, `group_add` and, beside the tree at `/app`, the socket — no store | `compose_project`, `own_project` | DevOps | the socket in the dashboard; a third-party socket proxy; a TCP daemon endpoint; a published port |
| the host's docker group, so the one socket holder reads the socket without being root | `DOCKER_GID` of the Makefile (`getent group docker`), carried by `COMPOSE_ENV` into `group_add: ["${DOCKER_GID:-999}"]` on `devops` | — | — | `privileged`, `user: root`, a hardcoded gid, `group_add` on any other service |
| the dashboard's command — the server, on the internal port | `dashboard`'s own `command: python -m module_monitoring.serve`; `CONTAINER_PORT` = 8900 and `BIND_ADDRESS` = `0.0.0.0` in `module_monitoring/config.py` | — | — | a port or a bind address read from the environment or the command line, `PORT` inside a container |
| the host port: the host side of the dashboard's mapping, measured at invocation, never hardcoded | `PORT` of the Makefile — the port the dashboard already publishes, else the first free port from 8900 upward; `PORT=n` overrides (`skill_asset_containers.md` § The topology); `${PORT:-8900}` in `docker-compose.yml` | — | — | `8900` as the page's address in a document, a command or a comment; a second variable for it; `PORT` inside a container (the row of the dashboard's command); a measurement outside the Makefile |
| the compose project — the one fixed name every container, network and volume of this project carries on every host | `name: liora` in `docker-compose.yml`; containers `liora-<service>-1`, the network `liora_default` | `compose_project`, `own_project` (the panel's keys) | — | a name derived from the checkout's directory; a project per ticker; two checkouts of the project up at once on one host (they share the name — run one, or set `COMPOSE_PROJECT_NAME`) |
| a runner — a compose service that is a role and a one-off: no command of its own, `docker compose run --rm -T <runner> python -m <module>.<stage> --tickers <TICKER>` supplies one and the container exits with the stage | `data`, `features`, `ml` — the `x-service` anchor, which carries the one `build:` and `image:`; the `run`, `fanout` and `basket` macros of the Makefile | — | — | `pipeline` (one runner for every module), a stage run by `exec` inside a resident, a runner with a `command:` |
| the memory ceiling of the one task that needs it — HPO and XGBoost above DuckDB's `4GB` | `deploy.resources.limits.memory` of the `ml` runner alone | — | — | `mem_limit` beside it, a CPU quota, a reservation; a ceiling on the anchor, so on the dashboard too |
| how long a container lives: one-off — a `run --rm` process that exits with its stage — or resident — a server that stays up | the `lifetime` column of `skill_asset_containers.md` § The topology | — | — | one-shot, ephemeral, daemon, long-running; `task` or `job` for the one-off |
| the presentation switch: the whole stack up with the page open, or everything down, in one word | `make on`, `make off` — the two bare lifecycle targets a presenter types | — | — | `start` / `stop` (the panel's verbs for one container), bare `up` / `down` (compose's), `run`, a second switch pair |

## Run record

What one recorded run of the chain leaves in `store/run_records/<run_id>/` — one
record for the whole basket and never one per asset, because a run of the chain
is one event and every asset's stages belong to it — written by the repository's
`record.py`, which wraps each make target of the chain from outside every
container: the four pipeline stores listed before, the command, the four listed
after. The recorder knows no module and reads nothing a stage says about itself;
what a stage did is what it left in the pipeline stores — the same thing a task
scheduler records about a task. The trials store is not among them, and that is
the reason rather than an oversight: a trial ledger is the stage's own account of
its search, which is the one thing this recorder never reads. `run_id` is `<YYYYMMDDTHHMMSS>Z_<git short commit>`: not a
content hash, but git's own identity, the record `module_ml/config.py` already
names — so it sorts chronologically and points at the code that ran.

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| one recorded execution of the chain — the execution name, read forward | `run_id` | `run_id` | run | build, job, a content hash; mlflow's own run id, which is never bound to a project name and enters no identifier, key, route or path here |
| one command of a run, named by its make target — one seam, `data-download`, runs two stages (`skill_pre_aws_solution.md` § The Makefile is the developer interface) | the target name | `stage` — the file name `<stage>.json` | stage | step, task |
| the command the recorder ran | `command` | `command` | — | a stage naming itself |
| how the stage ended | the command's exit code, the recorder's own | `exit_code` | exit | status, ok |
| when the stage ran, and for how long | `started_at_utc`, `ended_at_utc`, `duration_seconds` | the same | start / time | wall, elapsed |
| what the stage did to the stores — every file added, changed (size or mtime moved) or removed, by store and path | `store_diff()` | `store_diff` with `added`, `changed` (`store`, `path`, `size_bytes`, `mtime_ns`) and `removed` (`store`, `path`) | added / changed / removed, bytes written | output, artifacts, a stage → artifact map |
| the basket one run covered | the launcher's `TICKERS`, which the make target the recorder wrapped carries into every stage command | — (not in the record: the recorder knows no basket) | — | `ticker`, the first of the basket standing for it |
| the run ids the dashboard lists, newest first | `load_run_ids()` | `run_ids` — the envelope of `GET /runs`, beside `generated_at_utc` | run | a run list per asset |
| the stage records of one run, in the order the stages started | `run_payload()` | `stages` — the envelope of `GET /runs/<run_id>`, beside `run_id` and `generated_at_utc` | the stage table | a record per asset |
| where a run's record lives | `STORE_RUN_RECORDS_DIR`, `run_dir()` | — | — | a `runtime/` folder under an asset, one run record per asset |

One file per stage, `<stage>.json`, written after the second listing so it never
appears in its own difference; a run is the directory. None of it is committed;
`.gitignore` covers `store/run_records/`.

The routes: `GET /runs` lists the run ids newest first, `GET /runs/<run_id>`
answers the run's stage records in the order the stages started.

## Documentation ownership

Where a rule is written is itself a named decision. `AGENTS.md` § The default
choice holds the rule; these are the names it uses.

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| a normative document describing one module's own responsibility | `module_<name>/skills/<document>.md` | — | — | module-specific rules kept in `module_skills/`; a per-module `docs/` or `doc/` folder |
| a normative document that crosses modules or governs the project | `module_skills/<document>.md` — the canon (§ The tree) | — | — | a cross-cutting rule filed under one module; an edit to a copy |
| a normative document about one sub-module alone, kept beside its code — the canon having no `skills/`, and `module_skills/skill_*.md` holding the rules that cross modules or govern the project; a column of the skill matrix, like every skill. A rule two sub-modules draw to crosses them and goes to the canon: `module_skills/skill_tui_designer.md` | `module_features/sub_module_coordinate_search_terminal/skill_coordinate_search_terminal.md` | — | — | a sub-module's own rule among `module_skills/skill_*.md`; a rule two sub-modules obey kept beside one of them; a `skills/` folder for one document |
| the directory holding one module's own skills | `module_<name>/skills/` | — | — | `module_<name>/skill/`, `module_<name>/documentation/` |
| the link surface that finds every skill without holding one | `module_skills/README.md` — every skill by a relative path, cross-cutting and module-owned alike | — | — | a collection of copies; an index that restates a rule it links to; a relative link into another repository |
| the door a session opens before the contract: the working path, the modules by name and the documents that hold the rules — it points and holds none | `CLAUDE.md` at the root | — | — | a rule written in it; a per-module `CLAUDE.md`; `CLAUDE.local.md` or `.claude/` inside the tree |
| one module's reader-facing front door | `module_<name>/README_module_<name>.md`; a sub-module's `README_<its directory>.md`, `module_skills/sub_module_scalability_crawler/README_sub_module_scalability_crawler.md` | — | — | `module_<name>/README.md`; a front door that restates a skill or a decision table |
| a review report: the tree reviewed against one question, kept at the root beside the contract and the overview — `REPORT_pre_aws_minimalism.md` asks whether each seat of the mapping is the cheapest that keeps its boundary | `REPORT_<subject>.md` | — | — | a report inside a module; a report that restates a rule instead of citing it; a work order or a plan kept in the tree |
| the design rationale: the section of a module's orientation that says, per object or analogous pair or the module's documents, why here, why beside these, why this boundary and which mapping row it answers to — the fourth the test of the first three | `## Design rationale` of each `README_module_<name>.md`, and of `module_skills/skill_scalability_crawler.md` for the canon's sub-module | — | — | a decision table; a rule restated; an object with no row or two; ADR, decision record, decision log, `docs/` |

## Pre-AWS direction

The names `AGENTS.md` § Pre-AWS architectural direction and
`skill_pre_aws_solution.md` use — how the repository is drawn, not what it
computes; the rules are there, not here. The mapping table is
`skill_pre_aws_solution.md` § The mapping table, and *the elsewhere column*
its column *the same responsibility elsewhere*. Cloud proper nouns are
external vocabulary; the closed list of where one may be spoken is
`AGENTS.md` § Pre-AWS architectural direction, and no identifier, key or path
carries one.

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| the stance: a local academic architecture whose boundaries would survive a move onto standard cloud primitives, with no cloud used and none planned | Pre-AWS — a word of the documents; `pre_aws` in two file stems, the skill's and the report's, no identifier carries it | — | — | cloud-ready, AWS-ready, cloud-native, a migration plan, a deployment guide; `pre-aws` or `PreAWS` in prose |
| compute: a process that reads a store, writes a store and exits, owning no asset state between invocations | every stage's `main()`, `python -m <module>.<stage> --tickers <TICKER>`; the container that runs it; elsewhere a task on the one host every asset's runs share, `task` being the elsewhere column's word | — | — | a container as the home of an asset's state; a resident as a requirement of a stage; an in-process cache between stages; `worker`, `processor` |
| the rebuild condition: whether an asset's artifacts must be rebuilt from its canonical series, answered without launching anything | `is_artifact_set_complete()` is its completeness half; freshness has no predicate yet — its names when written: `has_new_market_data()`, `requires_canonical_rebuild()`, `requires_feature_rebuild()`, `requires_model_rebuild()`; until then the rerun table of `module_ml/skills/methodology_ml.md` § 11 is read by a human | — | — | a scheduler, a watcher, an event bus, a function that both detects new data and trains; `should_run()`, `check_update()`, `trigger()` |
| the mapping table: where cloud proper nouns are spoken — what this repository has, beside the shape the same responsibility takes elsewhere | `skill_pre_aws_solution.md` § The mapping table | — | — | an adapter, a cloud config file, a proper noun outside the places `AGENTS.md` § Pre-AWS architectural direction lists; a path of the elsewhere column read as a proposal for a local directory |
| the seat: the one paragraph of a local skill, or one bullet where the skill has no headings, that names the primitive its object answers to, in the mapping table's words with the proper noun in parentheses as the table spells it, and cites the skill for the rest | — (a word of four documents: `skill_asset_containers.md`, `skill_determinism.md`, `module_data/skills/skill_candle_canonicalisation.md` § 15, `module_monitoring/skills/skill_devops_panel.md`) | — | — | a second seat in one skill; a seat that restates a row or a ladder; a seat in a `README_module_<name>.md`, whose form is the design rationale; `target`, `cloud note`, `mapping section` |
| the resource role: the name a cloud resource would carry — `<project>-<environment>-<resource-role>`, the role the seat's name in `skill_pre_aws_solution.md` § Infrastructure seats or the task a row of its § The mapping table names, lower case with `-` between its words (`task-host`, `store-volume`), the project the head the image names and the compose project already carry, `liora` | — (no identifier; `liora-1m-pipeline` and `liora-<service>-1` are the names of that shape the tree holds, with no environment token) | — | — | a second list of roles; a role no seat or row names; `dev` or `prod` in a tracked name; a ticker in a resource name; an environment token on the image tag |
| a state name: the state a stage would be — one per row of `skill_pre_aws_solution.md` § The Makefile is the developer interface, and PublishStores, the copy state no stage answers to; *Publish* in a state name means: write the object where its readers read it | — (a word of the elsewhere column; no identifier) | — | — | registering them one by one; a state name with "and" in it; *publish* as *make public* |
| an instance: one Linux virtual machine of the elsewhere column — the host containers run on: the task host every asset's runs share, its store volume beside it, and the strategy host | — (a word of `skill_pre_aws_solution.md` § Infrastructure seats; no identifier) | — | — | `instance` or `host` for a container — a container is a *machine* in the DevOps panel; a host per asset; node |
| the store volume: the task host's durable disk — the five stores at `/store/<content>`, each at the path its `STORE_*_DIR` names | the `./store/<content>` mounts of `docker-compose.yml`, read forward as `<volume>/<content>:/store/<content>` — no identifier carries it | — | — | asset volume; a volume per asset; a shared network filesystem; the volume as the copy; `data_volume` |
| the ladder: the three phases in which the runtime elsewhere becomes true, each named for what it changes — *the lift*, *the idiom*, *the image carries the code* | — (a word of `skill_pre_aws_solution.md` § The retrain runtime is a ladder; no identifier) | — | — | a letter or a number for a phase; a phase as a branch or an environment; `dev` / `prod`; a phase built here; rung |
| the promotion threshold: a second concurrent writer or a cross-asset query — the one condition under which a managed database replaces an asset's embedded file | — (a word of `skill_pre_aws_solution.md` § The databases; no identifier) | — | — | a database process for one writer; a threshold in rows or bytes |
| the active version: the one `<version>` of an asset's artifacts a reader reads, chosen where the reader is | — (`<version>` is the execution name, `run_id`; no identifier) | — | — | latest, current, prod; a mark inside a file |
| the tunnel: how a reader reaches the page on a host that is not theirs — `ssh -L <local>:127.0.0.1:<port> <host>` of `README.md` § Quickstart; elsewhere a port-forward, the elsewhere column's word | — (a command of the README; no identifier) | — | — | a public port; a load balancer |
| read forward: a local object read as the same responsibility elsewhere — the mapping table's column — with nothing moved | — (a phrase of the documents; no identifier) | — | — | migrated, ported, deployed, in production |
| the move: what a local thing's seat elsewhere costs it — a rename, one edit, or absent here — described; the fourth column of the mapping table | — (a word of `skill_pre_aws_solution.md` § The mapping table; no identifier) | — | — | migration, deployment, a plan, a roadmap |
| an absent object — a primitive, an orchestration state, a skill — nothing local answers to and a document describes: a sentence ending, or a verdict reading, *absent here — described* | — (a phrase of the documents; no identifier) | — | — | planned, a debt marker, future, ghost, placeholder, missing |

## DevOps panel

The names of `module_monitoring/sub_module_devops` — the machines the
project runs on, and the three verbs offered for them. The contract is
`module_monitoring/skills/skill_devops_panel.md`.

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| the panel and its sub-module — named for the persona whose page it is | `sub_module_devops`; the compose service `devops` | — | DevOps | `portraefik` (the retired coinage), `sub_module_docker`, Portainer, Traefik, a tool's brand as a name, any routing the old name suggested |
| one container the daemon reports, whether or not this project owns it | `machine` — `machines` in the payload, `machine_row()` | `machines` | container | `node`, `host`, `instance` (an instance is the elsewhere column's host, § Pre-AWS direction); a foreign container hidden rather than listed |
| whether a container belongs to the project the panel itself runs in | `own_project`, compared on `com.docker.compose.project` read from the panel's own labels | `own_project`, `compose_project` | `own` | a match on service name or image; the project written as a literal |
| the whole set of state changes the panel offers | `CONTAINER_ACTIONS` = `("start", "stop", "restart")` | `actions` | start / stop / restart | `rm`, `exec`, `prune`, compose up/down from the browser, an action outside the tuple |
| the refusal of an action on another project's container | HTTP 403 with `refused` and `reason` | `refused`, `reason` | the reason, shown | a silent no-op, a disabled button as the only guard, a 404 that hides the reason |
| the panel's own API, proxied by the dashboard and reached by literal name from the page | `DEVOPS_ROUTE_PREFIX` = `/devops`, `devops_api_url()` | `GET /devops/api/{machines,networks,volumes,image,events}`, `POST /devops/api/machines/<id>/<action>` | — | a route on the dashboard that opens the socket; a second prefix for the same panel |
| what one machine row publishes about a container | `machine_row()` | `container_id`, `name`, `compose_project`, `compose_service`, `own_project`, `state`, `image`, `started_at_utc`, `restart_count`, `ports`, `memory_bytes`, `memory_limit_bytes`, `cpu_usage_seconds`, `cpu_count` | the container table's columns | a key the page does not read; `mem`, `cpu_pct`, a bare duration for uptime |
| how often the panel asks again | `CONTAINER_POLL_INTERVAL_SECONDS` in `module_monitoring/config.py`, published by `machines_payload()` | `poll_interval_seconds` | — | a cadence literal in the page |
| what the three engine inventories publish beside the machines | `networks_payload()`, `volumes_payload()`, `image_payload()` | `networks` with `name`, `driver`, `scope`, `attached`, `compose_project`, `own_project`; `volumes` with `name`, `driver`, `size_bytes`, `reference_count`, `compose_project`, `own_project`; `bind_mounts` with `source`, `destination`, `writable`, `containers`; the image as `image`, `image_id`, `size_bytes`, `created_utc`, `repo_tags` | the networks, volumes, bind-mount and image tables | a hash as an image identity; a volume size the daemon did not report |
| one daemon event of this project, over a doubly bounded window | `events_payload()` | `events` with `time_utc`, `type`, `action`, `name`, `compose_service` | the events table | an unbounded `/events`; a host's other stacks in this project's tail |
| an action the container's state already satisfies | HTTP 304 from the engine, forwarded with no body | — (the status is the answer) | `changed nothing … already in that state` | `refused` for a 304; an error style for a success |
| a control that leaves a page for another persona's page | `.jump` | — | DevOps / Status | a second class for a jump, a tab for a machine view |
| the toolkit every page loads before its own sections | `page.js` | — | — | `utils.js`, `common.js`, `shared.js`, `lib.js`; a page-specific element written from it |
| the one selector component of both pages — the top tabs, the summary views, the ticker rows — each group wired by its `data-key` | `.pills`, `.pill`, `.pill--active`, `initPills()`, `PILL_HOOKS` in `page.js` | — | — | a second selector component |

The page's navigation: the
tabs *Pipeline*, *Data Quality*, *ML Research*, *ML Assets*, *Scalability*, *Lifecycle*, the
jump *DevOps*, and the ML Assets views *Labels & data*,
*Classification*, *Strategy*, *Search*, *Feature set*.

## Scalability crawler

The names of `module_skills/sub_module_scalability_crawler` — each file a hand
lists, read against the skills a hand marks for it. The rules are
`module_skills/skill_scalability_crawler.md`, and the standards of its screens
`module_skills/skill_tui_designer.md`, the canon's, which every TUI of this tree obeys.

| concept | code | artifact key | UI label | never |
|---|---|---|---|---|
| the crawler: the canon's sub-module that reads each file a hand lists against the skills a hand marks for it, writes a report a hand reads, and its snapshot — a crawler because it walks the listed files as a crawler walks pages, and scalability because it keeps what makes the code scale, the generic, algorithmic conventions | `sub_module_scalability_crawler`; `make skills-crawl` | — | — | a linter, a check, a gate, a CI step; a web crawler, walking sites or services to gather what they hold; conformance, review — names that tell a reader nothing |
| the skill matrix: `to_crawl.md`, a Markdown table kept by a hand — a row per entry, its `path` a path from the root naming a file or a folder, a folder every file under it but `__pycache__` and the reports; a column per skill; a mark where that skill acts on the crawl of the entry's files; its rows' order is the crawl's queue | `to_crawl.md`, `TO_CRAWL_MD_PATH`, `load_skill_matrix()`, `load_crawl_paths()`, `load_entry_paths()`, `write_skill_matrix()`, `SKILL_MATRIX_PATH_COLUMN` | — | path | the list; the matrix or the table, alone; grid, checklist; `to_crawl.txt`; a mark read off the module a skill sits in; rows derived from the tree; the whole tree by default |
| a skill column: one skill of the tree, headed by its file's stem — every `module_*/skills/*.md`, `module_skills/skill_*.md` and `module_*/sub_module_*/skill_*.md`, in the byte order of their paths; read off the tree at every read, written into the header by every write | `SKILL_PATHS`, `load_skill_paths()` | — | the stem (`skill_determinism`, `methodology_ml`, `skill_tui_designer`) | a column kept by hand; a column for `AGENTS.md`, the register or an orientation; a skill's title, path or abbreviation as its header; two skills of one stem |
| a mark: `X` in a skill column of an entry's row — that skill is sent with every file the entry names; an empty cell leaves it unmarked, named to the agent by its path alone; a hand's decision, in the file or through the TUI; a file two entries name takes the marks of both | `SKILL_MARK` | — | `X`; marked; unmarked | assign, tag, tick, check, enable; `x`, `✓` or `yes` in a cell; a mark a crawl writes; `X` as a state word |
| the documents sent with every file, never a column: the contract, the register and the orientation of the module the file's first path segment names — of which a root file, or one under `module_skills/`, has none | `SENT_DOCUMENT_PATHS` | — | — | a column for one of them; one of them left unsent; the canon's skills sent with every file |
| the mission: what the agent reports of one file, and how | `crawlers_mission.md`, `CRAWLERS_MISSION_MD_PATH` | — | — | a rule restated in it; a work order or a plan |
| the rules sent with a file, each under its path: the documents sent with every file under `# Rules`, then the skills its row marks under `# Skills marked for this file`, in the columns' order | `load_rules_text()` | — | — | a rule summarised for the message; an unmarked skill's text in the message; a list of rules kept per module |
| one file's message: the mission, the rules and the marked skills, `# Skills not marked for this file` — every other skill by its path alone — then the file with every line after its number; the mission's section *Skills to mark* names an unmarked skill the file looks governed by | `build_message()`; `crawlers_mission.md` | — | — | a prompt per module; a line number the agent has to count; an unmarked skill left unnamed, quoted or cited as a departure |
| the sub-module's folder and the checkout's root: where its own files are read, and where a listed path and a rule are | `SUB_MODULE_DIR`, `REPO_ROOT` | — | — | a host path; a listed path read from the working directory |
| a vendor: an agent's command line a crawl sends each chosen file to — one table of `vendors_for_crawling.toml`, one fresh session per chosen file | `vendors_for_crawling.toml` with `active`, `command` and its forms; `VENDORS_FOR_CRAWLING_TOML_PATH`, `load_active_vendors()`, `AGENT_TIMEOUT_MINUTES` | — | vendor; on PATH; command | an API key; a vendor named in the code; an interactive session; a vendor active before one run on one file showed it answers from the message alone |
| a form: one decision of an action — the vendor; each form of the vendor's table, `model`, `effort`, `permissions`, in that order, a list of options, each a `label` shown with its `args` and the `args` appended to the command line, the first preselected and a form of one option answered without asking; the files to crawl; the path to add and its skills, the matches of `SKILL_PRESELECTED_PATHS` preselected — the canon's, those of its module and those in its folder or a folder above it; the path to mark and its skills, its marks preselected; the path to remove | `build_command()`, `VENDOR_FORMS`, `load_preselected_skills()`, `_skills_answer()` in `crawl.py`; `SKILL_PRESELECTED_PATHS`; `model`, `effort`, `permissions` with `label`, `args` | — | vendor; model; effort; permissions; label; args; files to crawl; path to add; skills for <path>; skill; path to mark; path to remove | two decisions on one form; an option's `args` left out on a terminal wide enough for them, or left out unsaid; a flag known to the code; a remembered choice; a form asked that the vendor's table lacks; a first `permissions` option that lets the agent use a tool |
| a file's report: one entry per crawl, the heading `## crawled <YYYY-MM-DD HH:MM> UTC · <vendor> · <labels> · <short commit> · skills: <stems>` — the stems of the skills sent, in the columns' order, `none` when its row marks none — and the answer as it came | `reports_after_crawled_files/<path>.md`, `REPORTS_AFTER_CRAWLED_FILES_DIR`, `report_path()`, `write_report_entry()`, `REPORT_HEADING_PREFIX`, `_skills_field()` | `report` | report | a skill in the heading that was not sent; a report overwritten or summarised; a report in a store; a dated review of the root, `REPORT_<subject>.md` (§ Documentation ownership) |
| the TUI — text-based user interface: every screen `make skills-crawl` draws, from the header block to the outcome, to the standards of `skill_tui_designer.md` | `main()` and `_skill_rows()` in `crawl.py`, drawn through `tui.py`; `make skills-crawl`; `-h`, `--help` | — | Scalability crawler; `<n> paths listed · <s> skills · <m> files · <k> crawled · <j> never crawled`; the listed paths table: #, path, kind (file, folder), files, crawled (`<k> / <n>`); the skill matrix turned: skill, then the # of each listed path, `X` or empty; `left out at <n> columns: <names>` | a main loop or a second menu after the action — the program ends; a remembered choice; an argument but `-h`, `--help` (`--json`, `--no-input`, `--simple`, `--a11y`, `--no-color`, `--no-animation`); the branch or the repository's name in the header; `target` for a listed path, `DIRECTORY` for a folder; a crawl scheduled or detached; the menu, for the whole of it |
| the menu: the choice of one action, under the listed paths and the skill matrix | `main()` in `crawl.py` | — | action; crawl, add a path, mark skills, remove a path, quit | `exit` as an option (§ Run record's exit code); a second menu after the action; *back* to it |
| the steps table: every step of a crawl in order, above the step it asks — each answered DONE with its choice, the one asked CURRENT, the rest PENDING | `_step_rows()`, `_step_answer()` in `crawl.py` | — | step; state; choice; select now; the vendor's forms; plan | `workflow` (`AGENTS.md` § Rejected vocabulary), wizard, stepper; a step assumed before the vendor's table names it; the steps of two actions |
| the plan: the last screen of a crawl before any agent is called — the choices, the command line, the report heading and the files — and its gate | `_write_crawl_reports()` in `crawl.py` | — | parameter; value; timeout per file; reports; command; report heading; `skills: <each file's marked skills>`; skills; `crawl <n> files with <vendor>?`; crawl; back; cancel | an agent called before *crawl*; *run* (§ Run record); a plan written into the tree; a gate that refuses what a hand confirms |
| the preview and the remove's block: what an add or a remove writes, shown before `write_skill_matrix()` writes it — the path, its kind, its files and its skills; the row that leaves `to_crawl.md`, no file and no report deleted — and their gates | `load_repository_paths()`, `_write_added_path()`, `_write_removed_path()` in `crawl.py`; `PREVIEW_TABLE_LIMIT_ROWS` | — | repository root; `resolving <path> …`; path; kind; files; skills; writes; `one row at the end of to_crawl.md`; `… <k> more, <n> files in all`; `add <path> to to_crawl.md?`; add; `removes its row from to_crawl.md`; `deletes a file of the repository`; `deletes its reports`; `remove <path> from to_crawl.md?`; remove; back; cancel | a skill matrix written before its gate; a remove said to delete a file or a report; a path git ignores offered; a listed path offered again |
| mark skills: the action that changes one entry's marks — the path to mark, the skills form, the changes table and its gate — writing the skill matrix and nothing else | `_write_marked_skills()` in `crawl.py`; `write_skill_matrix()` | — | mark skills; `path to mark`; the changes table: skill, now, after; `no mark changes`; `mark <path> in to_crawl.md?`; mark; back; cancel; `marked <path> in to_crawl.md · <k> of <n> skills · <c> changed` | assign skills, edit, tag; a mark written before its gate; an unchanged skill in the changes table |
| a crawl's progress and outcome: a line before each file, one line after it, the results table and the outcome last | `_write_crawl_reports()` in `crawl.py` | — | `[<i>/<n>] CRAWLING <path> · <vendor>`; `[<i>/<n>] DONE <path> <s> s`; result; time; `crawled <k> of <n> files with <vendor> · <labels>`; `wrote <snapshot>` | a spinner, a progress bar, a percentage, a line redrawn in place; an answer summarised on the screen — the report holds it |
| the failure block and the exits: a failure on stderr as what failed, where, why and what next, the run's last — 0 an action carried out or cancelled, 1 a failure, 2 an unknown argument, 130 Ctrl-C | `error_lines()`, `INTERRUPTED_EXIT_CODE` in `tui.py`; `_failure_exit_code()`, `_cancelled_exit_code()` in `crawl.py` | — | where; why; next; `nothing written`; `interrupted by Ctrl-C` | a traceback for an expected failure; a failure on stdout; exit 0 after a failure |
| a state word: the closed list of words that say how a step, a file or an action stands — its symbol and colour beside it in normal output, the word in brackets in plain output | `STATE_SYMBOLS`, `STATE_COLOURS`, `state_label()` in `tui.py` | — | DONE; CURRENT; CRAWLING; PENDING; NOT CRAWLED; WARN; CANCELLED; FAILED; ERROR | a colour or a symbol without its word; a coloured row (`AGENTS.md` § Rejected vocabulary); `running`, `ok`, `success`; `never` as a state — it is a value of last crawl (UTC) |
| plain output: the screens without colour, symbol or border, chosen by the environment alone — `NO_COLOR` set and not empty, `TERM=dumb`, or standard output not a terminal | `OUTPUT_PLAIN` in `config.py` | — | `[<word>]` | a flag (`--no-color`, `--simple`, `--a11y`); a theme or a gum configuration in the tree; a meaning a colour alone carries |
| gum: the terminal instrument the TUI speaks — `gum table --print`, `gum style`, `gum choose`, `gum filter`; gum 2, a binary of the host | `gum`, over `subprocess` in `tui.py` alone: `gum_table()`, `gum_style()`, `gum_choose()`, `gum_filter()`, `_gum()` | — | — | a Python dependency, Rich among them; a chooser, a table or a colour written here over curses or escape codes; a gum configuration in the tree; `gum spin`, `gum confirm`, `gum input`; gum's own pink and purple |
| the snapshot: every listed file, how often it was crawled and when last, read off the dates of its report's headings — a heading's skills enter no row | `SKILLS_STATUS_JSON_PATH`, `load_file_row()`, `build_skills_status()` in `status.py`; `make skills-status` | `skills_status.json`: `files` with `path`, `report`, `crawl_count`, `last_crawled_utc` | file, crawls, last crawl (UTC) | a clock in the snapshot; a snapshot that reads itself back |
| a file's age: its last crawl against the browser's clock, drawn and never stored | `formatAgeDays()` in `scalability.js` | — | age (days) | a stored age |
| the page's view of the reports | `scalability.js`; `SKILLS_STATUS` | — | Scalability — CRAWL ACTUALITY | a tab named for a tool; scale for a larger basket, which is `ASSET=<TICKER>` (`AGENTS.md` § Pre-AWS architectural direction) |
