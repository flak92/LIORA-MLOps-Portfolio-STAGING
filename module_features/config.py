"""The feature layer's configuration — the timeframe register, the frozen research window, the indicator register and
the feature catalogue: the one definition every timeframe-shaped and feature-shaped thing derives from, and one
descriptor per feature parquet. Every constant is fixed a priori; changing one defines a different experiment, and the
git commit is the record of which one ran."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

from .indicators import INDICATORS  # re-exported: the indicator register, one record per token beside its kernel

# twice by extraction
MILLISECONDS_PER_SECOND = 1000
# twice by extraction
MILLISECONDS_PER_MINUTE = 60_000
# twice by extraction
MILLISECONDS_PER_DAY = 86_400_000
# twice by extraction
DUCKDB_MEMORY_LIMIT = "4GB"
# twice by extraction
STORE_ASSETS_ARTIFACTS_DIR = Path(os.environ["STORE_ASSETS_ARTIFACTS_DIR"])
# twice by extraction
STORE_STATUS_DIR = Path(os.environ["STORE_STATUS_DIR"])


# twice by extraction
def to_utc_ms(day: str) -> int:
    """A UTC calendar day, `YYYY-MM-DD`, as the epoch milliseconds of its midnight."""
    return int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp() * MILLISECONDS_PER_SECOND)


# twice by extraction
def artifact_dir(ticker: str) -> Path:
    """One directory per ticker; inside it one file per artifact, named for it."""
    return STORE_ASSETS_ARTIFACTS_DIR / ticker


# twice by extraction
def research_ohlcv_duckdb(ticker: str) -> Path:
    """The asset's own database — the market object's one home, resident in the asset folder."""
    return artifact_dir(ticker) / f"{ticker}_research_ohlcv.duckdb"


# twice by extraction
def build_ticker_parser(description: str) -> argparse.ArgumentParser:
    """The one CLI every stage shares: --tickers, required — the launcher names the basket, a stage never does."""
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--tickers", required=True, help="comma-separated tickers, e.g. BTC or BTC,ETH")
    return ap


# twice by extraction
def parse_tickers(tickers_csv: str) -> list[str]:
    """The --tickers value as a basket: split on commas, trimmed, upper case, an empty item dropped."""
    return [ticker.strip().upper() for ticker in tickers_csv.split(",") if ticker.strip()]


MINUTES_PER_HOUR = 60
MILLISECONDS_PER_HOUR = MINUTES_PER_HOUR * MILLISECONDS_PER_MINUTE

# ---- frozen research window (later data top-ups do not change this experiment). The start repeats module_data's
# DATA_WINDOW_START_UTC on purpose rather than importing it: the download window may be widened without moving an
# experiment already run against it.
# twice by extraction
RESEARCH_START_UTC = "2021-01-01"   # inclusive
# twice by extraction
RESEARCH_END_UTC = "2026-08-26"     # exclusive
# twice by extraction
RESEARCH_START_MS = to_utc_ms(RESEARCH_START_UTC)
# twice by extraction
RESEARCH_END_MS = to_utc_ms(RESEARCH_END_UTC)

# ---- the timeframe hierarchy: the experiment's literal, finest first — the decision grid, the trend gate's timeframe
# and the count the strategy's agreement reads all follow from it, so a new token is one line here and a new
# experiment. Every entry is an exact aggregation of the canonical 1m series, written by bars.py; a token is
# <integer><unit>, and its duration and its file-name slot derive from the token (skills/skill_feature_taxonomy.md)
HIERARCHY_TIMEFRAMES = ("15m", "1h", "4h")
DECISION_TIMEFRAME = "15m"
TIMEFRAME_UNIT_MS = {"m": MILLISECONDS_PER_MINUTE, "h": MILLISECONDS_PER_HOUR, "d": MILLISECONDS_PER_DAY}
# the five slots of module_skills/skill_sorting_files_naming_standard.md, finest first, and the field each unit fills
TIMEFRAME_SLOT_FIELDS = ("ss", "mm", "hh", "dd", "MM")
TIMEFRAME_UNIT_SLOT_FIELD = {"m": 1, "h": 2, "d": 3}


def timeframe_duration_ms(token: str) -> int:
    return int(token[:-1]) * TIMEFRAME_UNIT_MS[token[-1]]


def timeframe_slot(token: str) -> str:
    """The token in the five slots: its number, zero-padded, in its unit's field; the unit letters everywhere else."""
    fields = list(TIMEFRAME_SLOT_FIELDS)
    fields[TIMEFRAME_UNIT_SLOT_FIELD[token[-1]]] = f"{int(token[:-1]):02d}"
    return "-".join(fields)


