"""Regenerate tests/fixtures/desktop_commands.json from the installed Hermes.

The cheatsheet's curated intent ids must all be commands the *desktop* surface
advertises. This snapshot is the guard's reference set.

    python scripts/snapshot_desktop_commands.py

Requires ``hermes_cli`` importable (run it with the Hermes venv or on any machine
with Hermes installed). Writes the file even when run from the plugin venv.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HIDDEN_DESKTOP = {"terminal", "messaging", "hidden"}


def main() -> int:
    try:
        from hermes_cli import commands as C
    except Exception as exc:  # noqa: BLE001 - report and exit, this is a tool
        print(f"cannot import hermes_cli: {exc}", file=sys.stderr)
        return 1

    names = []
    for cmd in C.COMMAND_REGISTRY:
        meta = C.command_desktop_meta(cmd)
        if meta.get("desktop") in HIDDEN_DESKTOP:
            continue
        if getattr(cmd, "gateway_only", False):
            continue
        names.append(cmd.name)

    payload = {
        "_note": (
            "Desktop-visible slash command names advertised by commands.catalog. "
            "Regenerate with scripts/snapshot_desktop_commands.py."
        ),
        "commands": sorted(names),
    }
    out = REPO / "tests" / "fixtures" / "desktop_commands.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(names)} commands)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
