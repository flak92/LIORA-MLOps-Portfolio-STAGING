"""The ML reports: store/status/ml_status.json for the dashboard, and each asset's byte-reproducible
<TICKER>_README.md — assembled from the three per-asset result files, computing nothing of their own."""

from __future__ import annotations

from datetime import UTC, datetime


from . import config, coordinate_search, dataset, feature_set_search, hpo, strategy as strategy_module

EQUITY_CURVE_DOWNSAMPLE_INTERVAL_DAYS = 7          # daily equity grid -> weekly points for the sparkline


def sample_block(metrics: dict) -> dict:
    labels = metrics["labels"]
    return {
        "decision_count": labels["decision_count"],
        "ambiguous_event_count": labels["ambiguous_event_count"],
        "unobservable_entry_count": labels["unobservable_entry_count"],
        "trainable_row_count": labels["trainable_row_count"],
        "trainable_row_pct": round(100.0 * labels["trainable_row_count"] / labels["decision_count"], 4),
        "warmup_excluded_decision_count": metrics["segments"]["warmup_excluded_decision_count"],
        "class_counts": dict(metrics["class_counts"]),
    }


def hyperparameter_search_result_block(hyperparameter_search_result: dict) -> dict:
    return {
        "trial_count": hyperparameter_search_result["trial_count"],
        hpo.OBJECTIVE_KEY: round(hyperparameter_search_result[hpo.OBJECTIVE_KEY], 6),
        "best_params": dict(sorted(hyperparameter_search_result["best_params"].items())),
    }


def _classification_block(metrics_block: dict) -> dict:
    return {
        "prior_logloss": round(metrics_block["prior_logloss"], 6),
        "model_logloss": round(metrics_block["model_logloss"], 6),
        "relative_logloss_skill": round(metrics_block["relative_logloss_skill"], 6),
        "scored_row_count": metrics_block["scored_row_count"],
    }


def classification_block(metrics: dict) -> tuple[dict, dict]:
    """(validation per fold, final holdout)."""
    validation = {k: _classification_block(v) for k, v in sorted(metrics["validation"].items())}
    return validation, _classification_block(metrics["final_holdout"])


def equity_curve_block(curve: dict, final_equity: float) -> dict:
    """Weekly-sampled equity for the sparkline; the settled final value is appended when the stride misses it."""
    values = [round(v, 4) for v in curve["equity"][::EQUITY_CURVE_DOWNSAMPLE_INTERVAL_DAYS]]
    end = round(final_equity, 4)
    if values[-1] != end:
        values.append(end)
    return {"equity": values}


def _pnl_block(block: dict) -> dict:
    return {
        "sharpe": round(block["sharpe"], 3),
        "cagr": round(block["cagr"], 6),
        "max_drawdown": round(block["max_drawdown"], 4),
        "calmar": round(block["calmar"], 4),
        "profit_factor": config.rounded(block["profit_factor"], 4),
        "trade_count": block["trade_count"],
        "hit_rate": config.rounded(block["hit_rate"], 4),
        "average_trade_return": config.rounded(block["average_trade_return"], 6),
        "exposure": round(block["exposure"], 4),
        "final_equity": round(block["final_equity"], 4),
        "exit_counts": dict(block["exit_counts"]),
    }


def strategy_block(strategy: dict) -> dict:
    final_holdout = strategy["final_holdout"]
    return {
        "entry_edge_threshold": strategy["entry_edge_threshold"],
        "entry_edge_threshold_constraint_met":
            strategy["entry_edge_threshold_constraint_met"],
        # what the chosen threshold was chosen out of, carried verbatim: the page states the spread beside
        # the score rather than computing it, and a reader who wants a correction has the count to make it
        **{name: strategy[name] for name in strategy_module.SELECTION_EXPOSURE_KEYS},
        strategy_module.SELECTION_SCORE_KEY: config.rounded(strategy[strategy_module.SELECTION_SCORE_KEY], 6),
        "execution_cost_rate_per_trade_side": strategy["execution_cost_rate_per_trade_side"],
        "validation": {k: _pnl_block(v) for k, v in sorted(strategy["validation"].items())},
        "validation_path": {k: config.rounded(v, 6) if isinstance(v, float) or v is None else v
                            for k, v in sorted(strategy["validation_path"].items())},
        "final_holdout": _pnl_block(final_holdout),
        "equity_curve": equity_curve_block(final_holdout["equity_curve"],
                                   final_holdout["final_equity"]),
    }


