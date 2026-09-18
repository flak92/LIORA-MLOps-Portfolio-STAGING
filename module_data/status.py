"""Data-layer quality report: stdout tables + store/status/data_status.json, one sequential process over the
asset databases; every alias a scan publishes is the key it becomes.

Each venue is measured on its own, the canonical series the venues were merged into is measured beside them,
and the venue set is one definition — `config.SOURCE_VENUES`, published as `source_venues` so no reader
derives the tier order from a key order.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import duckdb

from . import config
from .ingest import OHLC_INTACT_PREDICATE
from .lean import MINUTES_PER_DAY

# invalid_row_count is what ingest.py refuses to join, counted with ingest's own predicate: the validity rule
# is written once (skills/skill_candle_canonicalisation.md § 4) and imported, never restated here
VENUE_SCAN = """
SELECT count(*)                     AS row_count,
       count(DISTINCT timestamp_ms) AS distinct_timestamp_count,
       min(timestamp_ms)            AS first_timestamp_ms,
       max(timestamp_ms)            AS last_timestamp_ms,
       count(*) FILTER (NOT {ohlc_intact}) AS invalid_row_count,
       count(*) FILTER (volume = 0) AS zero_volume_bars,
       count(*) FILTER (volume = 0 AND open = high AND high = low
                        AND low = close) AS flat_bars,
       arg_max(close, timestamp_ms) AS last_close
FROM ohlcv_1m_{venue}
"""

# one share per venue, the aliases derived from the one venue definition — a venue added to SOURCE_VENUES
# publishes its share with no edit here
CANONICAL_SCAN = """
SELECT count(*)                              AS row_count,
       {venue_source_counts},
       count(*) FILTER (source = 'ffill')    AS ffill_bars,
       count(*) FILTER (zero_volume)         AS zero_volume_bars,
       quantile_cont(rel_divergence, 0.99)   AS relative_divergence_p99,
       max(rel_divergence)                   AS relative_divergence_max,
       max(timestamp_ms)                     AS last_timestamp_ms,
       count(*) FILTER (high < greatest(open, close, low)
                     OR low  > least(open, close, high)) AS ohlc_violation_count
FROM ohlcv_1m_canonical
"""

# one ordered pass over the canonical close: a basis jump can enter only on a minute whose source differs from
# the previous one, the largest 1m move is the same lag, and a candle repeated verbatim while volume was
# printed is a feed frozen on its last bar — the flat and ffill runs below cannot see that one
SOURCE_SWITCH_SCAN = """
SELECT count(*) FILTER (source_changed)      AS source_switch_count,
       max(CASE WHEN source_changed THEN abs(close / previous_close - 1) END) AS max_abs_return_at_switch,
       max(abs(close / previous_close - 1))  AS max_abs_return_1m,
       count(*) FILTER (candle_repeated)     AS repeated_candle_count
FROM (SELECT close,
             lag(close)  OVER minute_order AS previous_close,
             source <> lag(source) OVER minute_order AS source_changed,
             volume > 0
             AND open   = lag(open)   OVER minute_order
             AND high   = lag(high)   OVER minute_order
             AND low    = lag(low)    OVER minute_order
             AND close  = lag(close)  OVER minute_order
             AND volume = lag(volume) OVER minute_order AS candle_repeated
      FROM ohlcv_1m_canonical
      WINDOW minute_order AS (ORDER BY timestamp_ms))
"""

# a minute of the canonical grid is in exactly one state — forward-filled, flat, or traded — and the longest run
# of each of the first two is one pass and one grouping. A forward-filled row repeats the previous close with no
# volume, so it satisfies the flat geometry as well; the state is decided in order, so fabrication is never
# reported as a quiet market (skills/skill_candle_canonicalisation.md § 6, § 10)
CANONICAL_RUN_SCAN = """
WITH marked AS (SELECT timestamp_ms,
                       CASE WHEN source = 'ffill'                     THEN 'ffill'
                            WHEN volume = 0 AND open = high AND high = low
                                             AND low = close          THEN 'flat'
                            ELSE 'traded' END AS minute_state
                FROM ohlcv_1m_canonical),
state_changes AS (SELECT timestamp_ms, minute_state,
                         CASE WHEN minute_state = lag(minute_state) OVER (ORDER BY timestamp_ms)
                              THEN 0 ELSE 1 END AS state_changed
                  FROM marked),
runs AS (SELECT minute_state, count(*) AS run_minutes
         FROM (SELECT minute_state, sum(state_changed) OVER (ORDER BY timestamp_ms) AS run_id
               FROM state_changes)
         GROUP BY minute_state, run_id)
SELECT coalesce(max(run_minutes) FILTER (minute_state = 'flat'),  0) AS longest_flat_run_minutes,
       coalesce(max(run_minutes) FILTER (minute_state = 'ffill'), 0) AS longest_ffill_run_minutes
