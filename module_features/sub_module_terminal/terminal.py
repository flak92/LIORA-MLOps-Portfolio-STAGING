"""The features terminal — the feature module's text-based user interface (TUI): each asset's database, its contract
and its feature parquets, then one stage of the chain a hand chooses in the menu — bars, catalogue or status — started
through `make`, its lines on this screen as they come; then it closes. Drawn by tui.py to
module_skills/skill_tui_designer.md.

It computes nothing and writes nothing of its own: whether an asset's database, its contract and its parquets stand it
reads off the artifacts store by the descriptors config.py carries, and every stage is `make features-<stage>
ASSET=<TICKER>` — the Makefile is where a container and the order of the chain are named.

keys:
  Enter takes the option under the cursor; Esc cancels and writes nothing (exit 0); Ctrl-C ends the TUI (exit 130),
  and a stage already started stays.

output is plain — state words in brackets, no colour, no symbol, no border — when NO_COLOR is set and not empty,
TERM is dumb or standard output is not a terminal; the words, the order and the counts are the same in both.

exit codes:
  0 the stage done, or cancelled with nothing written; 1 a failure, named last on stderr; 2 an unknown argument;
  130 Ctrl-C

examples:
  make features-terminal                  the TUI over the basket
  make features-terminal ASSET=BTC        the TUI over one asset
  NO_COLOR=1 make features-terminal       the TUI in plain output
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys

from . import config, tui

STATE_COLUMNS = ("asset", "database", "catalogue", "feature parquets")
STATE_COLUMNS_DROP_ORDER = ("feature parquets", "catalogue")


# ---- the screens' own rows ------------------------------------------------------------------------------

def _option_rows(*options: str) -> list[dict]:
    return [{"option": option} for option in options]


def _cancelled_exit_code() -> int:
    """Esc, cancel or quit: one line, nothing written, exit 0."""
    print(f"{tui.state_label('CANCELLED')}  nothing written")
    return 0


def _failure_exit_code(what: str, where: str, why: str | None, next_action: str) -> int:
    """A failure as the run's last block, on stderr: exit 1."""
    tui.gum_style(tui.error_lines(what, where, why, next_action), "ERROR", sys.stderr)
    return 1


def _make(target: str, *variables: str) -> int:
    """The one call of make: its lines reach this terminal as they come, and its exit code is the answer. The
    Makefile is where a stage, a container and a tmux session are named (AGENTS.md § Canonical vocabulary)."""
    command = ("make", target, *variables)
    print(f"{tui.state_label('CURRENT')}  {shlex.join(command)}", flush=True)
    return subprocess.run(command).returncode


def _present(path) -> str:
    return "yes" if path.exists() else "no"


def _asset_rows(tickers: list[str]) -> list[dict]:
    """One row per asset — whether its database and its contract stand and how many feature parquets its folder
    holds; every cell a value as it stands, the count 0 where the folder holds none."""
    return [{"asset": ticker,
             "database": _present(config.research_ohlcv_duckdb(ticker)),
             "catalogue": _present(config.catalogue_json(ticker)),
             "feature parquets": len(list(config.artifact_dir(ticker).glob(f"{ticker}_features_*.parquet")))}
            for ticker in tickers]


# ---- the actions ----------------------------------------------------------------------------------------

def _write_stage(ticker: str, stage: str) -> int:
    """One stage of this module's chain for one asset, started through make after the plan and its gate."""
    target = f"{config.MODULE_TOKEN}-{stage}"
    tui.gum_table(("parameter", "value"), [
        {"parameter": "asset", "value": ticker},
        {"parameter": "stage", "value": stage},
        {"parameter": "writes", "value": config.WRITES_BY_STAGE[stage].replace("<TICKER>", ticker)}])
    print(f"command         {shlex.join(('make', target, f'ASSET={ticker}'))}")
    print()
    decision = tui.gum_choose(f"{stage} {ticker}?", _option_rows(stage, "cancel"), "option")
    if decision != stage:
        return _cancelled_exit_code()
    print()
    code = _make(target, f"ASSET={ticker}")
    print()
    if code:
        return _failure_exit_code(f"{target} of {ticker} ended with exit {code}",
                                  shlex.join(("make", target, f"ASSET={ticker}")), f"make exited with {code}",
                                  "read make's lines above")
    tui.gum_style([f"{tui.state_label('DONE')}  {target} of {ticker} done"], "DONE")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -B -m module_features.sub_module_terminal.terminal",
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--tickers", required=True, help="the assets this run is about, comma-separated, e.g. BTC")
    args = parser.parse_args()
    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]

    if not sys.stdin.isatty():
        return _failure_exit_code("the TUI needs a terminal", "standard input", "it is not a terminal, so no "
                                  "choice can be asked", "run make features-terminal in a terminal")
    if not shutil.which("gum"):
        return _failure_exit_code("gum is not on PATH", "PATH", None,
                                  "install gum 2: https://github.com/charmbracelet/gum#installation")
    if not tickers:
        return _failure_exit_code("the TUI needs an asset", "--tickers", "it names none", "ASSET=<TICKER> on the make line")
    try:
        catalogues = sum(1 for ticker in tickers if config.catalogue_json(ticker).exists())
        tui.gum_style(["Features terminal", f"{' '.join(tickers)} · {len(tickers)} assets · {catalogues} catalogues"],
                      "CURRENT")
        print()
        tui.gum_table(STATE_COLUMNS, _asset_rows(tickers), STATE_COLUMNS_DROP_ORDER)
        print()
        action = tui.gum_choose("action", _option_rows(*config.STAGES, "quit"), "option")
        if action in (None, "", "quit"):
            return _cancelled_exit_code()
        ticker = tui.gum_choose("asset", [{"asset": ticker} for ticker in tickers], "asset")
        if ticker in (None, ""):
            return _cancelled_exit_code()
        return _write_stage(ticker, action)
    except KeyboardInterrupt:
        print()
        print(f"{tui.state_label('CANCELLED')}  ended; a stage already started stays", file=sys.stderr)
        return tui.INTERRUPTED_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