def proposal_block(proposal: dict, trial: dict, active_columns_by_timeframe: dict, timeframes: tuple[str, ...]) -> dict:
    """One proposal as the page reads it: its rank and trial from the state file, and everything else from that
    trial's line of the ledger — the columns it moves against the state the search was run on, the model's skill,
    then what the strategy would do."""
    columns_by_timeframe = trial["columns_by_timeframe"]
    return {
        "proposal": proposal["proposal"],
        "trial_index": proposal["trial_index"],
        "added_columns_by_timeframe": feature_set_search.columns_added(columns_by_timeframe, active_columns_by_timeframe, timeframes),
        "removed_columns_by_timeframe": feature_set_search.columns_removed(columns_by_timeframe, active_columns_by_timeframe, timeframes),
        "mean_relative_logloss_skill": round(trial["mean_relative_logloss_skill"], 6),
        "validation": {fold: {"relative_logloss_skill": round(block["relative_logloss_skill"], 6),
                              "sharpe": round(block["sharpe"], 3),
                              "cagr": round(block["cagr"], 6), "calmar": round(block["calmar"], 4),
                              "profit_factor": config.rounded(block["profit_factor"], 4),
                              "trade_count": block["trade_count"]}
                       for fold, block in sorted(trial["validation"].items())},
        "validation_path": {k: config.rounded(v, 6) if isinstance(v, float) or v is None else v
                            for k, v in sorted(trial["validation_path"].items())},
        "entry_edge_threshold": trial["entry_edge_threshold"],
        "entry_edge_threshold_constraint_met": trial["entry_edge_threshold_constraint_met"],
        strategy_module.SELECTION_SCORE_KEY: config.rounded(trial[strategy_module.SELECTION_SCORE_KEY], 6),
    }


def feature_set_block(ticker: str, cat: dict) -> dict:
    """Where the asset's feature set came from — the promoted file when it exists, else the default set of the
    catalogue — and the columns it holds by timeframe."""
    return {"source": "promoted" if config.feature_set_json(ticker).exists() else "default",
            "columns_by_timeframe": dataset.load_feature_columns(ticker, cat)}


def coordinate_search_block(ticker: str, best_params: dict, active_columns_by_timeframe: dict,
                            active_barriers: dict, cat: dict) -> dict | None:
    """The coordinate search as it last wrote itself, and whether its inputs are still the asset's — a
    promotion, a retuning, a catalogue change, an edited profile or a flipped selection makes a recorded
    search describe a state that has gone; None while the asset has no search file, and false rather than
    an error while it has no profile."""
    path = config.coordinate_search_json(ticker)
    profile_path = config.coordinate_search_profile_json(ticker)
    if not path.exists():
        return None
    search = dataset.load_json(path)
    ledger = config.coordinate_search_trials_jsonl(ticker)
    # the trials are the ledger's lines, and a proposal is read off the line its index names; how many points
    # each loop put through a fit is the search's own number, written once at a round boundary and copied
    # here — the page, the terminal and the state file show one number because one of them computed it
    trials = dataset.load_jsonl(ledger) if ledger.exists() else []
    inputs_current = profile_path.exists() and search["inputs"] == dataset.to_json_safe(
        coordinate_search.build_search_inputs(best_params, active_columns_by_timeframe, active_barriers,
                                              cat, dataset.load_json(profile_path)))
    return {
        "trial_count": len(trials),
        "trial_count_by_loop": search["trial_count_by_loop"],
        "round_count": search["round_count"],
        "search_converged": search["search_converged"],
        "champion_trial_index": search["champion_trial_index"],
        "inputs_current": inputs_current,
        # a search whose inputs have gone describes another experiment, and its proposals are numbers of
        # that one: the page shows none of them, and the snapshot publishes none either
        "proposals": [proposal_block(proposal, trials[proposal["trial_index"] - 1],
                                     search["inputs"]["active_columns_by_timeframe"], config.timeframes(cat))
                      for proposal in search["proposals"]] if inputs_current else [],
    }


