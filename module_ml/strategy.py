"""Top-down gated strategy on the canonical research path.

    directional_probability_edge = p_long - p_short;  side = sign(edge)
    agreeing_trend_timeframe_count = #{timeframe : sign(TREND_GATE_FEATURE_DEFINITION_<timeframe>) == side}
    enter = |edge| >= entry_edge_threshold  AND  max(p_long, p_short) > p_neutral  AND  side != 0
            AND side == sign(TREND_GATE_FEATURE_DEFINITION_<TREND_GATE_TIMEFRAME>)
            AND agreeing_trend_timeframe_count >= 2
            AND entry_observable

USDT-perpetual PnL at a fixed quantity, linear in price (compounding per-bar returns would misprice shorts):

    Q      = s * E0 / P0                       notional 1x current equity
    R      = s * (Px/P0 - 1) - c - c * (Px/P0)  entry fee c*E0, exit fee c*|Q|*Px
    E_next = E0 * (1 + R)
    E_t    = E0 * (1 - c + s * (Pt/P0 - 1))     mark-to-market while open

A take-profit fills at the barrier, a stop at the worse of the barrier and the open of the touching minute. The
entry edge threshold is the grid point maximising the mean validation-fold Sharpe among those with at least
MINIMUM_TRADES_PER_VALIDATION_FOLD trades in every fold, ties to the smaller threshold.
"""

from __future__ import annotations

import duckdb
import numpy as np

from . import config, dataset, labels, validation

EQUITY_CURVE_SAMPLE_INTERVAL_MINUTES = 1440    # one equity point per day for the dashboard curve


def load_bars_1m(ticker: str) -> dict[str, np.ndarray]:
    """The canonical 1m series over the research window — the path the backtest re-walks for the
    trade's own barriers and marks the open position to. One loader, the labels', not a second."""
    con = duckdb.connect(str(config.research_ohlcv_duckdb(ticker)), read_only=True)
    con.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
    con.execute("SET threads=1")   # float summation must not be reordered
    bars_1m = labels.load_research_1m(con)
    con.close()
    return bars_1m


def load_oos_predictions(ticker: str, cat: dict) -> dict[str, np.ndarray]:
    """The out-of-sample windows as train.py wrote them, fold-major and by decision."""
    parquet_con = duckdb.connect()
    parquet_con.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
    parquet_con.execute("SET threads=1")   # float summation must not be reordered
    oos_predictions = parquet_con.execute(
        f"SELECT * FROM read_parquet('{config.oos_predictions_parquet(ticker, cat)}') ORDER BY oos_fold_id, decision_ts"
    ).fetchnumpy()
    parquet_con.close()
    return oos_predictions


def build_simulation_inputs(xy: dict, bars_1m: dict[str, np.ndarray], oos_predictions: dict[str, np.ndarray]) -> dict:
    """The strategy's inputs: X and Y, the 1m series, the predictions, and the trend definition on every timeframe,
    read from the catalogue by name — whatever the feature set holds."""
    trend = {timeframe: xy["catalogue_values"][config.feature_id(config.TREND_GATE_FEATURE_DEFINITION, timeframe)]
             for timeframe in xy["timeframes"]}
    return {"xy": xy, "bars_1m": bars_1m, "trend": trend, "oos_predictions": oos_predictions}


def load_simulation_inputs(ticker: str) -> dict:
    xy = dataset.load_xy(ticker)
    return build_simulation_inputs(xy, load_bars_1m(ticker), load_oos_predictions(ticker, xy["catalogue"]))


def trade_barriers(side: np.ndarray, entry_price: np.ndarray, upper_barrier: np.ndarray,
                   lower_barrier: np.ndarray, atr_barrier_multiplier: float,
                   take_profit_atr_multiplier: float,
                   stop_loss_atr_multiplier: float) -> tuple[np.ndarray, np.ndarray]:
    """The trade's own barriers in price order — take-profit above and stop below for a long, mirrored
    for a short: the label's own half-widths rescaled by what the trade asks of each side.

    At tp = sl = m every scale is x / x = 1.0 and 1.0 * d = d, so the trade's barriers are the label's
    to the bit, for every m. Recovering one sigma from the upper barrier instead — entry + (U - E)/m * tp
    — reproduces the upper barrier and misses the lower by one unit in the last place on 2 % of rows,
    which fill_price returns verbatim for a long stop: do not simplify this back to a sigma."""
    take_profit_scale = take_profit_atr_multiplier / atr_barrier_multiplier
    stop_loss_scale = stop_loss_atr_multiplier / atr_barrier_multiplier
    return (entry_price + np.where(side > 0, take_profit_scale, stop_loss_scale) * (upper_barrier - entry_price),
            entry_price - np.where(side > 0, stop_loss_scale, take_profit_scale) * (entry_price - lower_barrier))


