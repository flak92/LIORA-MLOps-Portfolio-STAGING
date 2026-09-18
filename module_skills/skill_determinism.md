# Skill: determinism — the same bits, and where speed comes from

Two runs of the same experiment produce the same bits — otherwise
out-of-sample results lose their evidential value. The claim is scoped: bit
parity for the same code, the same fixed input window and the same execution
environment; the four library pins do not claim byte-identical environment
reconstruction at an arbitrary future date. *The repository shows the destination, not the road*: bit parity is the proof; no test suite stands in for it.

- Thread caps are frozen at one: `nthread=1` (XGBoost), `OMP_NUM_THREADS=1`.
  Multi-threaded float summation reorders, two runs diverge, backtests stop
  being comparable. Never raise them, on any machine size.
- The seed is fixed (`SEED = 42`), Optuna runs sequentially (`n_jobs=1`, TPE
  seeded) — a parallel study draws trials in nondeterministic order.
- DuckDB aggregations pin their order (`arg_min`/`arg_max` by timestamp,
  explicit `ORDER BY`); artifact writers sort before writing.
- The standard for a change that should not alter results is bit parity:
  rerun the affected stages and compare the bytes. "Looks the same" is not a
  standard; identical bytes are.

Parallelism is an execution-time optimisation — never at the cost of
deterministic correctness:

- Speed comes only from external parallelism: independent processes side by
  side, one asset per process, all under the same fixed `SEED` — never from
  raising thread caps inside one process.
- Width is measured at invocation, never hardcoded — `JOBS` in the Makefile,
  `module_ml/skills/methodology_ml.md` § 11; `JOBS=n` overrides. A literal written for one
  machine is silently wrong on every other.
- Before optimising, measure the time distribution; after optimising, compare
  against the run-to-run spread — an improvement within the spread is noise
  and is rejected.
- A stage that is the only writer to a shared resource stays sequential;
  `data-ingest` stays sequential because a memory ceiling is per process and
  the sum of the concurrent ceilings is what has to fit the host.
- **The seat.** Read forward the caps travel unchanged: `nthread=1` and
  `OMP_NUM_THREADS=1` are the environment of the one task definition, and
  `JOBS` is the width of the Map over `TICKERS` in the state machine (AWS Step
  Functions) — measured as it is measured here, never a literal in the
  definition; `skill_pre_aws_solution.md` § The Makefile is the developer
  interface.
