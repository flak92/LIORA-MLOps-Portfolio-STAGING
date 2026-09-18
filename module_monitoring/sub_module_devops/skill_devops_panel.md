# Skill: the DevOps panel — the machines, and the one socket

Two personas, two entries. The status page carries the results the business
persona wants; the **DevOps** control opens this panel — the containers, networks and
volumes the project actually runs on. *The repository shows the destination, not the road*:
the panel shows what the daemon reports and offers three verbs, and nothing else.

The panel is `module_monitoring/sub_module_devops/`. Its page is a static
file the dashboard already serves; only its API is a route.

## Why a sub-module, and why that name

The panel is named for the persona whose page it is: the **DevOps** control
opens `sub_module_devops/`, and the route the dashboard proxies for it is `/devops/*` —
one word for the control, the route, the compose service `devops` and the
directory. Retired: `portraefik`, the owner's coinage of two tool brands this
repository does not use — a name that needed a lookup before it said anything.
Rejected beside it: `sub_module_docker` (the register bans `module_docker` as a
stem), a tool's brand as a name, and any routing the old name suggested —
nothing of Portainer or Traefik is inside: no reverse proxy, no third-party
management UI.

It is nested rather than promoted because the dashboard serves its own
directory, so the panel's page needs no route; the grammar it answers to is the
sub-module row of `AGENTS.md` § Canonical vocabulary, and the three that minted it
are named in `AGENTS.md` § The default choice.

## The one socket, and what containment means

`/var/run/docker.sock` is mounted in `devops` and in no other container.
The dashboard holds no socket and makes no Engine call: it proxies `/devops/*`
to `devops` by service name over the compose network. The scoped
repeal of the socket rule lives with the topology it changes,
`module_skills/skill_asset_containers.md`.

The containment is of the **mount**, not of the **reach**. Any client that can
reach the dashboard's loopback origin can reach the Engine through the proxy —
including a page on another site, because a simple cross-origin `POST` needs no
preflight. There is no auth, no token and no origin check. Stated, not
mitigated.

`devops` runs as the host user like every other service and takes the host's
docker group through `group_add`, so it reads the socket without being root; the
Makefile measures that group the way it measures `UID` and `GID`.

**The seat.** On the one Linux container instance (Amazon ECS on Amazon EC2)
`devops` keeps the same socket, because the service that runs the tasks starts
them through the host's own daemon; a task is a foreign container in the
**containers on this host** table; § The guard refuses it the three verbs as any
other project's. The provider's console and container metrics are absent here —
described. `module_skills/skill_pre_aws_solution.md` § The mapping table.

## The API

The Engine is addressed at a pinned version, `v1.44` — the daemon's own declared
minimum, so upgrading the engine does not move the contract underneath the panel.

| route | answers |
|---|---|
| `GET /devops/api/machines` | every container the daemon reports, this project's first and marked `own_project`; state, uptime, image, ports, restarts, and one stats sample |
| `GET /devops/api/networks` | the networks, their driver and scope, and what is attached to each |
| `GET /devops/api/volumes` | named volumes with the sizes only `/system/df` reports, and the bind mounts this project's containers carry |
| `GET /devops/api/image` | the image this container runs — named by the panel's own container, never by a literal |
| `GET /devops/api/events` | this project's own daemon events over a bounded window, newest first |
| `POST /devops/api/machines/<id>/<action>` | `start`, `stop`, `restart` — the whole allowlist |

A daemon that does not answer is answered for: every route above returns
**503 with no body**, and so does the dashboard's proxy when `devops` itself does
not — it cannot connect, the name does not resolve, or the exchange fails after the
request is sent — with `Cache-Control: no-store`. A stopped `devops` is answered for
once Docker's resolver gives up on the vanished name, not at the socket timeout —
stated, not mitigated. The page decides on the status alone and clears the
views it can no longer vouch for, so an unreachable Engine is never rendered as
an empty host. Having reached no cadence to poll on, it retries once the tab is
next looked at.

Three bounds on the event tail are deliberate: a window in minutes, because an
unbounded `/events` grows with the daemon's uptime rather than with the question;
a count cap, because the page holds the tail and nothing persists it — this is
the bound that actually drops an event a reader asked for; and a project label
filter, because a host's other stacks bury this project's events under their
health checks.

## The guard

An action is offered for a container of **this compose project** and refused for
every other, with the reason in the body:

```
403  {"action": "stop", "refused": true, "compose_project": "<theirs>",
      "reason": "stop is offered for this project's own containers; this one belongs to <theirs>"}
```

The project is read from the panel's own container labels at start, never
written as a literal: a host may run a sibling project whose services carry the
same names — `dashboard`, `devops` — and only the `com.docker.compose.project`
label separates them, and the read happens once — a daemon silent at that moment
leaves the panel read-only for the life of the process and `/api/events`
answering 503 rather than an empty tail, because an empty tail would read as a
quiet project. An action outside the allowlist and a container the daemon does
not know are both `404`.

A third answer is neither acceptance nor refusal: the engine returns `304` when
the container already holds the state the action asks for. It carries no body —
a 304 cannot — so the page reads the status and says the action changed nothing.
`refused` belongs to the 403 above and to nothing else.

Not offered, each needing its own decision: `rm`, `exec`, `prune`, image
operations, compose up/down from the browser, log streaming.

## The views

The **containers on this host** table reads the Engine's own accounting for every
container the daemon reports, foreign ones included — the one measurement of a
container's memory and CPU. Five more sections sit below it — **networks**, **volumes**, **bind
mounts**, **image** and **events** — each a flat table of what its route
answered — **image** a key-value box, the one row its route answers with — with no arithmetic of the page's own. Their keys are registered in
`module_skills/glossary.md` § DevOps panel and are not restated here.

## What the panel owes the reader

The engine reports counters, not
rates: a CPU rate is this page's arithmetic over two polls, a dash until the
second, and a counter that went backwards is a container that restarted rather
than a negative rate. An action never renders optimistically — the panel re-reads
every view and shows the state the engine now reports. One action at a time, and
the buttons of a foreign container are disabled before the server ever has to
refuse them.

The panel polls only while it is visible, at the interval the server publishes;
no cadence is a literal in the page.
