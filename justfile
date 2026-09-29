default:
    @just --list --unsorted

# Refresh the shared skills once at the start of a task.
skills-sync:
    python3 .origin89/sync-engineering.py

# Validate the exact filed export selected for this board, and the tools that do it.
check: gerbers silkscreen test

# Behaviour tests for the repository's own tools; standard library only.
test:
    python3 -m unittest discover -s tools -p 'test_*.py'

gerbers:
    python3 tools/validate_gerbers.py boards/controller-a/gerber-rules.json boards/controller-a/build/2026-09-20/gerber.zip

# Check an export's silkscreen text against the A-33 label list. Defaults to the
# filed export.
silkscreen dxf="boards/controller-a/build/2026-09-20/board.dxf":
    python3 tools/validate_silkscreen.py boards/controller-a/gerber-rules.json {{dxf}}
