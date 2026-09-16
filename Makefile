# the host side of the dashboard's mapping, measured at invocation: the port the dashboard already publishes,
# else the first free port from 8900 upward — another project on this host, or a checkout of LIORA run under
# COMPOSE_PROJECT_NAME=, may hold 8900
PORT ?= $(shell p=$$(docker compose port dashboard 8900 2>/dev/null | cut -d: -f2); \
                if [ -z "$$p" ]; then p=8900; while python3 -c "import socket, sys; sys.exit(0 if socket.socket().connect_ex(('127.0.0.1', $$p)) == 0 else 1)"; do p=$$((p+1)); done; fi; \
                echo $$p)
# measured once per make: the mapping and the page ask one port
PORT := $(PORT)
# the docker group of this host, so the one container that holds the socket can read it without being root
DOCKER_GID  := $(shell getent group docker | cut -d: -f3)
COMPOSE_ENV := UID=$(shell id -u) GID=$(shell id -g) PORT=$(PORT) DOCKER_GID=$(DOCKER_GID)
COMPOSE     := $(COMPOSE_ENV) docker compose
# the five stores of this checkout, one folder each under store/, one variable per store — the store contract every
# config.py reads; facts, not settings: docker-compose.yml mounts ./store/<content> at /store/<content>, the same
# <content> on both sides, record.py lists the four pipeline stores among them by these host paths, and every container
# sees /store/<content> in its own environment
export STORE_RAW_1M_DIR := $(CURDIR)/store/raw_1m
export STORE_ASSETS_ARTIFACTS_DIR := $(CURDIR)/store/assets_artifacts
export STORE_TRIALS_DIR := $(CURDIR)/store/trials
export STORE_RUN_RECORDS_DIR := $(CURDIR)/store/run_records
export STORE_STATUS_DIR := $(CURDIR)/store/status
STORES := store/raw_1m store/assets_artifacts store/trials store/run_records store/status
# mlflow speaks at import: it opens a telemetry client and prints an agent hint unless told otherwise. Both are off
# here and in docker-compose.yml, so a stage run in a venv is as quiet and as offline as one run in a container
export MLFLOW_DISABLE_TELEMETRY := true
export MLFLOW_DISABLE_AGENT_HINT := 1
# the basket — the one definition. ASSET=<TICKER> on the make line narrows every per-asset stage to one asset; make
# exports ASSET into every recipe's environment, which is harmless: no service reads it, and a runner is told its assets
# by --tickers
TICKERS     := BTC
TICKER_LIST := $(if $(ASSET),$(ASSET),$(TICKERS))
# the basket as one argument — --tickers takes a comma-separated value, printf/xargs take one ticker per line. It goes to
# the basket-wide stages, which ASSET never narrows: a snapshot of one asset would silently drop the rest of the basket
# from the page, and the download is one process per venue for the whole basket
TICKERS_CSV := $(shell echo $(TICKERS) | tr ' ' ,)
# one process per asset with its threads pinned to 1; the width is min(cores, available GiB), at least 1
JOBS ?= $(shell c=$$(nproc 2>/dev/null || echo 1); \
                g=$$(awk '/MemAvailable/ {printf "%d", $$2 / 1048576}' /proc/meminfo 2>/dev/null); \
                if [ -n "$$g" ] && [ "$$g" -lt "$$c" ]; then c=$$g; fi; \
                if [ "$$c" -lt 1 ]; then echo 1; else echo $$c; fi)
# the proposal a promotion copies, by its rank in the coordinate search result
PROPOSAL ?= 1
# the tmux session the detached coordinate search runs in: one per asset, named for it
COORDINATE_SEARCH_SESSION = coordinate-search-$(shell echo $(ASSET) | tr A-Z a-z)
RUN_ID = $(shell date -u +%Y%m%dT%H%M%SZ)_$(shell git rev-parse --short HEAD)
# a stage runs in a one-off container of its module's runner service — a role, not an image; nothing resident is assumed
# for compute. `env $(COMPOSE_ENV) docker compose`, because $(COMPOSE) cannot cross xargs
run    = env $(COMPOSE_ENV) docker compose run --rm -T
# $(1) runner service, $(2) python module, $(3) width: the same stage for every ticker of the list, one one-off container each
fanout = printf '%s\n' $(TICKER_LIST) | xargs -P $(3) -I{} $(run) $(1) python -m $(2) --tickers {}
# $(1) runner service, $(2) python module: a basket-wide stage, once, the whole basket
basket = $(run) $(1) python -m $(2) --tickers $(TICKERS_CSV)

.DEFAULT_GOAL := help

help:            ## list targets
	@grep -E '^[a-zA-Z][a-zA-Z0-9_-]*:[^#]*##' $(MAKEFILE_LIST) | sed -E 's/:[^#]*## / — /'

all:             ## the whole chain from a fresh clone: the image, raw data, canonical, features, ML, snapshots
	$(MAKE) build data-all features-all ml-all
build: | $(STORES) ## the image every service runs
	$(COMPOSE) build

# a bind-mounted store must exist before compose mounts it: Docker would create a missing source directory as root, and the
# ${UID}:${GID} container could not write it — order-only, so a store's contents never make a target stale; every new
# compose target joins the line below
$(STORES):
	@mkdir -p $@
data-download data-ingest data-status features-bars features-catalogue features-status ml-labels ml-hpo ml-train ml-strategy ml-status ml-coordinate-search ml-coordinate-search-promote on all-record: | $(STORES)

data-download:   ## raw 1m candles of both venues into store/raw_1m — one process per venue, a venue's rate limit being per process
	$(call basket,data,module_data.download_binance)
	$(call basket,data,module_data.download_bybit)
