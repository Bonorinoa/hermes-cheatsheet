import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Query

_PLUGIN_DIR = Path(__file__).resolve().parent.parent


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _PLUGIN_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses resolve __module__; drop it again on failure.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


_INDEX_MODULE = _load_module("cheatsheet_plugin_index", "cheatsheet_index.py")
_INTENTS_MODULE = _load_module("cheatsheet_plugin_intents", "cheatsheet_intents.py")

GAPS = _INDEX_MODULE.GAPS
PROMPTS = _INDEX_MODULE.PROMPTS
docs_root_for_install = _INDEX_MODULE.docs_root_for_install
get_cached_index = _INDEX_MODULE.get_cached_index
search = _INDEX_MODULE.search

match_intents = _INTENTS_MODULE.match
CHIPS = _INTENTS_MODULE.CHIPS

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


def _index():
    root = docs_root_for_install()
    if root is None:
        return get_cached_index(Path("/nonexistent"), _COMMUNITY), None
    return get_cached_index(root, _COMMUNITY), root


@router.get("/practices")
async def practices(q: str = Query(default=""), facet: str = Query(default="all")):
    if facet not in ("all", "doc", "issue"):
        facet = "all"
    index, root = _index()
    gaps = list(GAPS)
    if root is None:
        gaps.append("Docs tree not found next to this Hermes install.")
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


@router.get("/suggest")
async def suggest(q: str = Query(default="")):
    index, _root = _index()
    phrase = (q or "").strip()
    hits = search(index, phrase, facet="all", limit=3) if phrase else []
    return {
        "query": q,
        "chips": list(CHIPS),
        "cmds": match_intents(q)["cmds"],
        "hits": hits,
    }
