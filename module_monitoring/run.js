/* Lifecycle tab: one recorded run read from /runs and /runs/<run_id> — the run header, the stage table
   and what each stage wrote to the four pipeline stores. Classic script; uses the shared toolkit from page.js,
   buildTable among them. The page collects nothing: every number below was measured from outside the stage
   by record.py — when it started, how it exited, what it added, changed and removed. */
"use strict";

function formatSeconds(seconds) {
  if (seconds === null || seconds === undefined) return "-";
  if (seconds < SECONDS_PER_MINUTE) return seconds.toFixed(1) + "s";
  return Math.floor(seconds / SECONDS_PER_MINUTE) + "m " + Math.round(seconds % SECONDS_PER_MINUTE) + "s";
}

/* what a stage wrote: the bytes of every file it added or changed */
function bytesWritten(stage) {
  return stage.store_diff.added.concat(stage.store_diff.changed)
    .reduce((total, entry) => total + entry.size_bytes, 0);
}

function buildRunHeader(record) {
  const stages = record.stages;
  const first = stages[0];
  const last = stages[stages.length - 1];
  const failed = stages.filter((stage) => stage.exit_code !== 0);
  const wallSeconds = (millisecondsSinceEpoch(last.ended_at_utc) - millisecondsSinceEpoch(first.started_at_utc))
    / MILLISECONDS_PER_SECOND;
  const stageSeconds = stages.reduce((total, stage) => total + stage.duration_seconds, 0);
  return buildKeyValueBox([
    ["run", record.run_id],
    ["start / end", first.started_at_utc + "  ->  " + last.ended_at_utc + " UTC"],
    ["total time", formatSeconds(wallSeconds) + "  (stages " + formatSeconds(stageSeconds) + ")"],
    ["stages", stages.length + (failed.length
      ? "  ·  failed at " + failed.map((stage) => stage.stage).join(", ")
      : "  ·  every exit code 0")],
    ["written", formatBytes(stages.reduce((total, stage) => total + bytesWritten(stage), 0)) + " across the four pipeline stores"],
  ]);
}

function renderRunStages(body, stages) {
  body.appendChild(buildTable(
    ["stage", "start", "time", "exit", "added", "changed", "removed", "bytes written"],
    stages.map((stage) => [
      stage.stage, stage.started_at_utc, formatSeconds(stage.duration_seconds),
      [stage.exit_code, stage.exit_code !== 0],
      formatCount(stage.store_diff.added.length), formatCount(stage.store_diff.changed.length),
      formatCount(stage.store_diff.removed.length), formatBytes(bytesWritten(stage)),
    ])));
}

/* every file a stage touched, by store: the record of what the run left behind */
function renderRunStores(body, stages) {
  const rows = [];
  stages.forEach((stage) => {
    ["added", "changed", "removed"].forEach((state) => {
      stage.store_diff[state].forEach((entry) => {
        rows.push([stage.stage, entry.store, entry.path, state,
                   state === "removed" ? "-" : formatBytes(entry.size_bytes)]);
      });
    });
  });
  if (!rows.length) {
    body.appendChild(buildFootnote("no stage of this run wrote a file."));
    return;
  }
  body.appendChild(buildTable(["stage", "store", "path", "state", "size"], rows));
}

function renderRun(record) {
  const host = document.getElementById("run-detail");
  host.textContent = "";
  if (!record.stages.length) {
    host.appendChild(buildFootnote("run " + record.run_id + " recorded no stage."));
    return;
  }
  const header = buildFrame("RUN — " + record.run_id);
  header.body.appendChild(buildRunHeader(record));
  const stages = buildFrame("STAGES — what ran, how long, how it ended, what it wrote");
  renderRunStages(stages.body, record.stages);
  const stores = buildFrame("STORES — every file a stage added, changed or removed in the pipeline stores");
  renderRunStores(stores.body, record.stages);
  [header, stages, stores].forEach((frame) => host.appendChild(frame.frame));
}

function fetchRunRecord(runId) {
  return fetch("/runs/" + runId, { cache: "no-store" })
    .then((response) => { if (!response.ok) throw new Error("HTTP " + response.status); return response.json(); });
}

function initRun() {
  const meta = document.getElementById("run-meta");
  fetch("/runs", { cache: "no-store" })
    .then((response) => { if (!response.ok) throw new Error("HTTP " + response.status); return response.json(); })
    .then((runs) => {
      if (!runs.run_ids.length) {
        meta.textContent = "no recorded run yet — run `make all-record`";
        return;
      }
      meta.textContent = runs.run_ids.length + " recorded run(s) · newest " + runs.run_ids[0];
      return fetchRunRecord(runs.run_ids[0]).then((record) => {
        meta.textContent = runs.run_ids.length + " recorded run(s) · showing " + record.run_id
          + " · " + record.stages.length + " stages";
        renderRun(record);
      });
    })
    .catch((error) => {
      meta.textContent = "could not load /runs (" + error.message + ") — run `make on`";
      meta.className = "box err";
    });
}

initRun();