data-ingest:     ## ZIPs -> one canonical series per asset, one asset at a time
	$(call fanout,data,module_data.ingest,1)
data-status:     ## data_status.json -> store/status
	$(call basket,data,module_data.status)
data-all:        ## the data chain in order
	$(MAKE) data-download data-ingest data-status

features-bars:   ## canonical 1m -> every timeframe of the register, in each asset's own database
	$(call fanout,features,module_features.bars,$(JOBS))
features-catalogue: ## every catalogued column on the decision grid, one parquet per timeframe per asset, and <TICKER>_catalogue.json — the contract the ML layer reads
	$(call fanout,features,module_features.catalogue,$(JOBS))
features-status: ## features_status.json -> store/status: the catalogue's facts and each asset's row counts
	$(call basket,features,module_features.status)
features-all:    ## the feature chain in order
	$(MAKE) features-bars features-catalogue features-status

ml-labels:       ## triple-barrier labels on the canonical 1m path
	$(call fanout,ml,module_ml.labels,$(JOBS))
ml-hpo:          ## Optuna TPE per asset (one process per asset, nthread=1)
	$(call fanout,ml,module_ml.hpo,$(JOBS))
ml-train:        ## out-of-fold predictions + final-holdout report per asset
	$(call fanout,ml,module_ml.train,$(JOBS))
ml-strategy:     ## entry edge threshold on the validation folds, final-holdout PnL
	$(call fanout,ml,module_ml.strategy,$(JOBS))
ml-status:       ## ml_status.json -> store/status, and <TICKER>_README.md
	$(call basket,ml,module_ml.status)
ml-all:          ## the ML chain in order
	$(MAKE) ml-labels ml-hpo ml-train ml-strategy ml-status
ml-coordinate-search: ## coordinate search on the validation folds under the asset's profile and frozen parameters; resumes; promotes nothing
	$(call fanout,ml,module_ml.coordinate_search,$(JOBS))
# a hand's decision for one asset, never fanned out: ASSET= is required
ml-coordinate-search-promote: ## copy proposal PROPOSAL=<n> (default 1) of one asset into <TICKER>_feature_set.json and <TICKER>_barriers.json, then rerun its ML chain either way; ASSET= is required
	$(if $(ASSET),,$(error ASSET=<TICKER> is required))
	$(run) ml python -m module_ml.coordinate_search_promote --tickers $(ASSET) --proposal $(PROPOSAL)
	$(MAKE) ml-all ASSET=$(ASSET)
# the detached twin: the same search in a tmux session that outlives the terminal, started in this checkout, one asset per
# session; the session ends with the search — `<TICKER>_coordinate_search.json` and the page are the record.
# A plain make, not $(MAKE): the session is a new process of the tmux server, and a recipe line carrying $(MAKE) runs
# even under -n
tmux-ml-coordinate-search: ## the search detached in tmux session coordinate-search-<ticker>, alive after the terminal closes and gone with the search; tmux attach -t coordinate-search-<ticker> to watch, Ctrl-C stops, a rerun after it ends resumes; ASSET= is required
	$(if $(ASSET),,$(error ASSET=<TICKER> is required))
	@tmux has-session -t $(COORDINATE_SEARCH_SESSION) 2>/dev/null && echo '$(COORDINATE_SEARCH_SESSION) is already running — tmux attach -t $(COORDINATE_SEARCH_SESSION)' || tmux new-session -d -s $(COORDINATE_SEARCH_SESSION) -c $(CURDIR) 'make ml-coordinate-search ASSET=$(ASSET)'

# the canon's crawler and its text-based user interface (TUI), on the host: python3 and gum, git only for the root, the
# paths an add offers and the commit a report entry names, the canon having no runner and no dependency — it gates
# nothing, and no target of the chain depends on it
skills-crawl:    ## the crawler's TUI: the listed paths and the skill matrix, then one action — crawl chosen listed files with a vendor, model, effort and permissions chosen in turn, after the plan; add a path with its skills; mark a path's skills; or remove a path — then it closes; run it in a terminal
	python3 -B -m module_skills.sub_module_scalability_crawler.crawl
skills-status:   ## skills_status.json -> store/status: every listed file with the date of its last report
	python3 -B -m module_skills.sub_module_scalability_crawler.status

# the presentation switch — the one switch pair the target grammar admits (AGENTS.md § Canonical vocabulary): two words to
# type in front of an audience; the rest is a click in the page
on: build        ## the presentation switch: the dashboard and the DevOps panel up, the page's address printed and opened
	$(COMPOSE) up -d dashboard devops
	@python3 -c "import webbrowser; url = 'http://127.0.0.1:$(PORT)/'; print('dashboard at', url); webbrowser.open(url)"
off:             ## the presentation switch: stop and remove every container of this project
	$(COMPOSE) down
btc-all: all     ## the single-asset chain by its ticker name; the alias goes when the basket grows
# the stages of all, one make target each, measured from outside by record.py: the four pipeline stores before and after
RECORDED_STAGES := data-download data-ingest data-status features-bars features-catalogue features-status ml-labels ml-hpo ml-train ml-strategy ml-status
all-record: build ## one recorded run of the whole chain, every stage measured from outside by record.py -> store/run_records/<run_id>/<stage>.json
	@run_id=$(RUN_ID); for stage in $(RECORDED_STAGES); do RUN_ID=$$run_id python3 record.py $$stage $(MAKE) $$stage || exit $$?; done
btc-lifecycle: all-record ## the recorded lifecycle by its ticker name; the alias goes when the basket grows
