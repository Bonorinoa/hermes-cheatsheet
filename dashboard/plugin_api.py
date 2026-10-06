import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Query  # noqa: E402

from cheatsheet_index import GAPS, PROMPTS, docs_root_for_install, get_cached_index, search  # noqa: E402

router = APIRouter()
_COMMUNITY = json.loads(
    (Path(__file__).resolve().parent.parent / "community.json").read_text(encoding="utf-8")
)


def _version() -> str:
    try:
        import hermes_cli

        return str(hermes_cli.__version__)
    except Exception:
        return ""


@router.get("/practices")
async def practices(q: str = Query(default=""), facet: str = Query(default="all")):
    if facet not in ("all", "doc", "issue"):
        facet = "all"
    root = docs_root_for_install()
    gaps = list(GAPS)
    if root is None:
        gaps.append("Docs tree not found next to this Hermes install.")
        index = get_cached_index(Path("/nonexistent"), _COMMUNITY)
    else:
        index = get_cached_index(root, _COMMUNITY)
    if not q and facet == "issue":
        hits = [c for c in index.chunks if c["kind"] == "issue"][:12]
    else:
        hits = search(index, q, facet=facet, limit=8)
    return {
        "hermes_version": _version(),
        "docs_root": str(root or ""),
        "indexed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {
            "doc": sum(1 for c in index.chunks if c["kind"] == "doc"),
            "issue": sum(1 for c in index.chunks if c["kind"] == "issue"),
        },
        "prompts": list(PROMPTS),
        "gaps": gaps,
        "hits": hits,
    }
