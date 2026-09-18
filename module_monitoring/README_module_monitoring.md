# module_monitoring — what the runtime modules measured, made readable

The front door of this module: what it is, where its responsibility stops, and
how to run it. The page's own conventions are `skills/`; the panel's rule and the
terminal's sit beside their code, `sub_module_devops/skill_devops_panel.md` and
`sub_module_terminal/skill_monitoring_terminal.md`; none is repeated here. *The
repository shows the destination, not the road*.

`module_monitoring` computes nothing about the market. It presents what
`module_data`, `module_features` and `module_ml` already measured about
themselves and the dates of the canon's crawler's reports, it runs the one
server that serves it, and it carries the terminal a hand switches that server
from.

## Where the responsibility stops

It reads snapshots; it never opens an asset's database and never recomputes a
number. Every value on the page was produced by the module that owns it —
`module_data/status.py`, `module_features/status.py`, `module_ml/status.py` and `module_skills/sub_module_scalability_crawler/status.py`. A metric that does not exist
in a snapshot does not appear on the page.

The same line is a storage seam: the four snapshots are status objects this module reads and never produces, and the run record is the run object `record.py` writes from outside every stage and this module reads
— about the run, not about the market; the page and its scripts are static
files; only the run and proxy routes are a running process. The
direction:
`module_skills/skill_pre_aws_solution.md`.

## What it runs

| piece | entry | does |
|---|---|---|
| the server | the `dashboard` service of `make on` | one server, the dashboard: the page, the snapshot route, the run routes and the proxy — `python -m module_monitoring.serve`, the resident's own `command:` |
| the DevOps panel | the `devops` service of `make on` | `sub_module_devops` — `python -m module_monitoring.sub_module_devops.serve`, the second resident: the containers, networks and volumes, and the one container that holds the docker socket |
| the terminal | `make monitoring-terminal` | `sub_module_terminal`: the four snapshots and the run records on one screen, then `on` or `off` through `make` — on the host, in no container |
| the presentation switch | `make on` / `make off` | the two residents up with the page's address printed and opened, and `docker compose down` — every container of this project stopped and removed |

`make on` builds the one image every service runs, `liora-1m-pipeline`, brings
the two residents up — `dashboard` and `devops`, each a role of that image and
not an image of its own — then prints the page's address and opens it;
`make off` is `docker compose down`, every container of this project stopped
and removed. Neither the dashboard nor the panel has a target of its own: each
is a service's `command:` in `docker-compose.yml`, raised and taken down by
that one switch.

The dashboard is published on the host at `127.0.0.1:<port>` — the address
`make on` prints (`module_skills/skill_asset_containers.md` § The
topology). The four snapshots it reads,
`store/status/data_status.json`, `store/status/features_status.json`, `store/status/ml_status.json` and
`store/status/skills_status.json`,
live in the status store beside the other stores, are served under `/store_status/<name>`, and are committed so the page opens on a fresh clone.

## Extending

| to add | change |
|---|---|
| a tab | one pill, one section and one section script, wired by `data-key` — `index.html` and the script own it (`skills/skill_dashboard_conventions.md` § Extending); its row in § Design rationale here, and the page's navigation in `module_skills/glossary.md` § DevOps panel moves in the same commit |
| a route | one branch of `DashboardHandler.do_GET` or `do_POST` in `serve.py`, with its constant in `config.py` where it builds a path — or of `PanelHandler` in `sub_module_devops/serve.py`, with its Engine path in `sub_module_devops/config.py`; the places that list routes move with it — the server's docstring, § Design rationale here, the route table of `sub_module_devops/skill_devops_panel.md` — and every key the route publishes enters `module_skills/glossary.md` |
| a column | one edit in the render function that emits the row, the header being built beside it; the key it reads is the snapshot's, registered in `module_skills/glossary.md` by the module that measured it |
| an action of the terminal | one token in `sub_module_terminal/config.py` `STAGES` and its line in `WRITES_BY_STAGE`, for a target the Makefile carries; the menu row of `module_skills/glossary.md` § Terminals moves with it |

## Design rationale

Why each object of this module sits where it does — the answers of
`module_skills/skill_self_explaining_naming.md` § The naming review written
down, one row per object, analogous pair or the module's documents; the mapping
row it answers to is `module_skills/skill_pre_aws_solution.md` § The mapping
table, cited by its *responsibility* column and never repeated.

