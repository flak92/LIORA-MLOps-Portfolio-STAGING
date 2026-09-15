# Skill: sorting files naming standard

A directory listing is read by eye before any parser reads it, and every
machine sorts it lexicographically — so a name is designed for the order it
will land in, on any server, under any locale. *The repository shows the destination, not the road*: the order is designed; the crawler reads against it every listed file whose row marks it, and gates nothing (`skill_scalability_crawler.md`).

- **Taxonomic ordering: the category token leads the name, so a lexicographic
  listing groups siblings into one contiguous block.** `module_*` beside
  `module_*`, `skill_*` beside `skill_*`: the eye takes the block for free,
  while a category scattered through the alphabet charges a scan and a memory
  for every lookup. The stores are a category that is also a folder: their
  token is spoken once, by the parent `store/`, the container's
  `/store` read back onto the host, and its children sort together inside it
  (`AGENTS.md` § Architecture shape), with no `store_` repeated at the root or
  beneath it. A
  file keeps its category token inside its folder (`skills/skill_*.md`),
  because a file is read detached from its folder.
- **Digits sort before letters — build granularity order on that.** In ASCII
  the digits precede every letter, so a slot filled with a number beats a
  letter placeholder at the same position; the timeframe slot standard below
  uses exactly this.
- **Zero-pad every number.** `01 < 04 < 15` sorts numerically as text;
  unpadded `1, 4, 15` sorts as `1, 15, 4`. Two digits per slot until a real
  name needs three.
- **Fixed width aligns columns.** Slots of constant width make sibling names
  line up character for character, so a difference is visible at the exact
  position where it lives — the listing becomes a table without a table.
- **Design for every collation at once.** `LC_COLLATE=C` compares bytes;
  UTF-8 locales fold case and punctuation; macOS and Windows filesystems
  compare case-insensitively. A standard survives them all when its order
  never depends on case or punctuation alone — digits-before-letters holds
  everywhere. The ecosystem-fixed names (`AGENTS.md`, `Dockerfile`, `Makefile`,
  `README.md`, `__init__.py`, `docker-compose.yml`, `requirements.txt`, the
  dot-files), `<TICKER>_README.md` and `README_module_<name>.md` keep their
  spelling, so they are the only
  names whose sort position depends on the collation: `<TICKER>_README.md` is
  first in its folder under `LC_COLLATE=C` and sorts among the lower-case names
  under `en_US.UTF-8`, and the `<TICKER>_*` block stays contiguous under both.
- **A module's orientation file is derived from its directory:
  `module_<name>/README_module_<name>.md`.** The name is not chosen — it is
  read off the folder it sits in, so `module_data → README_module_data.md`,
  `module_ml → README_module_ml.md`, `module_monitoring →
  README_module_monitoring.md`. Carrying the module in the file name is what a
  bare `README.md` cannot do: detached from its folder — in a search result, a
  diff, or a module lifted into its own repository — the name still says which
  module it opens. It sorts above that module's code and below nothing, and it
  never names a directory that is not `module_*`.
- A new sortable pattern is minted like any other convention — the seven
  conditions of `skill_self_explaining_naming.md` — and enters `AGENTS.md` in
  the commit that makes the third name follow it.

## The timeframe slot standard

A file that belongs to a timeframe family writes its granularity as five fixed
slots, finest to coarsest: `ss-mm-hh-dd-MM` (seconds, minutes, hours, days,
months). The active granularity is a zero-padded number in its slot; every
inactive slot keeps its unit letters as a placeholder.

| timeframe | slots |
|---|---|
| 1 second | `01-mm-hh-dd-MM` |
| 1 minute | `ss-01-hh-dd-MM` |
| 15 minutes | `ss-15-hh-dd-MM` |
| 1 hour | `ss-mm-01-dd-MM` |
| 4 hours | `ss-mm-04-dd-MM` |
| 1 day | `ss-mm-hh-01-MM` |
| 1 month | `ss-mm-hh-dd-01` |

A filled slot beats a placeholder at the same position, so finer granularity
always lists first; zero-padding keeps numeric order inside a slot; the fixed
slot count keeps listings column-aligned. Two patterns, two jobs: a raw store has
no sibling of another granularity to order — `raw_1m` is the one raw child of
`store/` — so it takes the compact token the code and the schema
already speak (`store/raw_1m/`, `ohlcv_1m_canonical`, `ANNUALISATION_PERIOD_15M_BARS`); the
feature files of one asset are read as one block, so they take the slots
(`BTC_features_ss-15-hh-dd-MM.parquet`, `…ss-mm-01-dd-MM…`, `…ss-mm-04-dd-MM…`).
The slots govern filesystem names only: serialised schema — table names,
feature names, artifact keys — keeps the compact token,
because those names are contracts with the files on disk. A feature parquet's
columns are the exception and carry no timeframe at all: the file name already
says which one, so repeating it in every column would be the same fact twice.
That is why a stored column reads `centered_rsi14` while the `gain_importance`
key that publishes it reads `centered_rsi14_1h` — the key has no file name
beside it to say so.
