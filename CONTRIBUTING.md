# Contributing

A rule in `LAYOUT-REQUIREMENTS.md` or `GENERATOR-BOARD.md` carries its reason.
Propose a change to a rule by arguing with the reason, in an issue, before
anyone moves copper. A change to a board file comes with the rule it serves
and the check that shows it kept: `tools/validate_gerbers.py` for the copper,
the bench procedure for anything the copper cannot witness.

Say what was measured and on which board. "Works on the bench" with a board
revision and a date is a result; "should work" is not.

File a fabrication export with `tools/import_easyeda_export.py`. It dates
the directory, fixes the names, and refuses to change a file that is already
filed. Export the schematic PDF with it. Then run the Gerber check and put
the result, pass or the rule numbers that failed, in the board README's
revision table.

## Development setup

Follow the [Origin89 engineering standards](https://github.com/origin89hq/engineering)
for working practices, tests, writing, and commits. `AGENTS.md` loads shared
skills at the start of a task; `just skills-sync` refreshes them from engineering.
Keep local constraints and domain-specific checks alongside those shared rules.

Track confirmed problems left outside the current fix using the
[shared issue rule](https://github.com/origin89hq/engineering/blob/main/skills/origin89-working/SKILL.md#track-unfinished-work).
Use `gh` to find or create the issue, verify it, and return its URL.

Install just 1.58.0 and Python 3.9+ for the skill bootstrap. Run `just --list`
for repository commands and `just check` before opening a pull request.

Create a Python 3.12 virtual environment and install `requirements-dev.txt`
with `python -m pip install --require-hashes -r requirements-dev.txt`. CI uses the same pins.

Dependency updates start in `requirements-dev.in`; regenerate the hash-locked
`requirements-dev.txt` from the repository root:

```sh
uv pip compile requirements-dev.in --python-version 3.12 \
  --generate-hashes --universal --no-header -o requirements-dev.txt
```

Update the export selected by `just gerbers` when filing a reviewed board revision.
