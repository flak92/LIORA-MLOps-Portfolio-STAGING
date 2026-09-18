"""The DevOps panel's own server: the one process that speaks the Docker Engine API.

    GET  /api/machines                 every container on the host, this project's marked as its own
    GET  /api/networks                 the networks, with what is attached to each
    GET  /api/volumes                  named volumes with their sizes, and the bind mounts in use
    GET  /api/image                    the image this container runs, named by the container itself
    GET  /api/events                   a bounded tail of the daemon's events
    POST /api/machines/<id>/<action>   start / stop / restart — this project's containers only

The socket lives in this container and in no other. The dashboard reaches these routes by
service name over the compose network and holds no socket of its own.
"""

from __future__ import annotations

import http.client
import json
import socket
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from module_monitoring import config as monitoring_config
from module_monitoring.serve import to_json_bytes, write_response

from . import config


class EngineUnavailable(Exception):
    """The daemon did not answer at all — distinct from an answer that was not 200.

    A view that cannot reach the Engine has nothing to report, and reporting nothing is not the same
    as reporting an empty host: the panel owes the reader dashes, never a number it did not measure.
    """


class EngineConnection(http.client.HTTPConnection):
    """The Engine API over its unix socket: http.client, with the one connection it opens swapped for AF_UNIX."""

    def __init__(self, socket_path: str, timeout: float):
        super().__init__(config.ENGINE_HOST_HEADER, timeout=timeout)
        self.socket_path = socket_path

    def connect(self):
        engine = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        engine.settimeout(self.timeout)
        engine.connect(self.socket_path)
        self.sock = engine


def fetch_engine(method: str, path: str) -> tuple[int, bytes]:
    """One Engine exchange as (status code, body): the answer as it came, 503 with no body when the daemon does not answer."""
    connection = EngineConnection(config.DOCKER_SOCKET_PATH, config.ENGINE_EXCHANGE_TIMEOUT_SECONDS)
    try:
        connection.request(method, path, headers={"Host": config.ENGINE_HOST_HEADER})
        answer = connection.getresponse()
        return answer.status, answer.read()
    except (OSError, http.client.HTTPException):
        return HTTPStatus.SERVICE_UNAVAILABLE, b""
    finally:
        connection.close()


def engine_object(path: str):
    """One Engine GET decoded: None when the daemon answered something other than 200, so a view renders
    what answered and dashes the rest — and EngineUnavailable when it did not answer at all."""
    status, body = fetch_engine("GET", path)
    if status == HTTPStatus.SERVICE_UNAVAILABLE:
        raise EngineUnavailable(path)
    if status != HTTPStatus.OK or not body:
        return None
    return json.loads(body)


def engine_events(path: str) -> list:
    """The event stream is newline-delimited JSON; a bounded window terminates it."""
    status, body = fetch_engine("GET", path)
    if status == HTTPStatus.SERVICE_UNAVAILABLE:
        raise EngineUnavailable(path)
    if status != HTTPStatus.OK or not body:
        return []
    return [json.loads(line) for line in body.splitlines() if line.strip()]


def own_project(hostname: str) -> str | None:
    """The compose project this container belongs to, read from its own labels — never a literal.

    The host may run a sibling project whose services carry the same names, so the guard
    compares the label and nothing else.
    """
    own = engine_object(config.container_path(hostname))
    return ((own or {}).get("Config") or {}).get("Labels", {}).get(config.COMPOSE_PROJECT_LABEL)


def own_image(hostname: str) -> str | None:
    own = engine_object(config.container_path(hostname))
    return ((own or {}).get("Config") or {}).get("Image")


def port_texts(container: dict) -> list:
    """A published port as the host sees it; an unpublished one is the container's own."""
    texts = []
    for port in container.get("Ports") or []:
        private = f"{port.get('PrivatePort')}/{port.get('Type')}"
        texts.append(f"{port.get('IP')}:{port['PublicPort']}->{private}" if port.get("PublicPort") else private)
    return sorted(set(texts))


