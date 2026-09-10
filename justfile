default:
    @just --list --unsorted

# Refresh the shared skills once at the start of a task.
skills-sync:
    python3 .origin89/sync-engineering.py

# Validate the exact filed export selected for this board.
check: gerbers

gerbers:
    python3 tools/validate_gerbers.py boards/controller-a/gerber-rules.json boards/controller-a/build/2026-09-09/gerber.zip
