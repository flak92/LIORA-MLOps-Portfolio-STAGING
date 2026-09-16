"""The feature catalogue on the decision grid: every feature definition evaluated on every timeframe it is offered on,
each value from the last closed bar of its timeframe; one parquet per timeframe, from the research warm-up onward."""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np

from . import config, dataset, indicators

# the series kernels cover the one series that is not a bar column; the indicators' kernels are their register records
SERIES_KERNELS = {"log_volume": lambda bars: np.log1p(bars["volume"])}


def load_timeframe(con: duckdb.DuckDBPyConnection, timeframe: str) -> dict[str, np.ndarray]:
    return con.execute(
        f"""SELECT timestamp_ms, open, high, low, close, volume
            FROM ohlcv_{timeframe}_canonical ORDER BY timestamp_ms"""
    ).fetchnumpy()


def series_values(bars: dict[str, np.ndarray], series: str) -> np.ndarray:
    return SERIES_KERNELS[series](bars) if series in SERIES_KERNELS else bars[series]


def term_values(bars: dict[str, np.ndarray], term: tuple) -> np.ndarray:
    """A bare series is its column; an indicator runs its kernel on its fixed inputs, else on the term's series."""
    if len(term) == 1:
        return series_values(bars, term[0])
    series, indicator, parameter_bars = ("close",) + term if len(term) == 2 else term
    record = indicators.INDICATORS[indicator]
    inputs = [bars[name] for name in record.get("inputs", ())] or [series_values(bars, series)]
    return record["kernel"](*inputs, parameter_bars)


def difference(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """`minus`: the left term less the right."""
    return left - right


def ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """`over`: a ratio, 0 where the denominator is 0."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denominator == 0.0, 0.0, numerator / denominator)


def centered(value: np.ndarray, low: float, high: float) -> np.ndarray:
    """`centered`: a bounded term mapped to [-1, 1] from the output range of its own indicator."""
    return (value - (low + high) / 2) / ((high - low) / 2)


# the two registers of the composition grammar, each beside its kernels, in the shape of INDICATORS
OPERATORS = {"minus": {"kernel": difference}, "over": {"kernel": ratio}}
NORMALISERS = {"centered": {"kernel": centered}}


def feature_definition_values(bars: dict[str, np.ndarray], definition: dict) -> np.ndarray:
    """The definition on one timeframe's own bars: the terms folded left to right by the operators, then normalised
    over the output range of the one bounded indicator the normalised definition is written on."""
    value = term_values(bars, definition["terms"][0])
    for operator, term in zip(definition.get("operators", ()), definition["terms"][1:]):
        value = OPERATORS[operator]["kernel"](value, term_values(bars, term))
    normaliser = definition.get("normaliser")
    if not normaliser:
        return value
    low, high = indicators.INDICATORS[config.term_indicator(definition["terms"][0])]["output_range"]
    return NORMALISERS[normaliser]["kernel"](value, low, high)


def timeframe_catalogue(bars: dict[str, np.ndarray], timeframe: str) -> dict[str, np.ndarray]:
    """Every definition offered on the timeframe, by its name, on that timeframe's own bars."""
    return {config.feature_definition_name(definition): feature_definition_values(bars, definition)
            for definition in config.FEATURE_CATALOGUE if timeframe in definition["timeframes"]}


def build_catalogue(con: duckdb.DuckDBPyConnection) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Return (decision_ts, every catalogued column by feature id, config.CATALOGUE_COLUMNS); the stacked matrix is
    built only to assert finiteness across all of them — a term that needs more warm-up than the experiment grants
    stops here."""
    timeframes = {timeframe: load_timeframe(con, timeframe) for timeframe in config.HIERARCHY_TIMEFRAMES}
    catalogue = {timeframe: timeframe_catalogue(timeframes[timeframe], timeframe)
                 for timeframe in config.HIERARCHY_TIMEFRAMES}

    ts_15m = timeframes[config.DECISION_TIMEFRAME]["timestamp_ms"].astype(np.int64)
    decision_ts = ts_15m[ts_15m >= config.WARMUP_END_MS]

    cols: dict[str, np.ndarray] = {}
    for timeframe in config.HIERARCHY_TIMEFRAMES:
        idx = indicators.asof_index(decision_ts,
                                    timeframes[timeframe]["timestamp_ms"].astype(np.int64),
                                    config.TIMEFRAME_DURATION_MS[timeframe])
        for name in config.catalogue_columns(timeframe):
            cols[config.feature_id(name, timeframe)] = catalogue[timeframe][name][idx]

    x = np.column_stack([cols[c] for c in config.CATALOGUE_COLUMNS])
    assert np.isfinite(x).all(), "NaN/inf in the catalogue after the research warm-up"
    return decision_ts, cols


def write_catalogue(ticker: str, decision_ts: np.ndarray, cols: dict[str, np.ndarray]) -> list[Path]:
    """One parquet per timeframe — the columns the catalogue offers on it, on the decision grid; the filename carries
    the timeframe, so the columns do not — and the asset's copy of the contract the ML layer reads."""
    written = []
    for timeframe in config.HIERARCHY_TIMEFRAMES:
        names = config.catalogue_columns(timeframe)
        written.append(dataset.write_parquet(
            config.features_parquet(ticker, timeframe),
            {"decision_ts": "BIGINT", **{name: "DOUBLE" for name in names}},
            ([int(decision_ts[i])] + [repr(float(cols[config.feature_id(name, timeframe)][i])) for name in names]
             for i in range(decision_ts.size)),
            order_by="decision_ts",
        ))
    contract = config.catalogue_json(ticker)
    payload = config.catalogue_contract(ticker)
    # the contract is what the ML layer reads, and every column in it was evaluated under this warm-up: a
    # contract that does not cover its own widest definition would hand ML rows the definition had not settled
    # into. Derived today, so this cannot fire — it is what makes writing the number back by hand fail loudly
    assert max(config.definition_warmup_bars(definition) for definition in config.FEATURE_CATALOGUE) \
        <= payload["warmup_top_timeframe_bars"], \
        "the catalogue's warm-up does not cover its widest definition"
    dataset.write_json(contract, payload)
    written.append(contract)
    return written


def main() -> int:
    args = config.build_ticker_parser("the feature catalogue on the decision grid per asset").parse_args()
    for ticker in config.parse_tickers(args.tickers):
        con = duckdb.connect(str(config.research_ohlcv_duckdb(ticker)), read_only=True)
        con.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        con.execute("SET threads=1")   # float summation must not be reordered
        decision_ts, cols = build_catalogue(con)
        con.close()
        *parquets, contract = write_catalogue(ticker, decision_ts, cols)
        print(f"{ticker} {', '.join(w.name for w in parquets)}: {decision_ts.size} rows x "
              f"{'/'.join(str(len(config.catalogue_columns(t))) for t in config.HIERARCHY_TIMEFRAMES)} columns, + {contract.name}",
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