def machine_row(container: dict, project: str | None) -> dict:
    """One container as the panel shows it: its identity and state from the list, its footprint from one stats sample."""
    labels = container.get("Labels") or {}
    inspected = engine_object(config.container_path(container["Id"])) or {}
    state = inspected.get("State") or {}
    sample = engine_object(config.container_stats_path(container["Id"])) or {}
    memory = sample.get("memory_stats") or {}
    cpu = (sample.get("cpu_stats") or {}).get("cpu_usage") or {}
    total_usage = cpu.get("total_usage")
    return {
        "container_id": container["Id"][:12],
        "name": (container.get("Names") or ["/"])[0].lstrip("/"),
        "compose_project": labels.get(config.COMPOSE_PROJECT_LABEL),
        "compose_service": labels.get(config.COMPOSE_SERVICE_LABEL),
        "own_project": bool(project) and labels.get(config.COMPOSE_PROJECT_LABEL) == project,
        "state": container.get("State"),
        "image": container.get("Image"),
        "started_at_utc": state.get("StartedAt"),
        "restart_count": inspected.get("RestartCount"),
        "ports": port_texts(container),
        "memory_bytes": memory.get("usage"),
        "memory_limit_bytes": memory.get("limit"),
        "cpu_usage_seconds": None if total_usage is None else round(total_usage / config.NANOSECONDS_PER_SECOND, 3),
        "cpu_count": (sample.get("cpu_stats") or {}).get("online_cpus"),
    }


def machines_payload(project: str | None) -> dict:
    containers = engine_object(config.containers_path()) or []
    rows = [machine_row(container, project) for container in containers]
    return {
        "generated_at_utc": monitoring_config.to_utc_text(datetime.now(tz=UTC)),
        "poll_interval_seconds": monitoring_config.CONTAINER_POLL_INTERVAL_SECONDS,
        "compose_project": project,
        "actions": list(config.CONTAINER_ACTIONS),
        "machines": sorted(rows, key=lambda row: (not row["own_project"], row["name"])),
    }


def networks_payload(project: str | None) -> dict:
    networks = engine_object(config.networks_path()) or []
    rows = []
    for network in networks:
        inspected = engine_object(config.network_path(network["Id"])) or {}
        attached = inspected.get("Containers") or {}
        rows.append({
            "name": network.get("Name"),
            "driver": network.get("Driver"),
            "scope": network.get("Scope"),
            "compose_project": (network.get("Labels") or {}).get(config.COMPOSE_PROJECT_LABEL),
            "own_project": bool(project) and (network.get("Labels") or {}).get(config.COMPOSE_PROJECT_LABEL) == project,
            "attached": sorted(entry.get("Name", "") for entry in attached.values()),
        })
    return {"generated_at_utc": monitoring_config.to_utc_text(datetime.now(tz=UTC)),
            "networks": sorted(rows, key=lambda row: (not row["own_project"], row["name"] or ""))}


def volumes_payload(project: str | None) -> dict:
    """Named volumes with the sizes only /system/df reports, and the bind mounts the containers actually carry."""
    disk = engine_object(config.system_df_path()) or {}
    volumes = [{
        "name": volume.get("Name"),
        "driver": volume.get("Driver"),
        "compose_project": (volume.get("Labels") or {}).get(config.COMPOSE_PROJECT_LABEL),
        "own_project": bool(project) and (volume.get("Labels") or {}).get(config.COMPOSE_PROJECT_LABEL) == project,
        "size_bytes": (volume.get("UsageData") or {}).get("Size"),
        "reference_count": (volume.get("UsageData") or {}).get("RefCount"),
    } for volume in (disk.get("Volumes") or [])]

    mounts = {}
    for container in engine_object(config.containers_path()) or []:
        labels = container.get("Labels") or {}
        if not project or labels.get(config.COMPOSE_PROJECT_LABEL) != project:
            continue
        name = (container.get("Names") or ["/"])[0].lstrip("/")
        for mount in container.get("Mounts") or []:
            if mount.get("Type") != "bind":
                continue
            key = (mount.get("Source"), mount.get("Destination"), bool(mount.get("RW")))
            mounts.setdefault(key, []).append(name)
    binds = [{"source": source, "destination": destination, "writable": writable, "containers": sorted(names)}
             for (source, destination, writable), names in sorted(mounts.items())]

    return {"generated_at_utc": monitoring_config.to_utc_text(datetime.now(tz=UTC)),
            "volumes": sorted(volumes, key=lambda row: (not row["own_project"], row["name"] or "")),
            "bind_mounts": binds}


def image_payload(hostname: str) -> dict:
    """The image this container runs, named by the container itself — its own `Config.Image` — and never by a literal."""
    image = own_image(hostname)
    inspected = engine_object(config.image_path(image)) if image else None
    return {
        "generated_at_utc": monitoring_config.to_utc_text(datetime.now(tz=UTC)),
        "image": image,
        "image_id": (inspected or {}).get("Id", "").removeprefix("sha256:")[:12] or None,
        "size_bytes": (inspected or {}).get("Size"),
        "created_utc": (inspected or {}).get("Created"),
        "repo_tags": (inspected or {}).get("RepoTags") or [],
    }


