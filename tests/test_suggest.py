import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))

import plugin_api


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    page = tmp_path / "docs" / "concepts"
    page.mkdir(parents=True)
    (page / "context.md").write_text(
        "# Context\n\n## Compress a long conversation\n\n"
        + "compress the conversation when it is getting too long. " * 12,
        encoding="utf-8",
    )
    # A doc that contains one of the gibberish query's tokens, so the precision test
    # below is meaningful: without the coverage floor this doc WOULD be returned.
    (page / "widgets.md").write_text(
        "# Widgets\n\n## Rendering widgets\n\n" + "the widget renders a widget in the sidebar. " * 12,
        encoding="utf-8",
    )
    return tmp_path / "docs"


def test_suggest_returns_commands_and_cited_hits(docs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(plugin_api, "docs_root_for_install", lambda: docs)
    out = asyncio.run(plugin_api.suggest(q="the conversation is getting too long"))
    assert "compress" in out["cmds"]
    assert any(hit["kind"] == "doc" for hit in out["hits"])
    assert out["chips"]


def test_suggest_empty_query_is_chips_only(docs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(plugin_api, "docs_root_for_install", lambda: docs)
    out = asyncio.run(plugin_api.suggest(q=""))
    assert out["cmds"] == []
    assert out["hits"] == []
    assert len(out["chips"]) >= 5


def test_suggest_unknown_query_is_empty(docs: Path, monkeypatch: pytest.MonkeyPatch):
    """The coverage floor drops a chunk matching only one of three query terms.

    The fixture DOES contain "widget", so this fails if the floor is removed.
    """
    monkeypatch.setattr(plugin_api, "docs_root_for_install", lambda: docs)
    out = asyncio.run(plugin_api.suggest(q="xyzzy frobnicate the widget"))
    assert out["cmds"] == []
    assert out["hits"] == []


def test_suggest_relevant_query_keeps_hits(docs: Path, monkeypatch: pytest.MonkeyPatch):
    """The floor must not suppress a query that genuinely matches."""
    monkeypatch.setattr(plugin_api, "docs_root_for_install", lambda: docs)
    out = asyncio.run(plugin_api.suggest(q="compress a long conversation"))
    assert any(hit["kind"] == "doc" for hit in out["hits"])


def test_suggest_filler_words_do_not_raise_the_bar(docs: Path, monkeypatch: pytest.MonkeyPatch):
    """Filler words must not inflate the coverage bar (a regression guard for F1)."""
    monkeypatch.setattr(plugin_api, "docs_root_for_install", lambda: docs)
    out = asyncio.run(plugin_api.suggest(q="please help me compress my conversation"))
    assert any(hit["kind"] == "doc" for hit in out["hits"])
