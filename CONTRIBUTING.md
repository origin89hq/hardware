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