| object | why here | why beside these | why this boundary | answers to |
|---|---|---|---|---|
| `config.py` | The one place this module builds a path or a URL (its docstring): the directory of a run record under `store/run_records/<run_id>/`, the panel's compose service name on the internal port, the polling cadence, the bound on a proxied exchange (`PANEL_FETCH_TIMEOUT_SECONDS`; the panel's own Engine bound is `ENGINE_EXCHANGE_TIMEOUT_SECONDS` in `sub_module_devops/config.py`) and `MODULE_MONITORING_DIR` — this module's own directory, the web root `serve.py` serves the page from. | `serve.py`, `sub_module_devops/serve.py` and `sub_module_terminal/terminal.py` import it, it reads `STORE_RUN_RECORDS_DIR` and `STORE_STATUS_DIR` from the environment the launcher sets, and the per-asset artifact paths stay in the configs of the modules that produce them (its docstring). | Its address is a compose service name on `CONTAINER_PORT` and its record root is the `STORE_RUN_RECORDS_DIR` the launcher names, so a reader reaches `devops` by the same name and a record lands in the same store on whatever host runs the services. | MONITORING — a small reader process |
| `serve.py` | The one server, the dashboard (its docstring; `module_skills/skill_asset_containers.md` § The topology): its directory with its run and proxy routes. | It serves `module_monitoring/` as a directory — the page, its scripts and `sub_module_devops/` — maps the route `/store_status/<name>` onto `store_status_file()` of `config.py` for the snapshots, answers `/runs/<run_id>` with the stage records `record.py` left, and imports nothing of another module. | It binds `CONTAINER_PORT` inside its container and compose publishes the dashboard on loopback alone (§ What it runs; `skills/skill_dashboard_conventions.md`), so a reader reaches it through the tunnel (`ssh -L`, `README.md` § Quickstart) whichever host runs it. | MONITORING — a small reader process |
| `index.html` + `style.css` | The page and its one stylesheet — plain HTML and CSS that `serve.py` serves as files from its directory (`skills/skill_dashboard_conventions.md`). | `index.html` links `style.css` and loads `page.js`, `data.js`, `asset.js`, `ml.js`, `run.js` and `scalability.js` in that order, and `sub_module_devops/index.html` links the same stylesheet. | Served from `module_monitoring/` on `CONTAINER_PORT`, the page opens at the same address through the tunnel whichever host serves it. | MONITORING — the static dashboard |
| `page.js` | The functions both pages load — `millisecondsSinceEpoch`, the one parser of the UTC text the snapshots and the recorder write, and the `format`, `build`, `append`, `render` and `init` families, `buildTable` and `renderTable` among them — and `PILL_HOOKS`, the state the pill machinery keeps (its header comment). | `index.html` loads it first and `sub_module_devops/index.html` loads it too, so `data.js`, `asset.js`, `ml.js`, `run.js`, `scalability.js` and `devops.js` call it and it calls none of them. | It writes into no page-specific element, so the panel a directory below loads the same file from the same root wherever the server runs. | MONITORING — the static dashboard |
| `asset.js`, `data.js`, `ml.js`, `run.js`, `scalability.js` | The section scripts of the status page, one per tab family — the ML assets panel, the pipeline and data-quality tabs, the ML research tabs, the lifecycle tab, the scalability tab (their header comments). | Analogous scripts over `page.js`: `data.js` fetches `/store_status/data_status.json`, naming no provider — it builds one section, one column and one share cell per entry of the snapshot's `source_venues`, and sets each asset's observation lag and measurement age against its `download_cadence_minutes`, `ml.js` fetches `/store_status/ml_status.json` and `/store_status/features_status.json` and feeds `asset.js`; `run.js` fetches `/runs` and `/runs/<run_id>`, and `scalability.js` fetches `/store_status/skills_status.json`. | Each renders numbers a snapshot or the run record already holds and derives no result of its own — only presentation arithmetic over what was measured, which `skills/skill_dashboard_conventions.md` licenses (§ Where the responsibility stops), so the page reads the same snapshot names and the same `/runs` routes wherever it is served. | MONITORING — the static dashboard |
| `__init__.py` | The package that makes `python -m module_monitoring.serve` a command, its docstring the module's responsibility in one line. | It names the server and the record it reads, and imports nothing. | The same `python -m module_monitoring.serve` is the `dashboard` service's command (`docker-compose.yml`), unchanged whichever host starts it. | MONITORING — a small reader process |
| `sub_module_devops/` | The engine's views: its own `serve.py` speaks the Docker Engine API over the one socket, with its own `config.py`, `main()`, page and scripts, its front door `README_sub_module_devops.md` and its rule `skill_devops_panel.md` beside them (§ The one socket, and what containment means). | Nested because the dashboard serves its own directory (`sub_module_devops/skill_devops_panel.md` § Why a sub-module, and why that name), and the dashboard proxies its API under `/devops/*` by service name while its page loads `page.js`; its documents sit beside its code, the sub-module row of `AGENTS.md` § Canonical vocabulary. | The socket is mounted into `devops` and no other service, and `devops` publishes no port (`module_skills/skill_asset_containers.md` § The topology), so the panel is reached only through the dashboard's proxy — the same socket path and the same route behind the tunnel, whichever host's daemon it reads. | INFRASTRUCTURE — the engine's views |
| `sub_module_terminal/` | The module's terminal, the hand's instrument over its switch: `terminal.py` with `main()`, its own `config.py`, `tui.py`, its front door `README_sub_module_terminal.md` and its rule `skill_monitoring_terminal.md` beside them — the shape every module's terminal shares (`AGENTS.md` § Canonical vocabulary, the row *sub-modules*). | Nested because it is an entry point and not a stage: it shows the four snapshots and the run records the dashboard reads, through this module's own `config.py`, and starts `on` or `off` through `make` and nothing else; `tui.py` is one file with every other terminal's and the crawler's, five times by extraction. | It runs on the host's `python3` with gum, in no container and no venv, reads the two stores the launcher names and computes nothing; the same screen opens over any host's stores, and the Makefile it calls is the one of the directory it was opened in. | no row — a hand's instrument over the Makefile, seated beside the module whose targets it starts |
| `store/status/data_status.json` + `store/status/features_status.json` + `store/status/ml_status.json` + `store/status/skills_status.json` | Status objects that `module_data/status.py`, `module_features/status.py`, `module_ml/status.py` and the crawler write into the status store and the page reads, committed so the page opens on a fresh clone (§ What it runs). | Outside this module, in the status store beside the other stores; `serve.py` maps the route segment `STORE_STATUS_ROUTE_SEGMENT` onto `store_status_file()` under `STORE_STATUS_DIR` — `/store_status/data_status.json` in `data.js`, and in `ml.js` and `scalability.js` the one prefix `/store_status/` with their file names. | Their paths are `STORE_STATUS_DIR / <name>` in the configs that write them and in this module's config that reads them; the five points that turned when the snapshots left this directory — two path constants, the served root, two literal fetches — are the ones `module_skills/skill_pre_aws_solution.md` § What stays as it is, and why, named; the third and the fourth snapshot arrived by the same route. | STORAGE — status and run objects |
| the module's documents — `README_module_monitoring.md`, `skills/`, and each sub-module's README and skill | This orientation and the normative documents of `skills/`, filed by ownership (`AGENTS.md` § The default choice); a sub-module's rule beside its code (`module_skills/glossary.md` § Documentation ownership). | The orientation points at the documents beside it (§ Its normative skills), every rule about the page sits in `skills/` (`AGENTS.md` § Canonical vocabulary, the row *a module's own skills*), and a rule about one sub-module alone sits in that sub-module's directory. | Tracked files under `module_monitoring/` that no stage and no route reads, travelling with the code beside them — the same paths beside the code wherever the code is. | no row — a document that travels with the task's code, seated beside its module |

## Its normative skills

| document | answers |
|---|---|
| `skills/skill_dashboard_conventions.md` | the static page, its BEM classes and its state |
| `sub_module_devops/skill_devops_panel.md` | the DevOps panel: its views, the action allowlist and its guard, and the one socket |
| `sub_module_terminal/skill_monitoring_terminal.md` | the monitoring terminal: its opening screen, its actions — the presentation switch —, what it starts through make, and its exits |

The compose topology is a contract between the
infrastructure and all four runtime modules, so it lives in
`module_skills/skill_asset_containers.md`,
not here. The rest of the project-wide rules are indexed by
`module_skills/README.md`.
