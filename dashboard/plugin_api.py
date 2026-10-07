import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Query

_PLUGIN_DIR = Path(__file__).resolve().parent.parent


def _load_index_module():
    spec = importlib.util.spec_from_file_location(
        "cheatsheet_index", _PLUGIN_DIR / "cheatsheet_index.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_INDEX_MODULE = _load_index_module()
GAPS = _INDEX_MODULE.GAPS
PROMPTS = _INDEX_MODULE.PROMPTS
docs_root_for_install = _INDEX_MODULE.docs_root_for_install
get_cached_index = _INDEX_MODULE.get_cached_index
search = _INDEX_MODULE.search

router = APIRouter()
_COMMUNITY = json.loads(
    (_PLUGIN_DIR / "community.json").read_text(encoding="utf-8")
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
