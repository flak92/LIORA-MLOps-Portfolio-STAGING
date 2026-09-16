# Project skills — the index

Where every rule of the project is written down. This file links; it holds no
rule of its own, so nothing here can disagree with the document it points at.
*The repository shows the destination, not the road*.

Ownership decides location, and `AGENTS.md` § The default choice holds the rule:
a module's own skills live in that module's `skills/`, the skills that cross
modules live here, in `module_skills/` — the canon, with its one sub-module, the
scalability crawler, which reads each file a hand lists against the skills a hand marks for it. A
rule two sub-modules draw to crosses them and lives here too — `skill_tui_designer.md`, the
standards of a TUI's screens; a rule about one sub-module alone stays beside its code. Each is
written exactly once, and a skill is named below by the path it holds in the tree.

## Cross-cutting — the skills in this directory

| skill | what it governs |
|---|---|
| [glossary.md](glossary.md) | the name register: one concept, one name, in code, artifacts and interface — and the register of the duplicates no module may import across |
| [skill_agent_first_development.md](skill_agent_first_development.md) | how an agent works on this project — subtract, don't add |
| [skill_asset_containers.md](skill_asset_containers.md) | the compose topology — one image, three runners, two residents — and the scoped socket rule: the runtime contract every module runs inside |
| [skill_determinism.md](skill_determinism.md) | bit parity, thread caps and where speed is allowed to come from |
| [skill_pre_aws_solution.md](skill_pre_aws_solution.md) | the Pre-AWS direction: which local boundary answers to which standard cloud primitive, the twelve classes, the four seat paragraphs, the ladder, the non-goals, what the shape holds and what it does not, and why none of it is built |
| [skill_scalability_crawler.md](skill_scalability_crawler.md) | the scalability crawler: the skill matrix, the mission, the reports and the snapshot that dates them |
| [skill_self_explaining_naming.md](skill_self_explaining_naming.md) | names derived from a closed grammar, and how a new convention is minted |
| [skill_sorting_files_naming_standard.md](skill_sorting_files_naming_standard.md) | taxonomic ordering, zero-padding and the timeframe slot standard |
| [skill_tui_designer.md](skill_tui_designer.md) | a text-based user interface (TUI) in gum: its instruments, its screen order, its tables, lists and forms, feedback, failures, exits, colour and plain output |

## Described, not written

Skills that exist as rows and not as files, each placed by ownership, with the
one condition under which it is written:
[../AGENTS.md](../AGENTS.md) § Skills absent here, described. This index holds
no row of it.

## module_data

Orientation: `module_data/README_module_data.md`

| skill | what it governs |
|---|---|
| `module_data/skills/skill_candle_canonicalisation.md` | candle validity, the primary-failover decision table, volume, forward fill, provenance and the canonical storage |
| `module_data/skills/methodology_data.md` | the venue endpoints, units and time, and the limitations of acquisition |

## module_features

Orientation: `module_features/README_module_features.md`

| skill | what it governs |
|---|---|
| `module_features/skills/skill_feature_taxonomy.md` | the timeframe register, the terms, the composition grammar, the scope nesting and the warm-up |
| `module_features/skills/methodology_features.md` | every catalogued feature definition, equation by equation, with its histories and citations |
| `module_features/sub_module_coordinate_search_terminal/skill_coordinate_search_terminal.md` | the coordinate search terminal: its five actions, what each screen holds and what each answer writes, the profile it drafts and the two `make` targets it starts |

## module_ml

Orientation: `module_ml/README_module_ml.md`

| skill | what it governs |
|---|---|
| `module_ml/skills/methodology_ml.md` | the research layer equation by equation, with its citations |

## module_monitoring

Orientation: `module_monitoring/README_module_monitoring.md`

| skill | what it governs |
|---|---|
| `module_monitoring/skills/skill_dashboard_conventions.md` | the static page, its BEM classes and its state |
| `module_monitoring/skills/skill_devops_panel.md` | the DevOps panel: its views, the action allowlist and its guard, and the one docker socket |
