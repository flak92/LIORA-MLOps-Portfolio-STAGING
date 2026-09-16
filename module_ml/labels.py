"""Triple-barrier labels on the canonical 1m path, per asset.

    t_d = decision_ts          close of the 15m bar; all features are known
    t_0 = entry_ts = t_d + 1m  the candidate entry minute after the decision
    event = [t_0, t_v),        t_v = t_0 + the asset's horizon (240 min by default)

Entry is the canonical 1m open at t_0; the barriers are P0 ± m·ATR14 of the last closed 1h bar, m the asset's
multiplier; a touch requires
volume > 0; event_end_ts is the exclusive end of the event, so the purge rule is event_end_ts <= oos_start. Both
barriers inside one minute leave the order unknowable: label_valid = false, never relabelled 0. entry_observable
(the entry minute traded) may gate an entry; label_valid never does. Y also carries the prices the backtest replays.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np

from . import config, dataset

LABEL_PROCESSING_CHUNK_SIZE_ROWS = 16384


# twice by extraction
def wilder_smoothing(x: np.ndarray, smoothing_period_bars: int) -> np.ndarray:
    """Wilder's recursive average: seeded with the SMA of the first period."""
    out = np.full_like(x, np.nan)
    if x.size < smoothing_period_bars:
        return out
    out[smoothing_period_bars - 1] = x[:smoothing_period_bars].mean()
    for i in range(smoothing_period_bars, x.size):
        out[i] = out[i - 1] + (x[i] - out[i - 1]) / smoothing_period_bars
    return out


