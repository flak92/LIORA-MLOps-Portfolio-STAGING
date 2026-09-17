# BTC — research artifacts

Research window 2021-01-01 → 2026-08-26, seed 42. One directory per ticker, one file per distinct artifact responsibility; `BTC_parameters.json` next to this file is the one parameters file: its `hyperparameter_search_result` section is what the search chose, written when the search runs — the a-priori configuration is `module_ml/config.py` at the commit that ran it, not a copy in the folder.

## Files

| file | holds | size |
| --- | --- | --- |
| `BTC_README.md` | this file | — |
| `BTC_barriers.json` | the promoted barrier geometry: the two multipliers of a trade, the label's own and the horizon token — a hand's choice; absent, the frozen constants are the asset's | — |
| `BTC_catalogue.json` | the feature layer's contract: the timeframes and their slots, the warm-up, the columns offered per timeframe and the default set — read once per stage | 2 KB |
| `BTC_coordinate_search.json` | where the coordinate search stands at a round boundary: its inputs, the beam, the champion, the path it took and the proposals, each trial named by its index into the ledger | — |
| `BTC_coordinate_search_profile.json` | the search profile: the columns admitted, the state to start from, each coordinate's grid and the loops of a round — drafted by a hand | — |
| `BTC_coordinate_search_trials.jsonl` | the coordinate search's ledger: one scored state a line, appended and never rewritten | — |
| `BTC_feature_set.json` | the promoted feature set: its columns per timeframe, a hand's choice — absent, the default set is the asset's | — |
| `BTC_features_ss-15-hh-dd-MM.parquet` | the catalogue on 15m — every definition offered on it, on the decision grid | 10,699 KB |
| `BTC_features_ss-mm-01-dd-MM.parquet` | the catalogue on 1h — every definition offered on it, on the decision grid | 2,950 KB |
| `BTC_features_ss-mm-04-dd-MM.parquet` | the catalogue on 4h — every definition offered on it, on the decision grid | 1,667 KB |
| `BTC_label_events_ss-15-hh-dd-MM.parquet` | Y — triple-barrier outcome and the event prices | 5,265 KB |
| `BTC_model_evaluation.json` | classification metrics per fold | 7 KB |
| `BTC_oos_predictions_ss-15-hh-dd-MM.parquet` | out-of-sample class probabilities, full windows | 2,401 KB |
| `BTC_parameters.json` | the one parameters file: what the search chose | 385 B |
| `BTC_strategy_evaluation.json` | threshold, PnL and the equity curve | 10 KB |

Each of the 3 catalogue parquets carries 16 rows more than `BTC_label_events_ss-15-hh-dd-MM.parquet`: the tail decisions whose full 240-minute horizon does not fit inside the research window have features but no label. `BTC_oos_predictions_ss-15-hh-dd-MM.parquet` holds the 4 out-of-sample prediction windows end to end; the metrics score only the supervised, horizon-fitting subset of each.

## Feature set

The default set of the catalogue — no promoted file. The asset's feature set by timeframe — the set every fit reads; the feature id is the column with the timeframe appended:

| timeframe | columns |
| --- | --- |
| 15m | `ema20_minus_ema50_over_atr14`, `centered_rsi14`, `atr14_over_close`, `range_position20`, `log_volume_zscore50` |
| 1h | `ema20_minus_ema50_over_atr14`, `centered_rsi14`, `atr14_over_close`, `range_position20`, `log_volume_zscore50` |
| 4h | `ema20_minus_ema50_over_atr14`, `centered_rsi14`, `atr14_over_close`, `range_position20`, `log_volume_zscore50` |

## Labels

194,832 decisions, of which **194,825 supervised** (99.996%) — 7 events resolve ambiguously and 0 entry minutes printed no trade, so neither trains anything. Classes over the supervised population: short 26,601, neutral 144,031, long 24,193 (194,825 total).

## Model

Search: 8 Optuna trials, best best_cagr_validation_path 0.023147. Winner: depth 2, eta 0.2521, 300 rounds, subsample 0.904, colsample 0.652, min_child_weight 49, lambda 0.1568, alpha 0.2336.

| fold | prior log-loss | model log-loss | rel. skill | scored |
| --- | --- | --- | --- | --- |
| F2 | 0.873507 | 0.858845 | +1.68% | 35,023 |
| F3 | 0.918886 | 0.830163 | +9.66% | 35,018 |
| F4 | 0.877705 | 0.805139 | +8.27% | 35,120 |
| **F5 — final holdout** | 0.866520 | 0.799422 | +7.74% | 57,776 |

## Fold geometry

| fold | trained on | purged | window | scored |
| --- | --- | --- | --- | --- |
| F2 | 31,824 | 16 | 35,040 | 35,023 |
| F3 | 66,875 | 4 | 35,040 | 35,018 |
| F4 | 101,908 | 5 | 35,136 | 35,120 |
| F5 | 137,033 | 16 | 57,776 | 57,776 |

`purged` counts the training events that had not finished before the fold opened; they are dropped, never truncated. Average-uniqueness weights are measured on each of these populations separately, after the purge.

## Strategy

Entry edge threshold **0.44**. Cost 0.06% per side; the hierarchy gate requires the side to match the 4h trend sign with at least 2 of 3 timeframes agreeing.

| fold | Sharpe | maxDD | trades | hit rate | exposure | final equity |
| --- | --- | --- | --- | --- | --- | --- |
| F2 | +0.843 | 8.3% | 60 | 50.0% | 2.08% | 1.0780 |
| F3 | +0.671 | 4.7% | 52 | 50.0% | 1.50% | 1.0368 |
| F4 | -0.747 | 7.9% | 31 | 41.9% | 1.06% | 0.9583 |
| **F5 — final holdout** | -1.347 | 15.3% | 62 | 37.1% | 1.29% | 0.8840 |

Final-holdout exits: upper_barrier 13, lower_barrier 13, vertical 36, ambiguous 0.

## Reproducing the ML artifacts in this folder

    python -m module_features.bars --tickers BTC && python -m module_features.catalogue --tickers BTC && python -m module_ml.labels --tickers BTC && python -m module_ml.hpo --tickers BTC && python -m module_ml.train --tickers BTC && python -m module_ml.strategy --tickers BTC && python -m module_ml.status --tickers BTC

The OHLCV lives in `BTC_research_ohlcv.duckdb` beside this file — the market object the whole chain reads, resident in the folder and outside the manifest above, because its size moves with every top-up and this file is promised byte-reproducible.

F5 never participates in feature definition, hyper-parameter selection, entry-edge-threshold selection or strategy-rule selection — folds F2, F3, F4 carry the data-driven selection of the hyper-parameters, the entry edge threshold and, once a set is promoted, the feature set. The method is in `module_ml/skills/methodology_ml.md`, the field names in `module_skills/glossary.md`.
