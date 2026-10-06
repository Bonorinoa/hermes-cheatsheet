import json
from pathlib import Path

from cheatsheet_index import build_index, search


def test_chunks_a_heading_and_skips_see_also(tmp_path: Path):
    docs = tmp_path / "docs"
    page = docs / "user-guide" / "features"
    page.mkdir(parents=True)
    (page / "skins.md").write_text(
        "# Skins\n\n## See also\n\nshort\n\n## Change skins\n\n"
        + "hermes skin set edits the active skin in place and keeps the background.\n" * 3,
        encoding="utf-8",
    )
    index = build_index(docs, community=[])
    titles = [c["title"] for c in index.chunks]
    assert "Change skins" in titles
    assert all("see also" not in t.lower() for t in titles)
    assert all(c["kind"] == "doc" for c in index.chunks)
    assert index.chunks[0]["url"].startswith("https://hermes-agent.nousresearch.com/docs/")


def test_search_returns_at_most_eight_and_respects_facet():
    docs = Path("/Users/bonorinoa/.hermes/hermes-agent/website/docs")
    community = json.loads(
        Path("/Users/bonorinoa/Hermes/Projects/hermes-cheatsheet/community.json").read_text()
    )
    index = build_index(docs, community=community)
    hits = search(index, "custom backend skins don't persist", facet="issue", limit=8)
    assert 1 <= len(hits) <= 8
    assert all(h["kind"] == "issue" for h in hits)
    assert "persist" in hits[0]["title"].lower()


def test_empty_query_is_not_a_dump():
    docs = Path("/Users/bonorinoa/.hermes/hermes-agent/website/docs")
    index = build_index(docs, community=[])
    assert search(index, "", facet="all", limit=8) == []