TIMEFRAME_DURATION_MS = {timeframe: timeframe_duration_ms(timeframe) for timeframe in HIERARCHY_TIMEFRAMES}
TIMEFRAME_SLOT = {timeframe: timeframe_slot(timeframe) for timeframe in HIERARCHY_TIMEFRAMES}
# ---- the terms: a series of the bars, or an indicator of the register with its one integer parameter glued to the
# token in a name (ema20, rsi14); the indicators' invariants are their register records in indicators.py, and the
# operators and normalisers that compose them are the registers beside their kernels in catalogue.py

# ---- the feature catalogue: one record per feature definition, from which the name, the computation, the history
# and the required warm-up derive. A term is ("<indicator>", <parameter_bars>) on the default series close,
# ("<series>", "<indicator>", <parameter_bars>) on another series, or ("<series>",) — a bare series. The five
# definitions of the default set lead, in the order the frozen experiment stacks them: the column order is what
# the model samples by position.
FEATURE_CATALOGUE = (
    {"terms": (("ema", 20), ("ema", 50), ("atr", 14)), "operators": ("minus", "over"),
     "range": "unbounded, dimensionless", "timeframes": HIERARCHY_TIMEFRAMES, "definition_in_default_set": True},
    {"terms": (("rsi", 14),), "normaliser": "centered",
     "range": "[-1, 1]", "timeframes": HIERARCHY_TIMEFRAMES, "definition_in_default_set": True},
    {"terms": (("atr", 14), ("close",)), "operators": ("over",),
     "range": "> 0, dimensionless", "timeframes": HIERARCHY_TIMEFRAMES, "definition_in_default_set": True},
    {"terms": (("range_position", 20),),
     "range": "[0, 1]", "timeframes": HIERARCHY_TIMEFRAMES, "definition_in_default_set": True},
    {"terms": (("log_volume", "zscore", 50),),
     "range": "dimensionless", "timeframes": HIERARCHY_TIMEFRAMES, "definition_in_default_set": True},
    {"terms": (("zscore", 20),),
     "range": "dimensionless", "timeframes": HIERARCHY_TIMEFRAMES, "definition_in_default_set": False},
    {"terms": (("close",), ("sma", 50), ("atr", 14)), "operators": ("minus", "over"),
     "range": "unbounded, dimensionless", "timeframes": HIERARCHY_TIMEFRAMES, "definition_in_default_set": False},
    {"terms": (("close",), ("sma", 200), ("atr", 14)), "operators": ("minus", "over"),
     "range": "unbounded, dimensionless", "timeframes": ("4h",), "definition_in_default_set": False},
)


def term_name(term: tuple) -> str:
    """A term as its name is written: a bare series is its token; an indicator glues its parameter, prefixed by its
    series unless the series is close or the indicator's inputs are fixed."""
    if len(term) == 1:
        return term[0]
    series, indicator, parameter_bars = ("close",) + term if len(term) == 2 else term
    prefix = "" if series == "close" or "inputs" in INDICATORS[indicator] else f"{series}_"
    return f"{prefix}{indicator}{parameter_bars}"


def feature_definition_name(definition: dict) -> str:
    """[<normaliser>_]<term>{_<operator>_<term>} — read off the record, never written by hand."""
    name = term_name(definition["terms"][0])
    for operator, term in zip(definition.get("operators", ()), definition["terms"][1:]):
        name += f"_{operator}_{term_name(term)}"
    normaliser = definition.get("normaliser")
    return f"{normaliser}_{name}" if normaliser else name


# twice by extraction
def feature_id(definition_name: str, timeframe: str) -> str:
    """The column of X and the key of an importance: the definition aligned to the decision grid on one timeframe."""
    return f"{definition_name}_{timeframe}"


def term_indicator(term: tuple) -> str | None:
    """The indicator token of a term — a bare series has none."""
    return None if len(term) == 1 else term[-2]


def term_warmup_bars(term: tuple) -> int:
    """Bars of the term's timeframe before its value is settled; a bare series needs none."""
    return 0 if len(term) == 1 else INDICATORS[term_indicator(term)]["warmup_multiple"] * term[-1]


def definition_warmup_bars(definition: dict) -> int:
    return max(term_warmup_bars(term) for term in definition["terms"])


