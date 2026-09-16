"""Frozen-parameter training: out-of-fold predictions per validation fold with the two importances of that fold's
booster, then the final-holdout report — the numbers are persisted, the model is not."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import config, dataset, model, validation


def write_predictions(ticker: str, cat: dict, rows: list[tuple]) -> Path:
    return dataset.write_parquet(
        config.oos_predictions_parquet(ticker, cat),
        {"decision_ts": "BIGINT", "oos_fold_id": "TINYINT",
         "p_short": "DOUBLE", "p_neutral": "DOUBLE", "p_long": "DOUBLE"},
        ([int(r[0]), int(r[1])] + [repr(float(v)) for v in r[2:]] for r in rows),
        order_by="oos_fold_id, decision_ts",
    )


def to_oos_predictions(prediction_records: list[tuple]) -> dict[str, np.ndarray]:
    """The prediction records as strategy.load_oos_predictions returns them: fold-major, by decision, the
    probabilities widened to float64 exactly as the parquet round trip widens them — so a search that never
    writes the parquet replays the strategy on the same numbers the stage would."""
    return {
        "decision_ts": np.array([row[0] for row in prediction_records], dtype=np.int64),
        "oos_fold_id": np.array([row[1] for row in prediction_records], dtype=np.int8),
        "p_short": np.array([row[2] for row in prediction_records], dtype=np.float64),
        "p_neutral": np.array([row[3] for row in prediction_records], dtype=np.float64),
        "p_long": np.array([row[4] for row in prediction_records], dtype=np.float64),
    }


def fold_metrics(y_cls, proba, weight, prior_train) -> dict:
    """Model log-loss against the training class prior: relative_logloss_skill = 1 - model / prior."""
    model_logloss = validation.multiclass_logloss(y_cls, proba, weight)
    prior_logloss = validation.prior_logloss(prior_train, y_cls, weight)
    return {
        "prior_logloss": prior_logloss,
        "model_logloss": model_logloss,
        "relative_logloss_skill": 1.0 - model_logloss / prior_logloss,
        "scored_row_count": int(y_cls.size),
    }


def fold_importance_block(booster, xy: dict, fold_id: int) -> dict:
    """The two importances of one validation fold's booster, the SHAP values measured on the fold's scoring rows."""
    oos_start, oos_end = validation.fold_bounds(fold_id)
    scoring_rows, _ = validation.scoring_set(
        xy["decision_ts"], xy["entry_ts"], xy["event_end_ts"], xy["sample_valid"], oos_start, oos_end,
        xy["barriers"]["horizon_minutes"])
    return {
        "gain_importance": model.gain_importance(booster, xy["feature_columns"]),
        "mean_abs_shap_importance": model.mean_abs_shap_importance(booster, xy["x"][scoring_rows], xy["feature_columns"]),
    }


def fold_evaluation(xy: dict, y_cls: np.ndarray, best: dict, fold_id: int) -> tuple[dict, dict, list[tuple], object]:
    """Fit before the fold's window, predict the FULL window, score the supervised
    subset only. Returns (metrics, segment, prediction_records, booster)."""
    oos_start, oos_end = validation.fold_bounds(fold_id)
    training_rows, train_weight = validation.training_set(
        xy["entry_ts"], xy["event_end_ts"], xy["sample_valid"], oos_start)
    window_rows = validation.prediction_window(xy["decision_ts"], oos_start, oos_end)
    scoring_rows, scoring_weight = validation.scoring_set(
        xy["decision_ts"], xy["entry_ts"], xy["event_end_ts"],
        xy["sample_valid"], oos_start, oos_end, xy["barriers"]["horizon_minutes"])
    prior_train = validation.weighted_class_prior(y_cls[training_rows], train_weight)
    booster = model.fit(best, xy["x"][training_rows], xy["y"][training_rows], train_weight, xy["feature_columns"])
    window_proba = model.predict_proba(booster, xy["x"][window_rows], xy["feature_columns"])
    pos = np.searchsorted(window_rows, scoring_rows)   # scoring_rows ⊂ window_rows
    metrics = fold_metrics(y_cls[scoring_rows], window_proba[pos], scoring_weight, prior_train)
    prediction_records = [
        (xy["decision_ts"][i], fold_id, window_proba[k, 0], window_proba[k, 1], window_proba[k, 2])
        for k, i in enumerate(window_rows)
    ]
    eligible = int((xy["sample_valid"] & (xy["decision_ts"] < oos_start)).sum())
    segment = {
        "training_row_count": int(training_rows.size),
        "purged_event_count": eligible - int(training_rows.size),
        "window_row_count": int(window_rows.size),
        "scored_row_count": int(scoring_rows.size),
    }
    return metrics, segment, prediction_records, booster


def main() -> int:
    args = config.build_ticker_parser("frozen-parameter training and the final-holdout report").parse_args()

    for ticker in config.parse_tickers(args.tickers):
        best = dataset.load_json(config.parameters_json(ticker))["hyperparameter_search_result"]["best_params"]
        xy = dataset.load_xy(ticker)
        y_cls = model.to_class(xy["y"])

        prediction_records, per_fold, segments, validation_importance = [], {}, {}, {}
        for fold_id in config.VALIDATION_FOLD_IDS:
            metrics, segments[f"fold_{fold_id}"], rows, booster = fold_evaluation(xy, y_cls, best, fold_id)
            per_fold[f"fold_{fold_id}"] = metrics
            validation_importance[f"fold_{fold_id}"] = fold_importance_block(booster, xy, fold_id)
            prediction_records.extend(rows)

        # the final holdout: fitted on everything before it, never used for a choice — and never attributed,
        # so that no importance of it can be read
        final_holdout, segments[f"fold_{config.FINAL_HOLDOUT_FOLD_ID}"], rows, _ = fold_evaluation(
            xy, y_cls, best, config.FINAL_HOLDOUT_FOLD_ID)
        prediction_records.extend(rows)
        write_predictions(ticker, xy["catalogue"], prediction_records)

        trainable = xy["sample_valid"]
        payload = {
            "validation": per_fold,
            "final_holdout": final_holdout,
            "validation_importance": validation_importance,
            "feature_columns": list(xy["feature_columns"]),
            # classes over the supervised population only: an ambiguous event carries y = 0 in the file
            "class_counts": {
                "short": int((trainable & (xy["y"] == -1)).sum()),
                "neutral": int((trainable & (xy["y"] == 0)).sum()),
                "long": int((trainable & (xy["y"] == 1)).sum()),
            },
            "labels": {
                "decision_count": int(xy["y"].size),
                "ambiguous_event_count": int((~xy["label_valid"]).sum()),
                "unobservable_entry_count": int((~xy["entry_observable"]).sum()),
                "trainable_row_count": int(trainable.sum()),
            },
            "segments": {
                **segments,
                "warmup_excluded_decision_count": (xy["catalogue"]["warmup_end_ms"] - config.RESEARCH_START_MS)
                // config.timeframe_entry(xy["catalogue"], xy["catalogue"]["decision_timeframe"])["duration_ms"],
            },
        }
        dataset.write_json(config.model_evaluation_json(ticker), payload)
        print(f"{ticker} model_evaluation: prior {final_holdout['prior_logloss']:.6f} "
              f"model {final_holdout['model_logloss']:.6f} "
              f"skill {final_holdout['relative_logloss_skill']:+.4f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
