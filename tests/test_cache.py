from cheatsheet_index import Index, docs_signature, get_cached_index

def test_cache_reuses_index_until_mtime_changes(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("## Change skins\n\n" + ("keep the background. " * 20), encoding="utf-8")
    calls = {"n": 0}

    def fake_build(root, community):
        calls["n"] += 1
        return Index(chunks=[{"id": "x", "kind": "doc", "where": "Docs", "title": "t", "url": "https://example.com", "text": "t" * 120}])

    monkeypatch.setattr("cheatsheet_index.build_index", fake_build)
    first = get_cached_index(docs, community=[])
    second = get_cached_index(docs, community=[])
    assert first is second
    assert calls["n"] == 1
    (docs / "a.md").write_text("## Change skins\n\n" + ("keep the background. " * 21), encoding="utf-8")
    third = get_cached_index(docs, community=[])
    assert third is not first
    assert calls["n"] == 2
    assert isinstance(docs_signature(docs), tuple)
