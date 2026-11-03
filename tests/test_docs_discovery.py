"""Docs-tree discovery and .md/.mdx indexing over real on-disk layouts.

The plugin is installed into whatever Hermes checkout the user runs, so it
must cite the Fumadocs corpus (``apps/docs/content/en``, ``.md`` + ``.mdx``)
on migrated checkouts and still fall back to ``website/docs`` on released
versions. Every test here builds a real tree on disk and drives the actual
discovery/read/index/search paths — no filesystem mocks, no source-string
assertions.
"""

import asyncio
import sys
import types
from pathlib import Path

import cheatsheet_index as ci

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))

import plugin_api

DOCS_SITE = "https://hermes-agent.nousresearch.com/docs"


def _fake_hermes_cli(monkeypatch, checkout: Path) -> None:
    """Make ``import hermes_cli`` resolve to a package inside ``checkout``."""
    pkg = checkout / "hermes_cli"
    pkg.mkdir(parents=True, exist_ok=True)
    init = pkg / "__init__.py"
    init.write_text("", encoding="utf-8")
    module = types.ModuleType("hermes_cli")
    module.__file__ = str(init)
    monkeypatch.setitem(sys.modules, "hermes_cli", module)


def _write_doc(path: Path, heading: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {path.stem}\n\n## {heading}\n\n{body}", encoding="utf-8")


def _long(text: str) -> str:
    return (text + " ") * 12


# --- discovery: which docs tree does this install expose? -------------------


def test_discovers_fumadocs_layout(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    _fake_hermes_cli(monkeypatch, checkout)
    _write_doc(
        checkout / "apps" / "docs" / "content" / "en" / "guides" / "quickstart.mdx",
        "Install the CLI",
        _long("run the installer script to set up the hermes agent command line"),
    )
    root = ci.docs_root_for_install()
    assert root is not None
    assert root == (checkout / "apps" / "docs" / "content" / "en").resolve()
    # the discovered root actually indexes — the review's "0 chunks" bug
    index = ci.build_index(root, community=[])
    assert any(c["id"].startswith("doc:guides/quickstart.mdx#") for c in index.chunks)


def test_falls_back_to_website_docs_layout(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    _fake_hermes_cli(monkeypatch, checkout)
    _write_doc(
        checkout / "website" / "docs" / "guides" / "cron.md",
        "Schedule a recurring job",
        _long("cron jobs run on a schedule without keeping the terminal busy"),
    )
    root = ci.docs_root_for_install()
    assert root is not None
    assert root == (checkout / "website" / "docs").resolve()
    index = ci.build_index(root, community=[])
    assert any(c["id"].startswith("doc:guides/cron.md#") for c in index.chunks)


def test_fumadocs_layout_wins_when_both_exist(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    _fake_hermes_cli(monkeypatch, checkout)
    _write_doc(checkout / "website" / "docs" / "old.md", "Legacy page", _long("the old layout"))
    _write_doc(
        checkout / "apps" / "docs" / "content" / "en" / "new.mdx",
        "Migrated page",
        _long("the new fumadocs layout"),
    )
    assert ci.docs_root_for_install() == (checkout / "apps" / "docs" / "content" / "en").resolve()


def test_returns_none_when_no_docs_tree(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    _fake_hermes_cli(monkeypatch, checkout)
    assert ci.docs_root_for_install() is None


# --- indexing: .md and .mdx, together, deterministically ---------------------


def test_indexes_mdx_pages_with_clean_urls(tmp_path):
    docs = tmp_path / "docs"
    _write_doc(
        docs / "getting-started" / "quickstart.mdx",
        "Install the CLI",
        _long("run the installer script to set up the hermes agent command line"),
    )
    _write_doc(docs / "index.mdx", "Welcome to Hermes", _long("the documentation root page"))
    index = ci.build_index(docs, community=[])
    quickstart = [c for c in index.chunks if "quickstart" in c["id"]]
    assert quickstart, index.chunks
    # extension-derived id/route: .mdx appears in the id, never in the URL
    assert quickstart[0]["id"].startswith("doc:getting-started/quickstart.mdx#install-the-cli")
    assert quickstart[0]["url"] == f"{DOCS_SITE}/getting-started/quickstart#install-the-cli"
    assert quickstart[0]["title"] == "quickstart · Install the CLI"
    # a root index page maps to the docs base URL, same as index.md always did
    root_page = [c for c in index.chunks if "index.mdx" in c["id"]]
    assert root_page, index.chunks
    assert root_page[0]["url"] == f"{DOCS_SITE}#welcome-to-hermes"


def test_mixed_suffixes_are_all_indexed(tmp_path):
    docs = tmp_path / "docs"
    _write_doc(docs / "alpha.md", "Alpha topic", _long("the alpha page covers the first topic"))
    _write_doc(docs / "beta.mdx", "Beta topic", _long("the beta page covers the second topic"))
    index = ci.build_index(docs, community=[])
    ids = [c["id"] for c in index.chunks]
    assert any(i.startswith("doc:alpha.md#") for i in ids), ids
    assert any(i.startswith("doc:beta.mdx#") for i in ids), ids
    for chunk in index.chunks:
        assert ".mdx" not in chunk["url"] and ".md" not in chunk["url"]


def test_duplicate_stem_is_indexed_once_from_the_md_file(tmp_path):
    docs = tmp_path / "docs"
    _write_doc(docs / "guide.md", "One topic", _long("the canonical markdown body text"))
    _write_doc(docs / "guide.mdx", "Other topic", _long("the stray twin orphan page content"))
    index = ci.build_index(docs, community=[])
    doc_chunks = [c for c in index.chunks if c["kind"] == "doc"]
    assert len(doc_chunks) == 1, doc_chunks
    assert doc_chunks[0]["id"].startswith("doc:guide.md#")
    # and the dropped twin really is unreachable through search
    assert ci.search(index, "orphan twin content", facet="doc") == []


def test_indexing_is_deterministic_across_rebuilds(tmp_path):
    docs = tmp_path / "docs"
    _write_doc(docs / "alpha.md", "Alpha topic", _long("the alpha page covers the first topic"))
    _write_doc(docs / "beta.mdx", "Beta topic", _long("the beta page covers the second topic"))
    _write_doc(docs / "sub" / "gamma.md", "Gamma topic", _long("the gamma page covers the third topic"))
    first = ci.build_index(docs, community=[])
    second = ci.build_index(docs, community=[])
    assert [c["id"] for c in first.chunks] == [
        "doc:alpha.md#alpha-topic",
        "doc:beta.mdx#beta-topic",
        "doc:sub/gamma.md#gamma-topic",
    ]
    assert [c["id"] for c in second.chunks] == [c["id"] for c in first.chunks]


def test_hidden_directories_are_still_skipped(tmp_path):
    docs = tmp_path / "docs"
    _write_doc(docs / "real.md", "Real topic", _long("the visible page body text"))
    _write_doc(docs / ".hidden" / "cache.md", "Hidden topic", _long("the hidden page body text"))
    index = ci.build_index(docs, community=[])
    assert [c["id"] for c in index.chunks] == ["doc:real.md#real-topic"]


def test_search_retrieves_an_mdx_passage(tmp_path):
    docs = tmp_path / "docs"
    _write_doc(
        docs / "quickstart.mdx",
        "Install the CLI",
        _long("run the installer script to set up the hermes agent command line"),
    )
    index = ci.build_index(docs, community=[])
    hits = ci.search(index, "install the cli", facet="doc")
    assert hits, index.chunks
    assert hits[0]["id"].startswith("doc:quickstart.mdx#")
    assert hits[0]["url"] == f"{DOCS_SITE}/quickstart#install-the-cli"


def test_signature_counts_mdx_and_cache_rebuilds(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text(
        "# a\n\n## Alpha topic\n\n" + _long("the alpha page covers the first topic"), encoding="utf-8"
    )
    first = ci.get_cached_index(docs, community=[])
    assert ci.docs_signature(docs) != ("missing",)
    (docs / "b.mdx").write_text(
        "# b\n\n## Beta topic\n\n" + _long("the beta page covers the second topic"), encoding="utf-8"
    )
    second = ci.get_cached_index(docs, community=[])
    assert second is not first  # the .mdx landing must invalidate the cache
    assert any(c["id"].startswith("doc:b.mdx#") for c in second.chunks)


def test_missing_root_indexes_nothing(tmp_path):
    assert ci.build_index(tmp_path / "missing", community=[]).chunks == []
    assert ci.docs_signature(tmp_path / "missing") == ("missing",)


# --- the plugin API: /practices over the new layout ---------------------------


def test_practices_serves_the_fumadocs_corpus_end_to_end(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    _fake_hermes_cli(monkeypatch, checkout)
    _write_doc(
        checkout / "apps" / "docs" / "content" / "en" / "guides" / "quickstart.mdx",
        "Install the CLI",
        _long("run the installer script to set up the hermes agent command line"),
    )
    out = asyncio.run(plugin_api.practices(q="install the cli"))
    assert out["docs_root"] == str((checkout / "apps" / "docs" / "content" / "en").resolve())
    assert out["counts"]["doc"] == 1
    assert any(h["id"].startswith("doc:guides/quickstart.mdx#") for h in out["hits"]), out["hits"]
    assert not any("Docs tree not found" in gap for gap in out["gaps"])


def test_practices_reports_the_gap_when_no_docs_tree(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    _fake_hermes_cli(monkeypatch, checkout)
    out = asyncio.run(plugin_api.practices(q="install the cli"))
    assert out["docs_root"] == ""
    assert out["counts"]["doc"] == 0
    assert any("Docs tree not found" in gap for gap in out["gaps"])