# The experiment's warm-up, in bars of the top timeframe — read off the catalogue, not written beside it.
# Written down it was a number that had to be remembered: a definition with a longer memory than the one it
# was set for is evaluated before its own value has settled, and nothing says so, because the rows are there
# and finite. Derived, the catalogue moves it. Today the widest are ema50 (4 x 50) and sma200 (1 x 200), and
# the derived value is 200 — the number that was written here.
WARMUP_TOP_TIMEFRAME_BARS = max(definition_warmup_bars(definition) for definition in FEATURE_CATALOGUE)
WARMUP_END_MS = RESEARCH_START_MS + WARMUP_TOP_TIMEFRAME_BARS * TIMEFRAME_DURATION_MS[HIERARCHY_TIMEFRAMES[-1]]


def definition_effective_history_hours(definition: dict, timeframe: str) -> float:
    """The longest parameter of the definition read on that timeframe: a window's history is the window, a
    recursion's the bars carrying most of its weight — the number the nesting of the levels compares."""
    longest_parameter_bars = max((term[-1] for term in definition["terms"] if len(term) > 1), default=0)
    return longest_parameter_bars * TIMEFRAME_DURATION_MS[timeframe] / MILLISECONDS_PER_HOUR


def catalogue_columns(timeframe: str) -> tuple[str, ...]:
    """The definitions offered on one timeframe, in catalogue order — the columns of that timeframe's parquet."""
    return tuple(feature_definition_name(definition) for definition in FEATURE_CATALOGUE
                 if timeframe in definition["timeframes"])


# every feature id the catalogue offers, timeframe-major and catalogue-order within
CATALOGUE_COLUMNS = tuple(feature_id(name, timeframe)
                          for timeframe in HIERARCHY_TIMEFRAMES for name in catalogue_columns(timeframe))
# the set an asset holds until a promotion: the default definitions on every timeframe they are offered on
DEFAULT_FEATURE_COLUMNS_BY_TIMEFRAME = {
    timeframe: tuple(feature_definition_name(definition) for definition in FEATURE_CATALOGUE
                     if definition["definition_in_default_set"] and timeframe in definition["timeframes"])
    for timeframe in HIERARCHY_TIMEFRAMES
}
# twice by extraction
TREND_GATE_FEATURE_DEFINITION = feature_definition_name(FEATURE_CATALOGUE[0])   # the strategy reads it on every timeframe, set or no set — module_ml/config.py carries the same name as a literal
TREND_GATE_TIMEFRAME = HIERARCHY_TIMEFRAMES[-1]                                  # the top timeframe that vetoes a side


def features_parquet(ticker: str, timeframe: str):
    """One parquet per timeframe, its grid in timeframe slots; built here and nowhere else."""
    return artifact_dir(ticker) / f"{ticker}_features_{TIMEFRAME_SLOT[timeframe]}.parquet"


FEATURES_STATUS_JSON_PATH = STORE_STATUS_DIR / "features_status.json"   # the snapshot this module writes: the catalogue's facts, each asset's row counts


# twice by extraction
def catalogue_json(ticker: str):
    """The asset's copy of the feature layer's contract — what the ML layer reads instead of the feature configuration."""
    return artifact_dir(ticker) / f"{ticker}_catalogue.json"


def catalogue_contract(ticker: str) -> dict:
    """The catalogue as the ML layer needs it, per asset: the decision grid, the hierarchy with each timeframe's slot and
    duration, the warm-up, the columns offered per timeframe in catalogue order, the default set, and the parquet each
    timeframe's columns live in — so ML parses no token, builds no path from this module's grammar and imports nothing."""
    return {
        "decision_timeframe": DECISION_TIMEFRAME,
        "timeframes": [{"timeframe": timeframe, "slot": TIMEFRAME_SLOT[timeframe], "duration_ms": TIMEFRAME_DURATION_MS[timeframe]}
                       for timeframe in HIERARCHY_TIMEFRAMES],
        "warmup_top_timeframe_bars": WARMUP_TOP_TIMEFRAME_BARS,
        "warmup_end_ms": WARMUP_END_MS,
        "columns_by_timeframe": {timeframe: list(catalogue_columns(timeframe)) for timeframe in HIERARCHY_TIMEFRAMES},
        "default_columns_by_timeframe": {timeframe: list(DEFAULT_FEATURE_COLUMNS_BY_TIMEFRAME[timeframe])
                                         for timeframe in HIERARCHY_TIMEFRAMES},
        "parquet_by_timeframe": {timeframe: features_parquet(ticker, timeframe).name for timeframe in HIERARCHY_TIMEFRAMES},
    }