def signals_for_fold(simulation_inputs: dict, fold_id: int) -> dict:
    """Signal arrays for one fold on the label-event grid, and the trade's own event re-walked on the 1m
    path for every entry the gate admits.

    The walked set — the gate open, the entry minute traded, the horizon inside the fold — depends on
    neither the threshold nor what the position was doing, so one walk serves the whole threshold grid:
    every trade any threshold realises is in it, and the threshold enters in backtest() alone."""
    xy = simulation_inputs["xy"]
    oos_predictions = simulation_inputs["oos_predictions"]
    in_fold = oos_predictions["oos_fold_id"] == fold_id
    ts = oos_predictions["decision_ts"][in_fold].astype(np.int64)
    pos = np.searchsorted(xy["decision_ts"], ts)
    p_short, p_long = oos_predictions["p_short"][in_fold], oos_predictions["p_long"][in_fold]
    p_neutral = oos_predictions["p_neutral"][in_fold]
    directional_probability_edge = p_long - p_short
    side = np.sign(directional_probability_edge)
    agreeing_trend_timeframe_count = sum(
        (np.sign(simulation_inputs["trend"][timeframe][pos]) == side).astype(np.int64)
        for timeframe in xy["timeframes"])
    gate_open = (
        (np.maximum(p_long, p_short) > p_neutral)
        & (side != 0)
        & (side == np.sign(simulation_inputs["trend"][config.trend_gate_timeframe(xy["catalogue"])][pos]))
        & (agreeing_trend_timeframe_count >= config.MINIMUM_AGREEING_TREND_TIMEFRAMES)
    )
    barriers = xy["barriers"]
    horizon_minutes = barriers["horizon_minutes"]
    entry_ts, entry_price = xy["entry_ts"][pos], xy["entry_price"][pos]
    fold_start_ms, fold_end_ms = validation.fold_bounds(fold_id)
    # eligibility must be decidable at t_0, so the maximum horizon is tested, not the event that follows
    entry_eligible = (gate_open & xy["entry_observable"][pos]
                      & (entry_ts >= fold_start_ms)
                      & (entry_ts + horizon_minutes * config.MILLISECONDS_PER_MINUTE <= fold_end_ms))
    eligible_rows = np.flatnonzero(entry_eligible)

    upper_barrier, lower_barrier = trade_barriers(
        side[eligible_rows], entry_price[eligible_rows],
        xy["upper_barrier"][pos][eligible_rows], xy["lower_barrier"][pos][eligible_rows],
        barriers["atr_barrier_multiplier"], barriers["take_profit_atr_multiplier"],
        barriers["stop_loss_atr_multiplier"])
    _, t_res, event_resolution, exit_reference_price = labels.triple_barrier(
        simulation_inputs["bars_1m"], entry_ts[eligible_rows], upper_barrier, lower_barrier,
        horizon_minutes)

    # the trade's event scattered back onto the fold's decision grid: a row no threshold can take
    # carries none, and backtest() reads a row only after entry_eligible admitted it
    trade = {"event_end_ts": np.zeros(pos.size, dtype=np.int64),
             "event_resolution": np.zeros(pos.size, dtype=np.int8),
             "exit_reference_price": np.zeros(pos.size),
             "upper_barrier": np.zeros(pos.size), "lower_barrier": np.zeros(pos.size)}
    trade["event_end_ts"][eligible_rows] = labels.event_end_ts(entry_ts[eligible_rows], t_res, horizon_minutes)
    trade["event_resolution"][eligible_rows] = event_resolution
    trade["exit_reference_price"][eligible_rows] = exit_reference_price
    trade["upper_barrier"][eligible_rows] = upper_barrier
    trade["lower_barrier"][eligible_rows] = lower_barrier
    return {
        "directional_probability_edge": directional_probability_edge,
        "side": side, "entry_eligible": entry_eligible,
        "entry_ts": entry_ts, "entry_price": entry_price,
        **trade,
    }


def fill_price(side: float, event_resolution: int, upper_barrier: float,
               lower_barrier: float, exit_reference_price: float) -> float:
    """Take-profit at the barrier; a stop at the worse of the barrier and the touching minute's open; a vertical exit at the last event minute's close."""
    if event_resolution == config.EVENT_RESOLUTION_VERTICAL:
        return exit_reference_price                      # mark: last event minute's close
    if event_resolution == side:
        return upper_barrier if side > 0 else lower_barrier   # target reached
    return (min(lower_barrier, exit_reference_price) if side > 0
            else max(upper_barrier, exit_reference_price))


