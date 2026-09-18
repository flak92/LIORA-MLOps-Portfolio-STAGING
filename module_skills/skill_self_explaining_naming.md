# Skill: self-explaining naming conventions

Every name in this repository — a variable, a parameter, a function, a key, a
directory — must explain itself, so an agent never has to guess. *The repository shows the destination, not the road*:
the names carry the discipline; no check gates them, and the crawler's reports say where
they drift (`module_skills/sub_module_scalability_crawler/skill_scalability_crawler.md`).

- **The name carries the information.** What a thing is, what it measures and
  in what unit are readable from the identifier alone, without opening another
  file — and without redundancy: a name repeats nothing its scope already
  states.
- **The measure is thoughts, not tokens.** A name is good when it minimises
  the number of thoughts an agent must think to use it correctly. Every
  obscure identifier forces a chain of decoding steps before the real work
  starts, and those steps are the cost — not the characters saved.
- **Self-explaining names are the interface.** Agents understand and extend
  this repository through its names; a name that needs a lookup turns every
  reader into an archaeologist.
- **Names are derived, not invented — the way BEM derives CSS class names.**
  Every layer has a closed grammar, fixed in `AGENTS.md`: a verb from a closed
  list for functions that act, no verb at all for functions that *are* a
  quantity, `<what>_<unit>` for quantities, `<population>_rows` for index
  arrays, `<category>_<detail>/` for a module's directory and
  `store/<content>/` for a store — the category spoken once, by the parent
  folder. Given the layer, the name
  follows; there is nothing left to invent, and nothing to argue about.
- **Units belong to quantities.** A name holding a number says its unit —
  counts, rates, durations, sizes, intervals — while enumerations, paths and
  names carry none, a collection keeps the unit of its values, and a local
  abbreviation is free inside one function.
- **A standard term beats an invented one.** If a concept already has a widely
  recognised name, that name wins; `AGENTS.md` holds the rule.
- **One concept, one name.** A synonym forces the reader to decide whether two
  names are one thing or two — a thought the code should never demand. And its
  converse, **one name, one concept**: a name denoting two things in one scope
  demands the same thought from the other side. `AGENTS.md` holds the rule and
  enumerates the scopes it binds.
- **The glossary confirms, it never decodes.** `glossary.md` registers what a
  name already says; if the register is needed to understand the name, the
  name is wrong.
- **A name gives way to a more derivable one.** The test is not whether the old
  name still works, but whether the family's grammar yields a name that
  classifies better, shows its family sooner or sorts with its siblings — when
  it does, the rename is the cheap part and the reasoning step it removes is
  paid back on every later reading. A serialised name (an artifact key, a
  parquet or database column, a feature) is a contract with the files on disk,
  so it moves only together with everything that writes, reads or stores it, in
  one commit.

## Minting a new convention

The grammars above are not the last ones this repository will need. A new one
is worth establishing when it meets all seven conditions, and it is not a
convention when it misses any:

- **Closed list.** The allowed words can be listed. `load_`, `write_`,
  `fetch_`, `parse_`, `to_`, `build_` is a list; "use a sensible verb" is not.
- **Derivable.** A reader can construct the correct name without asking anyone
  and without reading a second document.
- **Normative source.** The rule lives in exactly one place and every other
  document points at it. Two copies of a rule drift, and the drift is
  discovered by the reader who trusted the wrong copy. Which place is decided
  by ownership — `AGENTS.md` § The default choice.
- **It must be able to fail.** There is a name the rule forbids. A rule that
  excludes nothing describes taste, not structure.
- **Scope.** A convention states which language, layer and object kind it
  governs; a rule with no stated scope collects exceptions instead of naming
  them.
- **Boundary.** A convention states where an external format overrides it —
  the Lean raw tree keeps Lean's casing and layout, and the adapter speaks the
  external vocabulary. A named exception is a boundary; an unnamed one is rot.
- **Migration cost.** A convention is minted only when the ambiguity it
  removes is worth more than the one-time cost of the renames it forces.

Mint at the **third** occurrence of a pattern: two is a coincidence, three is a
convention. Write it into `AGENTS.md` in the same commit that makes the third
name follow it, and state what it forbids — the forbidden form is the half of
the rule that does the work.

## The naming review

Before a module, a file, a function, a compose service, a network, a volume, a
folder, an artifact, a make target, a JSON key or an environment variable is
added, eight answers are written down, in order:

1. what does it represent;
2. how long does it live;
3. who writes or creates it;
4. who reads or uses it;
5. does the name reveal that responsibility;
6. would a second asset force a rename;
7. is its future cloud equivalent obvious from the responsibility
   (`skill_pre_aws_solution.md`);
8. is the term already in use elsewhere (`glossary.md`).

A no at 5 or 6 means the name is wrong. The classes a name is placed in are
`skill_pre_aws_solution.md` § Every object is classified before it is placed.

## The closed list absorbs its synonyms

The generic verbs a reader may reach for, and the house form each already has —
one concept, one name, so none of them enters:

| reached for | written as |
|---|---|
| `save_`, `publish_` | `write_` |
| `read_` | `load_` |
| `download_` inside a function | `fetch_` — a stage file may be `download_<venue>.py`, because a file names a stage |
| `generate_`, `calculate_`, `compute_`, `aggregate_` | `build_<object>`, or the quantity itself with no verb |
| `train_` | `fit`, at the xgboost boundary |
| `evaluate_` | `<object>_evaluation`, the noun the stage writes |
| `process`, `handle`, `run`, `execute`, `manage`, `do_work` | never |

A function that computes never writes; a function that writes says so in its
verb. When the two would share a body, the body is split at the store: the
quantity is built, then written.
