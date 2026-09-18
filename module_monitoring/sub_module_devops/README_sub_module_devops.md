# DevOps panel

The engine's views over the one docker socket: every container the daemon reports, this project's first; the
networks, the volumes and the bind mounts; the image this container runs; a bounded tail of the daemon's events —
and the three verbs, start, stop and restart, offered for this project's containers alone. Its rules are
`skill_devops_panel.md`, beside this file; the topology it is one service of is
`../skill_asset_containers.md` § The topology.

```bash
make monitoring-devops    # the panel's server alone, on the host, over /var/run/docker.sock — it publishes nothing a reader reaches but through the dashboard's proxy
```

At the workspace the panel is the `devops` resident of `make on` — the one container that holds the socket, its API
proxied by the dashboard under `/devops/*`. Its page is a static file below the dashboard's web root, opened by the
**DevOps** control of the status page; only its API is a route.

| the file | what it is |
|---|---|
| `serve.py` | the panel's own server, the one process that speaks the Docker Engine API: the five inventories, the one action and its guard, `PanelHandler` and `main()` |
| `config.py` | every Engine API path under the pinned `v1.44`, the socket path, the action allowlist and the event-tail bounds — the only place this sub-module builds a path |
| `index.html` | the panel's page: the five tables, the image box and the jump back to the status page; it loads `../page.js` before its own script |
| `devops.js` | the panel's script: the five fetches of `/devops/api/*`, the CPU rate from two polls, the action buttons and the poll that runs only while the page is visible |
| `devops.css` | only what `../style.css` does not carry: the wider panel body and the disabled action button |
