#!/usr/bin/env python3
"""Release-time refresh of community.json from the GitHub API.

Run by a maintainer before a catalog SHA-bump PR. The installed plugin never
runs this. Exits 1 and writes nothing if any fetch fails or the result would
not be an improvement.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cheatsheet_index import _clip

ISSUES = (71446, 81785, 107486, 73987)
OUT = REPO_ROOT / "community.json"


def fetch_issue(number: int) -> dict:
    import urllib.request

    url = f"https://api.github.com/repos/NousResearch/hermes-agent/issues/{number}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "hermes-cheatsheet/1.0 (release refresh)", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def main() -> int:
    records = []
    for number in ISSUES:
        try:
            item = fetch_issue(number)
        except Exception as exc:
            print(f"fetch #{number} failed: {exc}", file=sys.stderr)
            return 1
        url = item.get("html_url") or ""
        title = (item.get("title") or "").strip()
        body = _clip(item.get("body") or "")
        if not url or not title or len(body) < 80:
            print(f"#{number} produced an unusable record", file=sys.stderr)
            return 1
        records.append(
            {
                "id": f"gh:{number}",
                "kind": "issue",
                "where": "GitHub",
                "title": title[:160],
                "url": url,
                "text": body,
            }
        )
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} with {len(records)} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())