FROM runs
"""


def venue_source_count_aliases() -> str:
    """One `count(*) FILTER (source = '<venue>') AS <venue>_source_count` per venue of the one definition."""
    return ",\n       ".join(f"count(*) FILTER (source = '{venue}') AS {venue}_source_count"
                             for venue in config.SOURCE_VENUES)


def load_row(con: duckdb.DuckDBPyConnection, statement: str) -> dict:
    """The one row a scalar scan returns, keyed by the scan's column names."""
    cursor = con.execute(statement)
    names = [column[0] for column in cursor.description]
    return dict(zip(names, cursor.fetchone()))


def to_utc_minute(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / config.MILLISECONDS_PER_SECOND, tz=UTC).strftime("%Y-%m-%d %H:%M")


def share_pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 3) if whole else 0.0


def venue_block(venue: str, tickers: list[str], venue_rows: dict, canonical_rows: dict) -> list[dict]:
    """One venue's table of the snapshot: a row per asset, each judged against its own canonical end."""
    table = []
    for ticker in tickers:
        # every asset is judged against its OWN canonical end, so a young asset is never charged
        # an older one's history and a stale feed is the only thing a gap can mean
        asset_window_end_ms = canonical_rows[ticker]["last_timestamp_ms"] + config.CANONICAL_GRID_INTERVAL_MS
        expected = (asset_window_end_ms - config.DATA_WINDOW_START_MS) // config.CANONICAL_GRID_INTERVAL_MS
        # a scalar scan of an empty venue table returns one row of zero and NULLs, never no row
        venue_row = venue_rows[venue][ticker]
        venue_row_count, distinct = venue_row["row_count"], venue_row["distinct_timestamp_count"]
        table.append(
            {
                "ticker": ticker,
                "symbol": config.symbol(ticker),
                "row_count": venue_row_count,
                "coverage_pct": share_pct(distinct, expected),
                "gap_count": expected - distinct,
                # measured from the first observation to the end of the window, so a stale feed reports its gap
                "gap_count_after_first_observation": (
                    (asset_window_end_ms - venue_row["first_timestamp_ms"]) // config.CANONICAL_GRID_INTERVAL_MS - distinct
                ) if venue_row["first_timestamp_ms"] is not None else 0,
                "duplicate_count": venue_row_count - distinct,
                "invalid_row_count": int(venue_row["invalid_row_count"]),
                "zero_volume_bars": int(venue_row["zero_volume_bars"]),
                "flat_bars": int(venue_row["flat_bars"]),
                "last_close": config.rounded(venue_row["last_close"], 8),
                "first_observation_utc": to_utc_minute(venue_row["first_timestamp_ms"]),
                "last_observation_utc": to_utc_minute(venue_row["last_timestamp_ms"]),
            }
        )
    return table


def canonical_source_block(ticker: str, canonical_row: dict) -> dict:
    """One asset's row of the canonical-construction table: the series the venues were merged into."""
    canonical_row_count = canonical_row["row_count"]
    return {
        "ticker": ticker,
        "symbol": config.symbol(ticker),
        "row_count": canonical_row_count,
        "last_observation_utc": to_utc_minute(canonical_row["last_timestamp_ms"]),
        "source_share_pct_by_venue": {
            venue: share_pct(int(canonical_row[f"{venue}_source_count"]), canonical_row_count)
            for venue in config.SOURCE_VENUES
        },
        "ffill_bars": int(canonical_row["ffill_bars"]),
        "longest_ffill_run_minutes": int(canonical_row["longest_ffill_run_minutes"]),
        "zero_volume_bars": int(canonical_row["zero_volume_bars"]),
        "longest_flat_run_minutes": int(canonical_row["longest_flat_run_minutes"]),
        "repeated_candle_count": int(canonical_row["repeated_candle_count"]),
        "source_switch_count": int(canonical_row["source_switch_count"]),
        "max_abs_return_at_switch": config.rounded(canonical_row["max_abs_return_at_switch"], 6),
        "max_abs_return_1m": config.rounded(canonical_row["max_abs_return_1m"], 6),
        "relative_divergence_p99": config.rounded(canonical_row["relative_divergence_p99"], 8),
        "relative_divergence_max": config.rounded(canonical_row["relative_divergence_max"], 8),
        "ohlc_violation_count": int(canonical_row["ohlc_violation_count"]),
    }


