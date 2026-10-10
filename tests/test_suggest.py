import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))

import plugin_api


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    page = tmp_path / "docs" / "guides"
    page.mkdir(parents=True)
    (page / "automate-with-cron.md").write_text(
        "# Automate with cron\n\n## Schedule a recurring job\n\n"
        + "cron runs a recurring job on a schedule. " * 12,
        encoding="utf-8",
    )
    return tmp_path / "docs"


def test_suggest_returns_commands_and_cited_hits(docs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(plugin_api, "docs_root_for_install", lambda: docs)
    out = asyncio.run(plugin_api.suggest(q="schedule a recurring job"))
    assert "cron" in out["cmds"]
    assert any(hit["kind"] == "doc" for hit in out["hits"])
    assert out["chips"]


def test_suggest_empty_query_is_chips_only(docs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(plugin_api, "docs_root_for_install", lambda: docs)
    out = asyncio.run(plugin_api.suggest(q=""))
    assert out["cmds"] == []
    assert out["hits"] == []
    assert len(out["chips"]) >= 5


def test_suggest_unknown_query_is_empty(docs: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(plugin_api, "docs_root_for_install", lambda: docs)
    out = asyncio.run(plugin_api.suggest(q="xyzzy frobnicate the widget"))
    assert out["cmds"] == []
    assert out["hits"] == []
