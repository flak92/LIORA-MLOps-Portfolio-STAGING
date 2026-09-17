"""Promotion of one proposal of the coordinate search into the asset's own state — a hand's choice, never a
derivation: the proposal's columns are copied into <TICKER>_feature_set.json and its barrier geometry into
<TICKER>_barriers.json, and nothing else. The Makefile reruns the ML chain after it, so the promoted state
is re-tuned and its realised result differs from the search's; the commit history is the record of every
promotion, and the same proposal again changes nothing."""

from __future__ import annotations

from . import config, dataset, feature_set_search


def main() -> int:
    parser = config.build_ticker_parser("copy one proposal of the coordinate search into the asset's own state")
    parser.add_argument("--proposal", type=int, default=1, help="the proposal's rank in the coordinate search result")
    args = parser.parse_args()
    for ticker in config.parse_tickers(args.tickers):
        cat = dataset.load_catalogue(ticker)
        timeframes = config.timeframes(cat)
        # the proposals by their rank, so a rank the search result does not hold fails on the lookup itself; a
        # proposal names its trial, and the state it holds is that trial's line of the ledger
        trial_index_by_rank = {row["proposal"]: row["trial_index"]
                               for row in dataset.load_json(config.coordinate_search_json(ticker))["proposals"]}
        trial = dataset.load_jsonl(config.coordinate_search_trials_jsonl(ticker))[trial_index_by_rank[args.proposal] - 1]
        columns_by_timeframe = {timeframe: list(trial["columns_by_timeframe"][timeframe])
                                for timeframe in timeframes}
        barriers = {name: trial[name] for name in config.BARRIER_COORDINATE_NAMES}
        active_columns = {timeframe: list(columns) for timeframe, columns
                          in dataset.load_feature_columns(ticker, cat).items()}
        active = dataset.load_barriers(ticker)
        active_barriers = {name: active[name] for name in config.BARRIER_COORDINATE_NAMES}
        if columns_by_timeframe == active_columns and barriers == active_barriers:
            print(f"{ticker} state unchanged — proposal {args.proposal} is the active state", flush=True)
            continue
        added = feature_set_search.column_count(
            feature_set_search.columns_added(columns_by_timeframe, active_columns, timeframes), timeframes)
        removed = feature_set_search.column_count(
            feature_set_search.columns_removed(columns_by_timeframe, active_columns, timeframes), timeframes)
        moved = [name for name in config.BARRIER_COORDINATE_NAMES if barriers[name] != active_barriers[name]]
        dataset.write_json(config.feature_set_json(ticker), {"columns_by_timeframe": columns_by_timeframe})
        dataset.write_json(config.barriers_json(ticker), barriers)
        print(f"{ticker} <- proposal {args.proposal} (+{added} -{removed} columns"
              f"{', ' + ', '.join(moved) if moved else ''}); rerun the ML chain for this asset", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