# the rounding of each importance as the page shows it: gain is a sum of gains, the SHAP value a margin
IMPORTANCE_ROUNDING_DIGITS = {"gain_importance": 1, "mean_abs_shap_importance": 6}


def validation_importance_block(validation_importance: dict) -> dict:
    """The two importances of every validation booster, per column, rounded — the page takes their means."""
    return {fold: {measure: {column: round(value, IMPORTANCE_ROUNDING_DIGITS[measure])
                             for column, value in sorted(block[measure].items())}
                   for measure in IMPORTANCE_ROUNDING_DIGITS}
            for fold, block in sorted(validation_importance.items())}


def asset_report(ticker: str, cat: dict, hyperparameter_search_result: dict, metrics: dict, strategy: dict) -> dict:
    validation, final_holdout = classification_block(metrics)
    feature_set = feature_set_block(ticker, cat)
    return {
        "ticker": ticker,
        "sample": sample_block(metrics),
        "hyperparameter_search_result": hyperparameter_search_result_block(hyperparameter_search_result),
        "validation": validation,
        "final_holdout": final_holdout,
        "feature_columns": list(metrics["feature_columns"]),
        "feature_set": feature_set,
        "validation_importance": validation_importance_block(metrics["validation_importance"]),
        "coordinate_search": coordinate_search_block(ticker, hyperparameter_search_result["best_params"],
                                                     feature_set["columns_by_timeframe"],
                                                     dataset.load_barriers(ticker), cat),
        "strategy": strategy_block(strategy),
    }


# the files of a hand's stage — drafted by a hand, written by the search a hand starts, or promoted by one. A file of a
# hand's stage is listed, not measured: its size moves with the hand, not with the chain, and the README is promised
# byte-reproducible by the chain alone
HAND_STAGE_FILE_DESCRIPTORS = (config.barriers_json, config.coordinate_search_json, config.coordinate_search_profile_json,
                               config.coordinate_search_trials_jsonl, config.feature_set_json)


def file_manifest(ticker: str, cat: dict) -> list[tuple]:
    """The asset folder manifest in LC_COLLATE=C listing order: (path, what it holds) — one row per timeframe of the
    hierarchy for the catalogue parquets, which the slot standard sorts finest first, as LC_COLLATE=C does."""
    return [
        (config.asset_readme_md(ticker), "this file"),
        (config.barriers_json(ticker), "the promoted barrier geometry: the two multipliers of a trade, the label's own and the horizon token — a hand's choice; absent, the frozen constants are the asset's"),
        (config.catalogue_json(ticker), "the feature layer's contract: the timeframes and their slots, the warm-up, the columns offered per timeframe and the default set — read once per stage"),
        (config.coordinate_search_json(ticker), "where the coordinate search stands at a round boundary: its inputs, the beam, the champion, the path it took and the proposals, each trial named by its index into the ledger"),
        (config.coordinate_search_profile_json(ticker), "the search profile: the columns admitted, the state to start from, each coordinate's grid and the loops of a round — drafted by a hand"),
        (config.coordinate_search_trials_jsonl(ticker), "the coordinate search's ledger: one scored state a line, appended and never rewritten"),
        (config.feature_set_json(ticker), "the promoted feature set: its columns per timeframe, a hand's choice — absent, the default set is the asset's"),
        *((config.features_parquet(ticker, cat, timeframe), f"the catalogue on {timeframe} — every definition offered on it, on the decision grid")
          for timeframe in config.timeframes(cat)),
        (config.label_events_parquet(ticker, cat), "Y — triple-barrier outcome and the event prices"),
        (config.model_evaluation_json(ticker), "classification metrics per fold"),
        (config.oos_predictions_parquet(ticker, cat), "out-of-sample class probabilities, full windows"),
        (config.parameters_json(ticker), "the one parameters file: what the search chose"),
        (config.strategy_evaluation_json(ticker), "threshold, PnL and the equity curve"),
    ]


