# Skill: asset containers — the topology and the socket

The asset is the primary object; its container is how a stage is run for it
locally, and the engine is the support layer. One image, built from the root `Dockerfile`;
three runners — `data`, `features`, `ml`, one per module of the chain, a role and a one-off
each — and two residents, `dashboard` and `devops`; every service written out in `docker-compose.yml` under two anchors: `x-store-environment` carries
the store contract every service reads — the five `STORE_*_DIR` — and beside it the thread cap; `x-service` is what
every service is — the `build`, the `image`, `init`, `user`, that environment and the tree mount `.:/app` — each service
respelling its `volumes:` whole, the tree mount and the stores it touches, because a service's key replaces the anchor's; a
resident adds its own `command:`, and a runner carries none. The project is named `liora` in the file, so a
container is `liora-<service>-1` on every host.
*The repository shows the destination, not the road*: no restart policy, no healthcheck.

**The socket rule, and its one scope.** Managing containers, networks and
volumes needs the Docker Engine API, and the honest way to it is the socket, so
the rule that forbade it is not bent but scoped: `/var/run/docker.sock` is
mounted in **exactly one container, `devops`**, whose single responsibility
is docker management and monitoring. It is never mounted in the dashboard, and never
in an asset container. No third-party socket proxy — that
is a dependency — and no TCP daemon endpoint, which is weaker than the socket.
What that contains is the **mount**: root-equivalent access lives in one service
that publishes no port. What it does not contain is **reach** — the dashboard
proxies `/devops/*` to it, so anything that can reach the dashboard's loopback
origin can reach the Engine through it, a browser tab on another site included.
Stated, not mitigated. The panel's own contract is
`module_monitoring/sub_module_devops/skill_devops_panel.md`.

## The topology

| service | what it is | role | lifetime |
|---|---|---|---|
| `data`, `features`, `ml` — one runner per module of the chain | the `x-service` anchor with its `volumes:` respelled: the tree at `/app` and the stores its stages touch — `data` the raw tree, the artifacts and the status store, `features` the artifacts and the status store, `ml` those two and the trials store it alone writes — no `command:`, so `run --rm -T` supplies one; `ml` alone adds the `5g` ceiling | every stage of its module: a per-asset stage as one one-off container per asset through the `fanout` macro, a basket-wide stage once through `basket`, the one-asset promotion a hand starts with `ASSET=`; a download stays one process per venue because a venue's per-IP limit is budgeted per process | one-off |
| `dashboard` | the `x-service` anchor, plus its own `command: python -m module_monitoring.serve`, `ports:` and, beside the tree at `/app`, two read-only mounts — the run records and the status store it reads | the status page's server, published on `127.0.0.1:${PORT}` only | resident |
| `devops` | the `x-service` anchor, plus its own `command:`, `group_add:` and, beside the tree at `/app`, the socket — no store | the DevOps panel's server: the one container that holds the docker socket | resident |

`init: true` on every service: a Python process as PID 1 has no SIGTERM
handler, so `docker compose down` would wait out the stop timeout and kill a
stage mid-write, and a one-off's PID 1 reaps whatever its stage leaves behind.
`5g` sits above DuckDB's `4GB` ceiling and bounds a runaway allocation
outside DuckDB; the `ml` runner alone carries it, the one task — HPO and
XGBoost — that allocates above that ceiling; `data` and `features` open a database
under its own `memory_limit` and allocate nothing outside it, and the residents
compute nothing. `build: .` and `image:` sit on the `x-service` anchor, so every service names the one
image and a bare clone builds it instead of reaching for a registry; `docker images` shows one, and the
`Dockerfile` installs the pins of `requirements.txt` onto `python:3.12-slim` and copies no code — the code
arrives through `.:/app`, the state through the `/store/<content>` mounts beside it.
Concurrency is bounded by `JOBS`. One mechanism only — no
`mem_limit` beside it, no reservation, no CPU quota, and no restart policy,
because a failure is reported, not hidden. Each service mounts the stores it
touches and no more, read-only where it only reads, beside the tree itself at `/app`: the code, the
stores and, in `devops` alone, the docker socket are what a container reaches on the host. The
five `STORE_*_DIR` stay on the anchor for every service — the variable is the name a service speaks,
the mount the I/O it is granted — which is why `devops` carries the five names and no store, and takes
the host's docker group through `group_add` so it reads the socket without being root. The raw store
is `data`'s alone, central and Lean-exact; the dashboard reads its stores and writes
none, so its store mounts are `:ro`. The store contract is the env-named path: a container addresses state only at its `/store/<content>` mounts,
never through the `/app/store/<content>` the tree mount also carries (`skill_pre_aws_solution.md` § Docker is compute,
not storage). Every process binds
`0.0.0.0` on the internal port 8900 — `CONTAINER_PORT` in `module_monitoring/config.py`, with no
argument: the server is docker-only. `PORT` is only the host side of the
dashboard's mapping, measured at invocation, never hardcoded — the Makefile asks
for the port the dashboard already publishes, else the first free port from 8900
upward, because another project on the same host — or a checkout of LIORA run
under `COMPOSE_PROJECT_NAME=` — may hold 8900
(`skill_pre_aws_solution.md` § What stays as it is, and why, the row on compose
names); `PORT=n` overrides it, `make on` prints the address, and no document
states the host port as a number. The measurement is a look, not a lock: a port
taken between the look and the bind fails the start, and the next `make on`
looks again — stated, not mitigated. A stage run with another `PORT` never
recreates a resident, and a checkout without the rule keeps assuming 8900 and
fails its own start the day this one holds it. Every container runs as the host user — `user: ${UID:-1000}:${GID:-1000}`,
fed by the Makefile's `COMPOSE_ENV` — so nothing it writes is root-owned.

`make on` builds the image if needed, starts the two residents, and
opens the page; `make off` takes everything down. `make all` runs the whole chain,
download to snapshots, every stage in a one-off container of its module's runner:
the `fanout` macro is `docker compose run --rm -T <runner> python -m
module_<x>.<stage> --tickers <TICKER>` once per asset, the asset's container — ingest one container at a
time, the ML stages `JOBS` at a time — and `basket` the same once for the whole
basket. No resident is assumed for compute: a resident only serves, the panel
measures the one-off doing the work while it runs, and `record.py` measures a
stage from outside and knows no container. The direction is
`skill_pre_aws_solution.md`. `ASSET` narrows the make line and no container reads
it — the fan-out passes `--tickers <TICKER>` from `TICKER_LIST`; `build_ticker_parser` has no default — every launcher names
the assets. The `COMPOSE` macro never gains `-f` or `COMPOSE_FILE`: one
compose file, every service visible in it. Adding an asset is one entry in
`TICKERS` and nothing else (the whole recipe,
the ticker's precondition included: `README.md` § Extending).

**The seat.** The `x-service` anchor is one task definition parameterised by `--tickers`,
each resident a service of the container runtime kept running on the one Linux container
instance (Amazon ECS on Amazon EC2): the
`fanout` macro's `run --rm` already a task run per stage per asset — nothing left to
edit — the store mounts the volume, the one image the task's image, the `ml` runner's
`5g` the task's memory, `init` and `user` the task definition's own keys. `skill_pre_aws_solution.md` § The mapping table and
§ The retrain runtime is a ladder.
