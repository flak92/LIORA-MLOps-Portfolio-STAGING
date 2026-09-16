# Scalability crawler

Reads each file a hand lists against the skills a hand marks for it and appends each agent's answer to
the file's report. Its rules are `../skill_scalability_crawler.md`, and the standards of its screens
`../skill_tui_designer.md`, which every TUI of this tree obeys.

```bash
make skills-crawl     # the TUI: the listed paths and the skill matrix, then crawl (vendor, model, effort, permissions, files, the plan), add a path with its skills, mark skills or remove a path
make skills-status    # store/status/skills_status.json again, after to_crawl.md was edited by hand
STORE_STATUS_DIR=store/status python3 -B -m module_skills.sub_module_scalability_crawler.crawl -h   # the TUI's keys, plain output and exit codes
```

Kept by hand: `to_crawl.md`, the skill matrix — the paths to crawl and, marked `X`, the skills each is
read against; `crawlers_mission.md`, what the agent reports; and `vendors_for_crawling.toml`, the
vendors and their forms.

## The loop

A rule is written through `../skill_self_explaining_naming.md` § Minting a new convention: a pattern
the reports show a third time is minted or declined in one commit with its register row, and the same
file is crawled again. A file is read against `AGENTS.md`, the register, the orientation of its own
module and the skills its row of `to_crawl.md` marks, so a skill acts on a file's crawl by its mark,
not by the module it sits in; a skill a report names under *Skills to mark* is marked, or left
unmarked, by a hand. The queue is the order of `to_crawl.md`'s rows. An unexplained finding is the
missing sentence, proposed for the owner of the file to accept.
