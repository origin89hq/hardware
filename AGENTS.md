# Working in this repository

At the start of each new task, run `just skills-sync` from the repository root.
Read `skills/origin89-working/SKILL.md` and the relevant domain skills under the
immutable `path` printed by that command. Keep that snapshot for the task; do not
refresh it halfway through work. Read local instructions and preserve stronger
project constraints and project-specific skills.

If refresh reports cached content, continue with that verified cache and mention
that the script could not check for updates. If no cache is available or
validation fails, report the error; do not claim the shared rules loaded. Local
instructions and the user's request still apply. Do not overwrite local skill
files to fix a conflict without reconciling them.

[Origin89 engineering](https://github.com/origin89hq/engineering) owns the shared
rules. Keep only repository-specific architecture, commands, target constraints,
and exceptions below. Internal RFCs and research belong in
[internal-research](https://github.com/origin89hq/internal-research). Add documentation
only when its value and upkeep are clear; remove AI filler from every message.

## Board work

Read `CONTRIBUTING.md` and the affected board's requirements and Gerber rules
before changing artwork. Preserve EasyEDA sources and archived fabrication
exports. Import new exports through `tools/import_easyeda_export.py`;
validation must not modify them.

Run `just check` for the selected controller export. Report the exact rule
failures and keep them visible. Gerber validation does not establish electrical
or bench qualification. Include board revision and measured evidence for
hardware claims. This is a Python/CAD repo; do not add Node or Cargo workspaces
without actual consumers.
