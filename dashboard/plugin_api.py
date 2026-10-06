from fastapi import APIRouter

router = APIRouter()


@router.get("/practices")
async def practices(q: str = "", facet: str = "all"):
    return {
        "hermes_version": "",
        "docs_root": "",
        "indexed_at": "",
        "counts": {"doc": 0, "issue": 0},
        "prompts": [],
        "gaps": ["Indexer not implemented."],
        "hits": [],
    }