def events_payload(project: str | None) -> dict:
    """A bounded tail: the window is a duration, the answer is this project's newest events of it, nothing is persisted."""
    now = datetime.now(tz=UTC)
    since = now - timedelta(minutes=config.EVENT_TAIL_MINUTES)
    events = (engine_events(config.events_path(int(since.timestamp()), int(now.timestamp()), project))
              if project else [])
    rows = [{
        "time_utc": monitoring_config.to_utc_text(datetime.fromtimestamp(event.get("time", 0), tz=UTC)),
        "type": event.get("Type"),
        "action": event.get("Action"),
        "name": (event.get("Actor") or {}).get("Attributes", {}).get("name"),
        "compose_service": (event.get("Actor") or {}).get("Attributes", {}).get(config.COMPOSE_SERVICE_LABEL),
    } for event in events]
    return {"generated_at_utc": monitoring_config.to_utc_text(now),
            "compose_project": project,
            "events": rows[-config.EVENT_TAIL_LIMIT:][::-1]}


def act_on_machine(container_id: str, action: str, project: str | None) -> tuple[int, bytes]:
    """The allowlist, and the one guard that closes it: a container of another project is refused with its reason."""
    if action not in config.CONTAINER_ACTIONS:
        return HTTPStatus.NOT_FOUND, b""
    inspected = engine_object(config.container_path(container_id))
    if inspected is None:
        return HTTPStatus.NOT_FOUND, b""
    target = ((inspected.get("Config") or {}).get("Labels") or {}).get(config.COMPOSE_PROJECT_LABEL)
    if not project or target != project:
        return HTTPStatus.FORBIDDEN, to_json_bytes({
            "action": action,
            "refused": True,
            "compose_project": target,
            "reason": f"{action} is offered for this project's own containers; "
                      f"this one belongs to {target or 'no compose project'}",
        })
    # the engine's answer as it came: a 304 cannot carry a body, and the page reads the status
    return fetch_engine("POST", config.container_action_path(container_id, action))


class PanelHandler(BaseHTTPRequestHandler):
    """The panel's API. The page itself is static and served by the dashboard, so no route answers with HTML."""

    def do_GET(self):
        route = self.path.split("?")[0]
        segments = route.split("/")
        project = self.server.project
        try:
            if segments[:3] == ["", "api", "machines"] and len(segments) == 3:
                write_response(self, HTTPStatus.OK, to_json_bytes(machines_payload(project)))
            elif route == "/api/networks":
                write_response(self, HTTPStatus.OK, to_json_bytes(networks_payload(project)))
            elif route == "/api/volumes":
                write_response(self, HTTPStatus.OK, to_json_bytes(volumes_payload(project)))
            elif route == "/api/image":
                write_response(self, HTTPStatus.OK, to_json_bytes(image_payload(self.server.hostname)))
            elif route == "/api/events":
                if not self.server.project_known:
                    raise EngineUnavailable("/api/events")   # an empty tail would read as a quiet project
                write_response(self, HTTPStatus.OK, to_json_bytes(events_payload(project)))
            else:
                write_response(self, HTTPStatus.NOT_FOUND)
        except EngineUnavailable:
            write_response(self, HTTPStatus.SERVICE_UNAVAILABLE)

    def do_POST(self):
        segments = self.path.split("?")[0].split("/")
        try:
            if len(segments) == 5 and segments[:3] == ["", "api", "machines"]:
                write_response(self, *act_on_machine(segments[3], segments[4], self.server.project))
            else:
                write_response(self, HTTPStatus.NOT_FOUND)
        except EngineUnavailable:
            write_response(self, HTTPStatus.SERVICE_UNAVAILABLE)


class PanelServer(ThreadingHTTPServer):
    """The panel's server; its project is read once from its own container, because it cannot change while it runs."""

    def __init__(self):
        super().__init__((monitoring_config.BIND_ADDRESS, monitoring_config.CONTAINER_PORT), PanelHandler)
        self.hostname = socket.gethostname()
        try:
            self.project = own_project(self.hostname)
            self.project_known = True
        except EngineUnavailable:
            # a daemon silent at boot leaves the panel read-only, which is the guard's own default; the
            # flag keeps that apart from a panel the daemon answered about but that carries no project
            self.project = None
            self.project_known = False


def main() -> int:
    server = PanelServer()
    print(f"devops panel of {server.project or 'no compose project'} "
          f"at http://{monitoring_config.BIND_ADDRESS}:{monitoring_config.CONTAINER_PORT}/api/", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
