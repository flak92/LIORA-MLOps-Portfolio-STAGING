"""The feature-set coordinate of the search: the algebra of a set of columns and the moves a pass expands
one by — a column of the catalogue in, a column of the set out. The two families are expanded in that
order, the second seeded by what the first left, which is what makes a pass one pass and not two.

It scores nothing and runs nothing: coordinate_search.py scores a state and decides which moves it keeps."""

from __future__ import annotations

from . import config

# the two families of a pass, in the order it expands them
FAMILIES = (config.COORDINATE_SEARCH_MOVE_FORWARD, config.COORDINATE_SEARCH_MOVE_BACKWARD)


# the helpers take the hierarchy from the asset's contract (xy["timeframes"]) — the ML layer holds no register of its own
def columns_added(columns_by_timeframe: dict, active: dict, timeframes: tuple[str, ...]) -> dict:
    return {timeframe: [name for name in columns_by_timeframe[timeframe] if name not in active[timeframe]]
            for timeframe in timeframes}


def columns_removed(columns_by_timeframe: dict, active: dict, timeframes: tuple[str, ...]) -> dict:
    return columns_added(active, columns_by_timeframe, timeframes)


def column_count(columns_by_timeframe: dict, timeframes: tuple[str, ...]) -> int:
    return sum(len(columns_by_timeframe[timeframe]) for timeframe in timeframes)


def with_column(columns_by_timeframe: dict, timeframe: str, name: str, catalogue_columns: list[str]) -> dict:
    """The set with one definition added on one timeframe, kept in catalogue order — the order the contract lists."""
    kept = set(columns_by_timeframe[timeframe]) | {name}
    return {**columns_by_timeframe,
            timeframe: tuple(column for column in catalogue_columns if column in kept)}


def without_column(columns_by_timeframe: dict, timeframe: str, name: str) -> dict:
    return {**columns_by_timeframe,
            timeframe: tuple(column for column in columns_by_timeframe[timeframe] if column != name)}


def to_tuples(columns_by_timeframe: dict, timeframes: tuple[str, ...]) -> dict:
    return {timeframe: tuple(columns_by_timeframe[timeframe]) for timeframe in timeframes}


def set_key(columns_by_timeframe: dict, timeframes: tuple[str, ...]) -> tuple:
    """A set as the scored-trial index keys it: timeframe-major, independent of how a dict was built or read back."""
    return tuple((timeframe, tuple(columns_by_timeframe[timeframe])) for timeframe in timeframes)


def moves(state: dict, asset: dict, profile: dict, family: str) -> tuple:
    """Every legal move of one family from one state: the direction the gate compares in, the move's own
    name for the progress line, and the whole state it leads to.

    The catalogue fixes the order — the profile says which columns are admitted, never in what order they
    are tried — and the last column of a set is never taken out, so a state always has one."""
    timeframes, catalogue = asset["timeframes"], asset["catalogue"]["columns_by_timeframe"]
    admitted, active = profile["columns_admitted_by_timeframe"], state["columns_by_timeframe"]
    if family == config.COORDINATE_SEARCH_MOVE_FORWARD:
        return tuple(
            (config.COORDINATE_SEARCH_MOVE_FORWARD, f"+{config.feature_id(name, timeframe)}",
             {**state, "columns_by_timeframe": with_column(active, timeframe, name, catalogue[timeframe])})
            for timeframe in timeframes for name in catalogue[timeframe]
            if name in admitted[timeframe] and name not in active[timeframe])
    if column_count(active, timeframes) <= 1:
        return ()
    return tuple(
        (config.COORDINATE_SEARCH_MOVE_BACKWARD, f"-{config.feature_id(name, timeframe)}",
         {**state, "columns_by_timeframe": without_column(active, timeframe, name)})
        for timeframe in timeframes for name in active[timeframe])