# twice by extraction
def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
        smoothing_period_bars: int) -> np.ndarray:
    prev_close = np.concatenate(([close[0]], close[:-1]))
    true_range = np.maximum(high - low,
                            np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
    return wilder_smoothing(true_range, smoothing_period_bars)


# twice by extraction
def asof_index(decision_ts: np.ndarray, timeframe_open_ts: np.ndarray,
               timeframe_duration_ms: int) -> np.ndarray:
    """Index of the last closed bar of a timeframe at each decision_ts — causality by construction; the assert says
    such a bar exists."""
    close_ts = timeframe_open_ts + timeframe_duration_ms
    idx = np.searchsorted(close_ts, decision_ts, side="right") - 1
    assert idx.min() >= 0, "decision before the first closed bar of the timeframe"
    return idx


Y_COLUMNS = {
    "decision_ts": "BIGINT", "entry_ts": "BIGINT", "y": "TINYINT",
    "event_end_ts": "BIGINT", "entry_observable": "BOOLEAN",
    "label_valid": "BOOLEAN",
    "event_resolution": "TINYINT", "entry_price": "DOUBLE",
    "upper_barrier": "DOUBLE", "lower_barrier": "DOUBLE",
    "exit_reference_price": "DOUBLE",
}


def load_research_1m(con: duckdb.DuckDBPyConnection) -> dict[str, np.ndarray]:
    """The canonical 1m series over the research window — the market object."""
    bars_1m = con.execute(
        f"""SELECT timestamp_ms, open, high, low, close, volume FROM ohlcv_1m_canonical
            WHERE timestamp_ms >= {config.RESEARCH_START_MS}
              AND timestamp_ms < {config.RESEARCH_END_MS}
            ORDER BY timestamp_ms"""
    ).fetchnumpy()
    grid = np.arange(config.RESEARCH_START_MS, config.RESEARCH_END_MS, config.MILLISECONDS_PER_MINUTE)
    assert np.array_equal(bars_1m["timestamp_ms"].astype(np.int64), grid), \
        "canonical 1m grid incomplete inside the research window"
    return bars_1m


def entry_rows(entry_ts: np.ndarray) -> np.ndarray:
    """The 1m row of each entry minute on the research grid — the one place that conversion is written."""
    return ((entry_ts - config.RESEARCH_START_MS) // config.MILLISECONDS_PER_MINUTE).astype(np.int64)


def label_barriers(entry_price: np.ndarray, sigma: np.ndarray,
                   atr_barrier_multiplier: float) -> tuple[np.ndarray, np.ndarray]:
    """The label's own barriers: entry_price +- the multiple of the barrier-timeframe ATR the asset's
    geometry fixes — symmetric and side-agnostic, because the direction is what the model learns."""
    return (entry_price + atr_barrier_multiplier * sigma,
            entry_price - atr_barrier_multiplier * sigma)


def event_end_ts(entry_ts: np.ndarray, t_res: np.ndarray, horizon_minutes: int) -> np.ndarray:
    """The exclusive end of an event: the minute after the one that resolved it, else the horizon's."""
    return entry_ts + np.minimum(t_res + 1, horizon_minutes) * config.MILLISECONDS_PER_MINUTE


def triple_barrier(bars_1m: dict[str, np.ndarray], entry_ts: np.ndarray, upper_barrier: np.ndarray,
                   lower_barrier: np.ndarray, horizon_minutes: int):
    """Walk the 1m path in chunks against the barriers given per row; returns (y, t_res,
    event_resolution, exit_reference_price). The one definition of the first barrier touched: the
    label walks its own barriers here, and a trade walks its own through the same call."""
    idx = entry_rows(entry_ts)
    high, low, vol, opn, close = (bars_1m["high"], bars_1m["low"], bars_1m["volume"],
                                  bars_1m["open"], bars_1m["close"])

    event_count = idx.size
    y = np.zeros(event_count, dtype=np.int8)
    t_res = np.full(event_count, horizon_minutes, dtype=np.int32)
    event_resolution = np.zeros(event_count, dtype=np.int8)
    offsets = np.arange(horizon_minutes)
    for a in range(0, event_count, LABEL_PROCESSING_CHUNK_SIZE_ROWS):
        b = min(a + LABEL_PROCESSING_CHUNK_SIZE_ROWS, event_count)
        event_minutes = idx[a:b, None] + offsets[None, :]
        traded = vol[event_minutes] > 0             # volume = 0 means no observed trade
        up_hit = traded & (high[event_minutes] >= upper_barrier[a:b, None])
        dn_hit = traded & (low[event_minutes] <= lower_barrier[a:b, None])
        t_up = np.where(up_hit.any(axis=1), up_hit.argmax(axis=1), horizon_minutes)
        t_dn = np.where(dn_hit.any(axis=1), dn_hit.argmax(axis=1), horizon_minutes)
        ambiguous = (t_up == t_dn) & (t_up < horizon_minutes)
        y[a:b] = np.where(t_up < t_dn, config.EVENT_RESOLUTION_UPPER_BARRIER,
                          np.where(t_dn < t_up, config.EVENT_RESOLUTION_LOWER_BARRIER,
                                   config.EVENT_RESOLUTION_VERTICAL)).astype(np.int8)
        t_res[a:b] = np.minimum(t_up, t_dn)
        event_resolution[a:b] = np.where(ambiguous, config.EVENT_RESOLUTION_AMBIGUOUS, y[a:b])

    resolved = t_res < horizon_minutes
    # horizontal or ambiguous: the open of the resolving minute (the price the
    # market was actually at); vertical: the close of the last event minute
    exit_reference_price = np.where(
        resolved,
        opn[idx + np.minimum(t_res, horizon_minutes - 1)],
        close[idx + horizon_minutes - 1],
    )
    return y, t_res, event_resolution, exit_reference_price


def write_y(ticker: str, cat: dict, cols: dict[str, np.ndarray]) -> Path:
    return dataset.write_parquet(
        config.label_events_parquet(ticker, cat),
        Y_COLUMNS,
        ([
            int(cols["decision_ts"][i]), int(cols["entry_ts"][i]), int(cols["y"][i]),
            int(cols["event_end_ts"][i]), int(cols["entry_observable"][i]),
            int(cols["label_valid"][i]), int(cols["event_resolution"][i]),
            repr(float(cols["entry_price"][i])), repr(float(cols["upper_barrier"][i])),
            repr(float(cols["lower_barrier"][i])),
            repr(float(cols["exit_reference_price"][i])),
        ] for i in range(cols["decision_ts"].size)),
        order_by="decision_ts",
    )


def load_label_inputs(ticker: str, cat: dict) -> dict:
    """Everything Y is built from, read once: the canonical 1m series, the grid of the decision timeframe
    and the bars whose ATR sets the barrier width. A search that relabels an asset holds these and calls
    label_events() again; the stage reads them and calls it once."""
    con = duckdb.connect(str(config.research_ohlcv_duckdb(ticker)), read_only=True)
    con.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
    con.execute("SET threads=1")   # float summation must not be reordered
    barrier_bars = con.execute(
        f"""SELECT timestamp_ms, high, low, close FROM ohlcv_{config.LABEL_BARRIER_ATR_TIMEFRAME}_canonical
            ORDER BY timestamp_ms"""
    ).fetchnumpy()
    decision_grid = con.execute(
        f"""SELECT timestamp_ms FROM ohlcv_{cat['decision_timeframe']}_canonical
            ORDER BY timestamp_ms"""
    ).fetchnumpy()["timestamp_ms"].astype(np.int64)
    bars_1m = load_research_1m(con)
    con.close()
    return {"bars_1m": bars_1m, "decision_grid": decision_grid, "barrier_bars": barrier_bars}


def label_events(label_inputs: dict, cat: dict, barriers: dict) -> dict[str, np.ndarray]:
    """Y for one asset under one barrier geometry: the decisions whose whole horizon fits the research
    window, the symmetric barriers the multiplier sets, the walk down the 1m path, and the columns the
    parquet carries. A move of the label's geometry moves this population — a longer horizon drops more of
    the tail — which is a property of the coordinate, not an accident of the code."""
    bars_1m, barrier_bars = label_inputs["bars_1m"], label_inputs["barrier_bars"]
    horizon_minutes = barriers["horizon_minutes"]
    decision_ts = label_inputs["decision_grid"][label_inputs["decision_grid"] >= cat["warmup_end_ms"]]
    entry_ts = decision_ts + config.MILLISECONDS_PER_MINUTE
    keep = entry_ts + horizon_minutes * config.MILLISECONDS_PER_MINUTE <= config.RESEARCH_END_MS
    decision_ts, entry_ts = decision_ts[keep], entry_ts[keep]

    barrier_atr = atr(barrier_bars["high"], barrier_bars["low"], barrier_bars["close"],
                      config.ATR_WILDER_SMOOTHING_PERIOD_BARS)
    sigma = barrier_atr[asof_index(decision_ts,
                                   barrier_bars["timestamp_ms"].astype(np.int64),
                                   config.timeframe_entry(cat, config.LABEL_BARRIER_ATR_TIMEFRAME)["duration_ms"])]
    assert np.isfinite(sigma).all() and (sigma > 0).all(), \
        f"ATR{config.ATR_WILDER_SMOOTHING_PERIOD_BARS} of the last closed {config.LABEL_BARRIER_ATR_TIMEFRAME} bar is not finite and positive at every decision"

    entry_price = bars_1m["open"][entry_rows(entry_ts)]
    upper_barrier, lower_barrier = label_barriers(entry_price, sigma, barriers["atr_barrier_multiplier"])
    y, t_res, event_resolution, exit_reference_price = triple_barrier(
        bars_1m, entry_ts, upper_barrier, lower_barrier, horizon_minutes)
    return {
        "decision_ts": decision_ts, "entry_ts": entry_ts, "y": y,
        "event_end_ts": event_end_ts(entry_ts, t_res, horizon_minutes),
        "entry_observable": bars_1m["volume"][entry_rows(entry_ts)] > 0,
        "label_valid": event_resolution != config.EVENT_RESOLUTION_AMBIGUOUS,
        "event_resolution": event_resolution, "entry_price": entry_price,
        "upper_barrier": upper_barrier, "lower_barrier": lower_barrier,
        "exit_reference_price": exit_reference_price,
        "t_res": t_res,                        # the walk's own, for the stage's count of vertical exits
    }


def main() -> int:
    args = config.build_ticker_parser("triple-barrier labels on the canonical 1m path").parse_args()
    for ticker in config.parse_tickers(args.tickers):
        cat = dataset.load_catalogue(ticker)
        barriers = dataset.load_barriers(ticker)
        cols = label_events(load_label_inputs(ticker, cat), cat, barriers)

        y, t_res = cols["y"], cols["t_res"]
        sample_valid = cols["entry_observable"] & cols["label_valid"]
        out = write_y(ticker, cat, cols)
        print(f"{ticker} {out.name}: {cols['decision_ts'].size} rows  classes(-1/0/+1)="
              f"{int((y == -1).sum())}/{int((y == 0).sum())}/{int((y == 1).sum())}  "
              f"ambiguous={int((~cols['label_valid']).sum())}  "
              f"unobservable={int((~cols['entry_observable']).sum())}  "
              f"trainable={int(sample_valid.sum())}  "
              f"vertical={int((t_res == barriers['horizon_minutes']).sum())}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
