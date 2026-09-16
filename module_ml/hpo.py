"""Optuna TPE per asset, sequential and seeded; the objective is the mean uniqueness-weighted log-loss over the
validation folds F2–F4. The final holdout is never touched here. Every point the search drew is left in the asset's
trial ledger, where the parameters file keeps only the one it chose; the ledger is this module's mlflow boundary."""

from __future__ import annotations

import mlflow
import numpy as np
import optuna

from . import config, dataset, model, validation


def log_trials(ticker: str, trials: list[dict]) -> None:
    """Every trial of the search: one mlflow run per trial, named `hpo_<n>` — its place in that search, counting from
    one — in the asset's own ledger, so two fanned-out processes share no path and no experiment id. The experiment
    is the ticker and is reused, so a rerun appends a search of its own, `hpo_1` again; the ledger only grows. mlflow's
    own vocabulary, its run id among it, begins and ends inside this call."""
    ledger = config.trials_sqlite(ticker)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{ledger}")
    mlflow.set_experiment(ticker)
    for index, trial in enumerate(trials, start=1):
        with mlflow.start_run(run_name=f"hpo_{index}"):
            mlflow.log_params(trial["params"])
            mlflow.log_metrics(trial["metrics"])


def build_objective(xy: dict[str, np.ndarray]):
    y_cls = model.to_class(xy["y"])
    folds = []
    for fold_id in config.VALIDATION_FOLD_IDS:
        oos_start, oos_end = validation.fold_bounds(fold_id)
        folds.append((
            validation.training_set(xy["entry_ts"], xy["event_end_ts"],
                                    xy["sample_valid"], oos_start),
            validation.scoring_set(xy["decision_ts"], xy["entry_ts"], xy["event_end_ts"],
                                   xy["sample_valid"], oos_start, oos_end,
                                   xy["barriers"]["horizon_minutes"]),
        ))

    def objective(trial: optuna.Trial) -> float:
        params = model.suggest_params(trial)
        losses = []
        for (training_rows, train_weight), (scoring_rows, scoring_weight) in folds:
            booster = model.fit(params, xy["x"][training_rows], xy["y"][training_rows], train_weight, xy["feature_columns"])
            proba = model.predict_proba(booster, xy["x"][scoring_rows], xy["feature_columns"])
            losses.append(validation.multiclass_logloss(y_cls[scoring_rows], proba, scoring_weight))
        return float(np.mean(losses))

    return objective


def search_hyperparameters(xy: dict) -> optuna.Study:
    """The asset's TPE search over the frozen space, sequential and seeded — the study itself, so a caller
    reads the point it chose, that point's value and every point it drew from one object."""
    study = optuna.create_study(
        direction="minimize", sampler=optuna.samplers.TPESampler(seed=config.SEED)
    )
    study.optimize(build_objective(xy),
                   n_trials=config.HYPERPARAMETER_SEARCH_TRIAL_COUNT, n_jobs=1)
    return study


def main() -> int:
    args = config.build_ticker_parser("Optuna TPE hyper-parameter search per asset").parse_args()
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    for ticker in config.parse_tickers(args.tickers):
        xy = dataset.load_xy(ticker)
        study = search_hyperparameters(xy)
        payload = {
            "hyperparameter_search_result": {
                "best_params": study.best_trial.params,
                "best_logloss": study.best_value,
                "trial_count": config.HYPERPARAMETER_SEARCH_TRIAL_COUNT,
            },
        }
        out = config.parameters_json(ticker)
        dataset.write_json(out, payload)
        log_trials(ticker, [{"params": trial.params,
                             "metrics": {"mean_validation_logloss": trial.value}}
                            for trial in study.trials])
        print(f"{ticker} {out.name}: best logloss {study.best_value:.6f} "
              f"(trial {study.best_trial.number})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
