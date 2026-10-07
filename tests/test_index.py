import json
from pathlib import Path

import pytest

from cheatsheet_index import build_index, search

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def community() -> list[dict]:
    return json.loads((REPO_ROOT / "community.json").read_text(encoding="utf-8"))


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    page = tmp_path / "docs" / "user-guide" / "features"
    page.mkdir(parents=True)
    (page / "skins.md").write_text(
        "# Skins\n\n## See also\n\nshort\n\n## Change skins\n\n"
        + "hermes skin set edits the active skin in place and keeps the background.\n" * 3,
        encoding="utf-8",
    )
    return tmp_path / "docs"


def test_chunks_a_heading_and_skips_see_also(docs: Path):
    index = build_index(docs, community=[])
    titles = [c["title"] for c in index.chunks]
    assert "Change skins" in titles
    assert all("see also" not in t.lower() for t in titles)
    assert all(c["kind"] == "doc" for c in index.chunks)
    assert index.chunks[0]["url"].startswith("https://hermes-agent.nousresearch.com/docs/")


def test_search_returns_at_most_eight_and_respects_facet(docs: Path, community: list[dict]):
    index = build_index(docs, community=community)
    hits = search(index, "custom backend skins don't persist", facet="issue", limit=8)
    assert 1 <= len(hits) <= 8
    assert all(h["kind"] == "issue" for h in hits)
    assert "persist" in hits[0]["title"].lower()


def test_empty_query_is_not_a_dump(docs: Path):
    index = build_index(docs, community=[])
    assert search(index, "", facet="all", limit=8) == []