def load_file_size_text(path):
    if not path.exists():
        return "—"
    n = path.stat().st_size
    return f"{n:,} B" if n < config.BYTES_PER_KIBIBYTE else f"{n / config.BYTES_PER_KIBIBYTE:,.0f} KB"


def markdown_table_row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def markdown_table(headers, rows):
    return "\n".join([markdown_table_row(headers), markdown_table_row(["---"] * len(headers))] + [markdown_table_row(r) for r in rows])


def asset_readme(ticker: str, cat: dict, hyperparameter_search_result: dict, metrics: dict, strategy: dict) -> str:
    """What this folder holds and what came out of it — no timestamp, by design."""
    barriers = dataset.load_barriers(ticker)   # the asset's own horizon, as the labels were written with
    labels, counts = metrics["labels"], metrics["class_counts"]
    supervised = counts["short"] + counts["neutral"] + counts["long"]
    folds = [f"fold_{i}" for i in config.VALIDATION_FOLD_IDS]
    holdout = f"fold_{config.FINAL_HOLDOUT_FOLD_ID}"
    best_params = hyperparameter_search_result["best_params"]

    files = []
    for path, note in file_manifest(ticker, cat):
        # this file's own size would be self-referential: writing it changes it; a hand's stage is listed, not measured
        unmeasured = path == config.asset_readme_md(ticker) or path in {descriptor(ticker) for descriptor in HAND_STAGE_FILE_DESCRIPTORS}
        size = "—" if unmeasured else load_file_size_text(path)
        files.append([f"`{path.name}`", note, size])

    cls_rows = [[f"F{k.split('_')[1]}", f"{metrics['validation'][k]['prior_logloss']:.6f}",
                 f"{metrics['validation'][k]['model_logloss']:.6f}",
                 f"{100 * metrics['validation'][k]['relative_logloss_skill']:+.2f}%",
                 f"{metrics['validation'][k]['scored_row_count']:,}"]
                for k in folds]
    final_holdout_metrics = metrics["final_holdout"]
    cls_rows.append([f"**F{config.FINAL_HOLDOUT_FOLD_ID} — final holdout**",
                     f"{final_holdout_metrics['prior_logloss']:.6f}", f"{final_holdout_metrics['model_logloss']:.6f}",
                     f"{100 * final_holdout_metrics['relative_logloss_skill']:+.2f}%",
                     f"{final_holdout_metrics['scored_row_count']:,}"])

    segments = metrics["segments"]
    geo_rows = [[f"F{k.split('_')[1]}", f"{segments[k]['training_row_count']:,}",
                 f"{segments[k]['purged_event_count']:,}", f"{segments[k]['window_row_count']:,}",
                 f"{segments[k]['scored_row_count']:,}"]
                for k in folds + [holdout]]

    def pnl_row(label, block):
        return [label, f"{block['sharpe']:+.3f}", f"{100 * block['max_drawdown']:.1f}%",
                f"{block['trade_count']:,}",
                f"{100 * block['hit_rate']:.1f}%" if block["hit_rate"] is not None else "—",
                f"{100 * block['exposure']:.2f}%", f"{block['final_equity']:.4f}"]

    feature_set = feature_set_block(ticker, cat)
    feature_set_rows = [[timeframe, ", ".join(f"`{column}`" for column in feature_set["columns_by_timeframe"][timeframe])
                         or "—"] for timeframe in config.timeframes(cat)]
    feature_set_source = ("The default set of the catalogue — no promoted file" if feature_set["source"] == "default"
                          else f"A promoted set — `{config.feature_set_json(ticker).name}`, a hand's choice; "
                               f"the commit history is the record")
    feature_set_reproduce_note = ("" if feature_set["source"] == "default" else
                                  f"`{config.feature_set_json(ticker).name}` must lie beside this file as well — every fit "
                                  f"reads the promoted set from it; absent, the chain reads the default set and the folder "
                                  f"it rebuilds is another one.\n\n")

    pnl_rows = [pnl_row(f"F{k.split('_')[1]}", strategy["validation"][k]) for k in folds]
    final_holdout_strategy = strategy["final_holdout"]
    pnl_rows.append(pnl_row(f"**F{config.FINAL_HOLDOUT_FOLD_ID} — final holdout**", final_holdout_strategy))
    exits = ", ".join(f"{name} {final_holdout_strategy['exit_counts'][name]}"
                     for name in config.EVENT_RESOLUTION_NAMES.values())
    fallback_note = ("" if strategy["entry_edge_threshold_constraint_met"]
                     else f" — **fallback**, no threshold reaches "
                          f"{config.MINIMUM_TRADES_PER_VALIDATION_FOLD} trades in every validation fold")

    reproduce = " ".join(
        [f"python -m module_features.{stage} --tickers {ticker} &&" for stage in ("bars", "catalogue")]
        + [f"python -m module_ml.{stage} --tickers {ticker} &&" for stage in ("labels", "hpo", "train", "strategy")]
    ) + f" python -m module_ml.status --tickers {ticker}"

    return f"""# {ticker} — research artifacts

Research window {config.RESEARCH_START_UTC} → {config.RESEARCH_END_UTC}, seed {config.SEED}. One directory per ticker, one file per distinct artifact responsibility; `{config.parameters_json(ticker).name}` next to this file is the one parameters file: its `hyperparameter_search_result` section is what the search chose, written when the search runs — the a-priori configuration is `module_ml/config.py` at the commit that ran it, not a copy in the folder.

## Files

{markdown_table(["file", "holds", "size"], files)}

Each of the {len(config.timeframes(cat))} catalogue parquets carries {barriers['horizon_minutes'] * config.MILLISECONDS_PER_MINUTE // config.timeframe_entry(cat, cat['decision_timeframe'])['duration_ms']} rows more than `{config.label_events_parquet(ticker, cat).name}`: the tail decisions whose full {barriers['horizon_minutes']}-minute horizon does not fit inside the research window have features but no label. `{config.oos_predictions_parquet(ticker, cat).name}` holds the {len(config.VALIDATION_FOLD_IDS) + 1} out-of-sample prediction windows end to end; the metrics score only the supervised, horizon-fitting subset of each.

## Feature set

{feature_set_source}. The asset's feature set by timeframe — the set every fit reads; the feature id is the column with the timeframe appended:

{markdown_table(["timeframe", "columns"], feature_set_rows)}

## Labels

{labels['decision_count']:,} decisions, of which **{labels['trainable_row_count']:,} supervised** ({100 * labels['trainable_row_count'] / labels['decision_count']:.3f}%) — {labels['ambiguous_event_count']:,} events resolve ambiguously and {labels['unobservable_entry_count']:,} entry minutes printed no trade, so neither trains anything. Classes over the supervised population: short {counts['short']:,}, neutral {counts['neutral']:,}, long {counts['long']:,} ({supervised:,} total).

## Model

Search: {hyperparameter_search_result['trial_count']} Optuna trials, best {hpo.OBJECTIVE_KEY} {hyperparameter_search_result[hpo.OBJECTIVE_KEY]:.6f}. Winner: depth {best_params['max_depth']}, eta {best_params['eta']:.4f}, {best_params['num_boost_round']} rounds, subsample {best_params['subsample']:.3f}, colsample {best_params['colsample_bytree']:.3f}, min_child_weight {best_params['min_child_weight']}, lambda {best_params['lambda']:.4f}, alpha {best_params['alpha']:.4f}.

{markdown_table(["fold", "prior log-loss", "model log-loss", "rel. skill", "scored"], cls_rows)}

## Fold geometry

{markdown_table(["fold", "trained on", "purged", "window", "scored"], geo_rows)}

`purged` counts the training events that had not finished before the fold opened; they are dropped, never truncated. Average-uniqueness weights are measured on each of these populations separately, after the purge.

## Strategy

Entry edge threshold **{strategy['entry_edge_threshold']}**{fallback_note}. Cost {100 * strategy['execution_cost_rate_per_trade_side']:.2f}% per side; the hierarchy gate requires the side to match the {config.trend_gate_timeframe(cat)} trend sign with at least {config.MINIMUM_AGREEING_TREND_TIMEFRAMES} of {len(config.timeframes(cat))} timeframes agreeing.

{markdown_table(["fold", "Sharpe", "maxDD", "trades", "hit rate", "exposure", "final equity"], pnl_rows)}

Final-holdout exits: {exits}.

## Reproducing the ML artifacts in this folder

    {reproduce}

The OHLCV lives in `{config.research_ohlcv_duckdb(ticker).name}` beside this file — the market object the whole chain reads, resident in the folder and outside the manifest above, because its size moves with every top-up and this file is promised byte-reproducible.

{feature_set_reproduce_note}F{config.FINAL_HOLDOUT_FOLD_ID} never participates in feature definition, hyper-parameter selection, entry-edge-threshold selection or strategy-rule selection — folds {', '.join('F' + str(i) for i in config.VALIDATION_FOLD_IDS)} carry the data-driven selection of the hyper-parameters, the entry edge threshold and, once a set is promoted, the feature set. The method is in `module_ml/skills/methodology_ml.md`, the field names in `module_skills/glossary.md`.
"""


