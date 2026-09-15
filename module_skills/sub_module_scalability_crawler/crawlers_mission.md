# Crawler's mission

You are reviewing one file of this repository against its written rules. This message carries, in
this order: this mission; `# Rules`, the documents sent with every file — the contract, the name
register and, for a file of a module, that module's orientation; `# Skills marked for this file`,
the skills a hand marked for this file in the crawler's skill matrix,
`module_skills/sub_module_scalability_crawler/to_crawl.md`, each under its path; `# Skills not
marked for this file`, every other skill of the tree, by its path alone; then the file, under its
own path, every line after its number. Everything you need is in this message — read nothing
else. A placement argued in a document this message does not carry is no departure: report it as
unexplained.

A marked skill binds the file as the rules do. An unmarked skill binds nothing in this review: its
text is not sent, so never cite it as a departure, never quote it, and never infer what it says
beyond its path. When the file looks governed by an unmarked skill — its path names the file's
module or a subject the file handles, or a sent document points to it — name it in section 4.

Report, in this order, with `none` under an empty section:

1. **Departures.** One line per rule the file departs from, a rule of a document under `# Rules` or
   `# Skills marked for this file`: `<rule path> § <section>`; the rule's deciding clause, quoted
   verbatim; every line of the file it touches, by the numbers in this message; the current form,
   quoted verbatim from those lines; the form the rule derives.
2. **Unexplained.** One line per item a reader cannot decode from the file and the sent documents
   alone: its line numbers, and the missing sentence, written out — a docstring, a comment or a
   `§ Design rationale` row — that would explain it. A pattern no sent document governs belongs
   here when it is seen exactly twice, or when it misses one of the conditions of section 3.
3. **Proposed conventions.** A pattern seen three times or more that no sent document governs, one
   block per pattern: the pattern and every occurrence by line number, then the seven conditions of
   `module_skills/skill_self_explaining_naming.md` § Minting a new convention, one field each —
   closed list, derivable, normative source, able to fail (the form it forbids), scope, boundary,
   migration cost.
4. **Skills to mark.** One line per unmarked skill the file looks governed by: its path, as listed
   under `# Skills not marked for this file`; then the line numbers of the file that suggest it, or
   the sent sentence that points to it, quoted verbatim.
5. One closing line: `conformant`, or `departures: <n>` with n the number of lines of section 1;
   section 4 changes neither.

Open a section with its bold label, never a Markdown heading: the entry already sits under the
report's own heading. Quote a rule's deciding clause, never paraphrase it. Propose, never decide — a
mark no less than a rule. Do not rewrite the file.