def backtest(simulation_inputs: dict, signals: dict, entry_edge_threshold: float,
             fold_start_ms: int, fold_end_ms: int) -> dict:
    """Single-position state machine producing one continuous equity path."""
    cat = simulation_inputs["xy"]["catalogue"]
    decision_bar_minutes = config.timeframe_entry(cat, cat["decision_timeframe"])["duration_ms"] // config.MILLISECONDS_PER_MINUTE
    bar_close_offset_minutes = decision_bar_minutes - 1   # a decision bar closes on the last minute of its block
    c = config.EXECUTION_COST_RATE_PER_TRADE_SIDE
    fold_start_minute = (fold_start_ms - config.RESEARCH_START_MS) // config.MILLISECONDS_PER_MINUTE
    fold_minute_count = (fold_end_ms - fold_start_ms) // config.MILLISECONDS_PER_MINUTE
    close_1m = simulation_inputs["bars_1m"]["close"]
    equity_1m = np.empty(fold_minute_count)

    take = np.flatnonzero(signals["entry_eligible"]
                          & (np.abs(signals["directional_probability_edge"]) >= entry_edge_threshold))

    equity, cursor, in_pos_ms = 1.0, 0, 0
    trades = []
    # the exit counts are counts by event_resolution, so they carry its names
    exits = {name: 0 for name in config.EVENT_RESOLUTION_NAMES.values()}
    for k in take:
        i = int((signals["entry_ts"][k] - config.RESEARCH_START_MS)
                // config.MILLISECONDS_PER_MINUTE) - fold_start_minute
        j = int((signals["event_end_ts"][k] - config.RESEARCH_START_MS)
                // config.MILLISECONDS_PER_MINUTE) - fold_start_minute - 1
        if i < cursor:
            continue                                     # position still open
        s = float(signals["side"][k])
        entry_price = float(signals["entry_price"][k])
        resolution = int(signals["event_resolution"][k])
        px = fill_price(s, resolution, float(signals["upper_barrier"][k]),
                        float(signals["lower_barrier"][k]),
                        float(signals["exit_reference_price"][k]))
        equity_1m[cursor:i] = equity                     # flat while out of the market
        equity_1m[i:j] = equity * (1.0 - c + s * (
            close_1m[fold_start_minute + i:fold_start_minute + j] / entry_price - 1.0))
        r = s * (px / entry_price - 1.0) - c - c * (px / entry_price)
        equity *= 1.0 + r
        equity_1m[j] = equity
        cursor = j + 1
        in_pos_ms += int(signals["event_end_ts"][k] - signals["entry_ts"][k])
        trades.append(r)
        exits[config.EVENT_RESOLUTION_NAMES[resolution]] += 1
    equity_1m[cursor:] = equity

    trade_returns = np.asarray(trades)
    # the same path sampled at bar closes, starting from the capital itself:
    # without E0 the first 15 minutes of the fold produce no return at all
    equity_15m = np.concatenate(([1.0], equity_1m[bar_close_offset_minutes::decision_bar_minutes]))
    returns_15m = np.diff(equity_15m) / equity_15m[:-1]
    return {
        "equity_1m": equity_1m,
        "trade_returns": trade_returns,
        "sharpe": validation.sharpe_annualised(returns_15m),
        "max_drawdown": validation.max_drawdown(equity_1m),  # 1m path: intra-bar drawdown is real
        "trade_count": int(trade_returns.size),
        "hit_rate": float((trade_returns > 0).mean()) if trade_returns.size else None,
        "average_trade_return": float(trade_returns.mean()) if trade_returns.size else None,
        "exposure": in_pos_ms / (fold_end_ms - fold_start_ms),
        "exit_counts": exits,
        "final_equity": float(equity),
    }


# what a fold's result carries for the chained path and for nothing else: a path and a population
INTERMEDIATE_RESULT_KEYS = ("equity_1m", "trade_returns")


def pnl_block(result: dict) -> dict:
    """Everything but the 1m path and the trade returns, which are intermediates, not a report."""
    return {k: v for k, v in result.items() if k not in INTERMEDIATE_RESULT_KEYS}


def validation_path_block(validation_by_fold: dict[int, dict]) -> dict:
    """The validation folds chained into one walk-forward path — each fold's 1m equity scaled by what the
    folds before it settled at — and what that path earned, drew down and returned per unit of drawdown.
    The scale runs left to right and the product is never written out: another association of the same
    factors differs in the last bit.""" 
    equity_scaled, trade_returns, minute_count, scale = [], [], 0, 1.0
    for fold_id in config.VALIDATION_FOLD_IDS:
        result = validation_by_fold[fold_id]
        equity_scaled.append(result["equity_1m"] * scale)
        trade_returns.append(result["trade_returns"])
        minute_count += result["equity_1m"].size
        scale *= result["final_equity"]
    equity_validation_1m = np.concatenate(equity_scaled)
    pooled_trade_returns = np.concatenate(trade_returns)
    max_drawdown = validation.max_drawdown(equity_validation_1m)
    cagr = validation.cagr(float(equity_validation_1m[-1]), minute_count)
    return {
        "cagr": cagr,
        "max_drawdown": max_drawdown,
        "calmar": validation.calmar(cagr, max_drawdown),
        "profit_factor": validation.profit_factor(pooled_trade_returns),
        "trade_count": int(pooled_trade_returns.size),
    }


def equity_curve(equity_1m: np.ndarray) -> dict:
    idx = np.arange(0, equity_1m.size, EQUITY_CURVE_SAMPLE_INTERVAL_MINUTES)
    return {"equity": np.round(equity_1m[idx], 6).tolist()}


def entry_edge_threshold_selection(simulation_inputs: dict) -> dict:
    """The entry edge threshold chosen on the validation folds — the grid point maximising the mean fold Sharpe
    among those clearing the trade floor, ties to the smaller threshold, the grid floor when none clears it — with
    the fold results at that point. The one selection the stage and the feature-set search both run."""
    validation_rows = {fold_id: signals_for_fold(simulation_inputs, fold_id)
                       for fold_id in config.VALIDATION_FOLD_IDS}
    validation_bounds = {fold_id: validation.fold_bounds(fold_id)
                         for fold_id in config.VALIDATION_FOLD_IDS}

    # the locals carry the names of the keys they end up as
    entry_edge_threshold, selection_score_mean_sharpe = None, -np.inf
    validation_by_fold, entry_edge_threshold_constraint_met = None, False
    results_at_grid_floor = None                     # kept for the fallback below
    for threshold in config.ENTRY_EDGE_THRESHOLD_GRID:
        results_by_fold = {fold_id: backtest(simulation_inputs, validation_rows[fold_id], threshold,
                                             *validation_bounds[fold_id])
                           for fold_id in config.VALIDATION_FOLD_IDS}
        if threshold == config.ENTRY_EDGE_THRESHOLD_GRID[0]:
            results_at_grid_floor = results_by_fold
        if any(r["trade_count"] < config.MINIMUM_TRADES_PER_VALIDATION_FOLD
               for r in results_by_fold.values()):
            continue
        entry_edge_threshold_constraint_met = True
        score = float(np.mean([r["sharpe"] for r in results_by_fold.values()]))
        if score > selection_score_mean_sharpe:      # strict: ties keep the smaller threshold
            entry_edge_threshold, selection_score_mean_sharpe = threshold, score
            validation_by_fold = results_by_fold
    if not entry_edge_threshold_constraint_met:      # deterministic fallback, reported as such
        entry_edge_threshold = config.ENTRY_EDGE_THRESHOLD_GRID[0]
        validation_by_fold = results_at_grid_floor
        selection_score_mean_sharpe = float(
            np.mean([r["sharpe"] for r in validation_by_fold.values()]))
    return {
        "entry_edge_threshold": entry_edge_threshold,
        "entry_edge_threshold_constraint_met": entry_edge_threshold_constraint_met,
        "selection_score_mean_sharpe": selection_score_mean_sharpe,
        "validation_by_fold": validation_by_fold,
    }


def main() -> int:
    args = config.build_ticker_parser(
        "entry edge threshold on the validation folds, final-holdout PnL"
    ).parse_args()

    for ticker in config.parse_tickers(args.tickers):
        simulation_inputs = load_simulation_inputs(ticker)
        selection = entry_edge_threshold_selection(simulation_inputs)
        entry_edge_threshold = selection["entry_edge_threshold"]

        holdout_start, holdout_end = validation.fold_bounds(config.FINAL_HOLDOUT_FOLD_ID)
        final_holdout = backtest(simulation_inputs, signals_for_fold(simulation_inputs, config.FINAL_HOLDOUT_FOLD_ID),
                                 entry_edge_threshold, holdout_start, holdout_end)

        payload = {
            "entry_edge_threshold": entry_edge_threshold,
            "entry_edge_threshold_constraint_met": selection["entry_edge_threshold_constraint_met"],
            "selection_score_mean_sharpe": selection["selection_score_mean_sharpe"],
            "execution_cost_rate_per_trade_side": config.EXECUTION_COST_RATE_PER_TRADE_SIDE,
            "validation": {f"fold_{fold_id}": pnl_block(r)
                           for fold_id, r in selection["validation_by_fold"].items()},
            "final_holdout": {**pnl_block(final_holdout),
                              "equity_curve": equity_curve(final_holdout["equity_1m"])},
        }
        out = config.strategy_evaluation_json(ticker)
        dataset.write_json(out, payload)
        print(f"{ticker} {out.name}: threshold={entry_edge_threshold} sharpe {final_holdout['sharpe']:.3f} "
              f"trades {final_holdout['trade_count']} maxDD {final_holdout['max_drawdown']:.3f} "
              f"final equity {final_holdout['final_equity']:.3f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