def main() -> int:
    args = config.build_ticker_parser("aggregate ML artifacts -> store/status/ml_status.json").parse_args()
    # the payload folds over the tickers the launcher named; every complete asset among them gets its README
    tickers = config.parse_tickers(args.tickers)

    assets, envelope_contract = [], None
    for ticker in tickers:
        if not config.is_artifact_set_complete(ticker):
            continue
        if not config.catalogue_json(ticker).exists():   # artifacts from before the contract, or a hand's deletion
            print(f"{ticker}: no {config.catalogue_json(ticker).name} — run `make features-catalogue`", flush=True)
            continue
        cat = dataset.load_catalogue(ticker)
        envelope_contract = envelope_contract or cat
        hyperparameter_search_result = dataset.load_json(config.parameters_json(ticker))["hyperparameter_search_result"]
        metrics = dataset.load_json(config.model_evaluation_json(ticker))
        strategy = dataset.load_json(config.strategy_evaluation_json(ticker))
        assets.append(asset_report(ticker, cat, hyperparameter_search_result, metrics, strategy))
        config.asset_readme_md(ticker).write_text(asset_readme(ticker, cat, hyperparameter_search_result, metrics, strategy),
                                             encoding="utf-8")
    if not assets:
        raise SystemExit("no complete artifact set found — run `make ml-all` first")

    payload = {
        "generated_at_utc": datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "research_window": {"start_utc": config.RESEARCH_START_UTC,
                            "end_utc": config.RESEARCH_END_UTC,
                            "seed": config.SEED},
        # the one structural number the page needs to label the final fold
        "final_holdout_fold_id": config.FINAL_HOLDOUT_FOLD_ID,
        "minimum_agreeing_trend_timeframes": config.MINIMUM_AGREEING_TREND_TIMEFRAMES,
        # one asset's contract stands for the basket's envelope: one feature configuration wrote them all
        "trend_gate_feature": config.feature_id(config.TREND_GATE_FEATURE_DEFINITION, config.trend_gate_timeframe(envelope_contract)),
        "assets": assets,
    }
    out = config.ML_STATUS_JSON_PATH
    dataset.write_json(out, payload)

    for asset in assets:
        print(f"{asset['ticker']:5} "
              f"skill={asset['final_holdout']['relative_logloss_skill']:+.4f} "
              f"threshold={asset['strategy']['entry_edge_threshold']} "
              f"sharpe={asset['strategy']['final_holdout']['sharpe']} "
              f"trades={asset['strategy']['final_holdout']['trade_count']}")
    print(f"wrote {out} ({out.stat().st_size / config.BYTES_PER_KIBIBYTE:.1f} KB) "
          f"+ <TICKER>_README.md in {len(assets)} asset folders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
