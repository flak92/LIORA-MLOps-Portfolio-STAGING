"""The barrier coordinate of the search: the geometry of an event, moved one grid point at a time.

Two families, in the order a pass expands them. **trade** moves the trade's own exit — its take-profit and
its stop, which the label never sees — and a child of it reuses its parent's fits and its parent's
predictions, because neither depends on where a position leaves. **label** moves the geometry Y itself is
written with — the multiplier the barriers stand at and the horizon they stand for — and a child of it is
Y walked again, X joined to the decisions the new horizon admits, and three fits.

That ordering is the whole economy of the loop: the cheap children are scored while their parent's
predictions are still in hand, and only then is that material thrown away."""

from __future__ import annotations

from . import config

FAMILY_TRADE = "trade"
FAMILY_LABEL = "label"
FAMILIES = (FAMILY_TRADE, FAMILY_LABEL)
# which coordinates each family moves, and what a child of it must build again
FAMILY_COORDINATES = {FAMILY_TRADE: ("take_profit_atr_multiplier", "stop_loss_atr_multiplier"),
                      FAMILY_LABEL: ("atr_barrier_multiplier", "label_horizon")}
FAMILY_REBUILD = {FAMILY_TRADE: config.REBUILD_BACKTEST, FAMILY_LABEL: config.REBUILD_LABELS}


def to_barrier(row: dict) -> dict:
    """A trial's barrier geometry as a state carries it: a JSON round trip leaves a whole number where a
    multiplier wants a float, and the key compares values, not their spelling."""
    return {name: cast(row[name]) for name, cast in config.BARRIER_COORDINATE_CASTS.items()}


def grid(profile: dict, name: str) -> list:
    """One coordinate's grid as the state carries its values, in the order it is searched."""
    return [config.BARRIER_COORDINATE_CASTS[name](value) for value in profile["grid_by_coordinate"][name]]


def moves(state: dict, asset: dict, profile: dict, family: str) -> tuple:
    """Every legal move of one family from one state: one grid point down and one up, per coordinate the
    family moves, in the order the register names them.

    A barrier move only ever grows a state, so it is compared forward — strictly better on every validation
    fold. A grid that does not hold the state's own value fails on the lookup: a profile says where a search
    may go, and it has to say where it starts."""
    del asset
    return tuple(
        (config.COORDINATE_SEARCH_MOVE_FORWARD,
         f"{name} {state[name]} -> {points[neighbour]}",
         {**state, name: points[neighbour]},
         FAMILY_REBUILD[family])
        for name in FAMILY_COORDINATES[family]
        for points in (grid(profile, name),)
        for neighbour in (points.index(state[name]) - 1, points.index(state[name]) + 1)
        if 0 <= neighbour < len(points))