def print_venue_table(venue: str, venue_table: list[dict]) -> None:
    print(f"[venue {venue}]")
    print(f"{'symbol':9} {'rows':>9} {'coverage':>8} {'gaps':>8} {'dups':>4} {'invalid':>7} "
          f"{'zero-vol':>8} {'flat':>6} {'last close':>12}")
    for venue_row in venue_table:
        print(f"{venue_row['symbol']:9} {venue_row['row_count']:>9} {venue_row['coverage_pct']:>8.3f} "
              f"{venue_row['gap_count']:>8} {venue_row['duplicate_count']:>4} {venue_row['invalid_row_count']:>7} "
              f"{venue_row['zero_volume_bars']:>8} {venue_row['flat_bars']:>6} "
              f"{venue_row['last_close'] if venue_row['last_close'] is not None else '-':>12}")


def print_canonical_table(canonical: list[dict]) -> None:
    shares = " ".join(f"{venue:>9}" for venue in config.SOURCE_VENUES)
    print("[canonical source]")
    print(f"{'symbol':9} {'rows':>9} {shares} {'ffill':>6} {'ffill run':>9} {'zero-vol':>8} {'flat run':>8} "
          f"{'repeated':>8} {'switches':>8} {'max |ret| at switch':>19} {'max |ret| 1m':>12} "
          f"{'rel. divergence p99':>19} {'rel. divergence max':>19} {'ohlc bad':>8}")
    for canonical_row in canonical:
        share_columns = " ".join(f"{canonical_row['source_share_pct_by_venue'][venue]:>9.3f}"
                                 for venue in config.SOURCE_VENUES)
        print(f"{canonical_row['symbol']:9} {canonical_row['row_count']:>9} {share_columns} "
              f"{canonical_row['ffill_bars']:>6} {canonical_row['longest_ffill_run_minutes']:>9} "
              f"{canonical_row['zero_volume_bars']:>8} {canonical_row['longest_flat_run_minutes']:>8} "
              f"{canonical_row['repeated_candle_count']:>8} {canonical_row['source_switch_count']:>8} "
              f"{canonical_row['max_abs_return_at_switch'] if canonical_row['max_abs_return_at_switch'] is not None else '-':>19} "
              f"{canonical_row['max_abs_return_1m'] if canonical_row['max_abs_return_1m'] is not None else '-':>12} "
              f"{canonical_row['relative_divergence_p99'] if canonical_row['relative_divergence_p99'] is not None else '-':>19} "
              f"{canonical_row['relative_divergence_max'] if canonical_row['relative_divergence_max'] is not None else '-':>19} "
              f"{canonical_row['ohlc_violation_count']:>8}")


def main() -> int:
    args = config.build_ticker_parser("data & database monitoring -> stdout + store/status/data_status.json").parse_args()
    requested = config.parse_tickers(args.tickers)
    venue_rows = {venue: {} for venue in config.SOURCE_VENUES}
    canonical_rows = {}
    canonical_scan = CANONICAL_SCAN.format(venue_source_counts=venue_source_count_aliases())
    for ticker in requested:
        path = config.research_ohlcv_duckdb(ticker)
        if not path.exists():
            continue
        con = duckdb.connect(str(path), read_only=True)
        con.execute(f"SET memory_limit='{config.DUCKDB_MEMORY_LIMIT}'")
        con.execute("SET threads=1")   # float summation must not be reordered
        for venue in config.SOURCE_VENUES:
            venue_rows[venue][ticker] = load_row(con, VENUE_SCAN.format(venue=venue,
                                                                       ohlc_intact=OHLC_INTACT_PREDICATE))
        canonical_rows[ticker] = {
            **load_row(con, canonical_scan),
            **load_row(con, SOURCE_SWITCH_SCAN),
            **load_row(con, CANONICAL_RUN_SCAN),
        }
        con.close()
    if not canonical_rows:
        raise SystemExit("no asset database found — run `make data-ingest` first")

    tickers = [ticker for ticker in requested if ticker in canonical_rows]
    venues = {venue: venue_block(venue, tickers, venue_rows, canonical_rows) for venue in config.SOURCE_VENUES}
    canonical = [canonical_source_block(ticker, canonical_rows[ticker]) for ticker in tickers]

    status = {
        "generated_at_utc": datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S"),
        "window_start_utc": f"{config.DATA_WINDOW_START_UTC} 00:00",
        "download_cadence_minutes": MINUTES_PER_DAY,
        # the venue set in its tier order, so a reader takes the order from the payload and never from a key order
        "source_venues": list(config.SOURCE_VENUES),
        "venues": venues,
        "canonical_source": canonical,
    }
    status_path = config.DATA_STATUS_JSON_PATH
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, sort_keys=True, indent=1) + "\n", encoding="utf-8")

    print(f"window from {status['window_start_utc']}  venues {' '.join(config.SOURCE_VENUES)}")
    for venue in config.SOURCE_VENUES:
        print_venue_table(venue, venues[venue])
    print_canonical_table(canonical)
    print(f"wrote {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
