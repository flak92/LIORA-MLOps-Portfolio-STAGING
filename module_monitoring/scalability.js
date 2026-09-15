/* Scalability tab: how current the crawler's reports are — /store_status/skills_status.json, every file to_crawl.md
   lists with the count and the last date of its report's entries. Classic script over the page.js toolkit; the page
   computes nothing but a file's age, the last crawl against the browser's clock. */
"use strict";

let SKILLS_STATUS = null;
const SECONDS_PER_DAY = 86400;

function formatAgeDays(utcText) {
  const seconds = (Date.now() - millisecondsSinceEpoch(utcText)) / MILLISECONDS_PER_SECOND;
  return formatNumber(seconds / SECONDS_PER_DAY, 1);
}

function renderCrawlActuality(host, status) {
  const frame = buildFrame("CRAWL ACTUALITY — every file to_crawl.md lists, and its last report");
  frame.body.appendChild(buildTable(
    ["file", "last crawl (UTC)", "age (days)", "crawls", "report"],
    status.files.map((file) => [
      file.path,
      file.last_crawled_utc === null ? "never" : file.last_crawled_utc,
      file.last_crawled_utc === null ? "never" : formatAgeDays(file.last_crawled_utc),
      formatCount(file.crawl_count),
      file.report,
    ])));
  host.appendChild(frame.frame);
}

function initScalability() {
  const meta = document.getElementById("scalability-meta");
  fetch("/store_status/skills_status.json", { cache: "no-store" })
    .then((response) => { if (!response.ok) throw new Error("HTTP " + response.status); return response.json(); })
    .then((status) => {
      SKILLS_STATUS = status;
      renderCrawlActuality(document.getElementById("scalability-detail"), status);
      meta.hidden = true;
    })
    .catch((error) => {
      meta.textContent = "could not fetch skills_status.json (" + error.message + ") — run `make skills-status`";
      meta.className = "box err";
    });
}

initScalability();
