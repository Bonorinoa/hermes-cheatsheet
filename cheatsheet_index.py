"""Cited passages from a Hermes docs tree plus a committed community file.

No network. No writes. Callers pass the docs directory.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

DOCS_SITE = "https://hermes-agent.nousresearch.com/docs"
MAX_TEXT = 900
SKIP_TITLES = {"see also", "overview", "introduction", "contents", "table of contents"}
STOP = set(
    "the a an of to and or in on for with is are be this that it as at by from your you not".split()
)
PROMPTS = [
    "Don't Break the Prompt Cache",
    "Change skins",
    "desktop plugin hot reload",
    "Delegate for Parallel Work",
    "Parallel Research",
    "custom backend skins don't persist",
    "Kanban vs delegate_task",
    "Installing from the Hub",
]
GAPS = [
    "Reddit is not in the index.",
    "X posts are not in the index.",
]


def _clean(text: str) -> str:
    text = re.sub(r"```.*?```", lambda m: " " + m.group(0).replace("`", "") + " ", text, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _clip(text: str) -> str:
    text = _clean(text)
    if len(text) <= MAX_TEXT:
        return text
    cut = text[:MAX_TEXT]
    return (cut.rsplit(" ", 1)[0] if " " in cut else cut) + "…"


def _slug(title: str) -> str:
    value = re.sub(r"[^\w\s-]", "", title.strip().lower())
    return re.sub(r"\s+", "-", value).strip("-")


def _doc_url(rel: Path, heading: str) -> str:
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "index":
        parts = parts[:-1]
    base = "/".join(parts)
    url = f"{DOCS_SITE}/{base}" if base else DOCS_SITE
    anchor = _slug(heading)
    return f"{url}#{anchor}" if anchor else url


def _tokens(value: str) -> list[str]:
    return [
        t
        for t in re.sub(r"[^a-z0-9+#./-]+", " ", value.lower()).split()
        if len(t) > 1 and t not in STOP
    ]


@dataclass
class Index:
    chunks: list[dict] = field(default_factory=list)
    docs: list[tuple] = field(default_factory=list)
    df: dict = field(default_factory=dict)
    avg: float = 1.0
    n: int = 1


def _chunk_docs(docs_root: Path) -> list[dict]:
    chunks = []
    if not docs_root.is_dir():
        return chunks
    for path in sorted(docs_root.rglob("*.md")):
        rel = path.relative_to(docs_root)
        if any(part.startswith(".") for part in rel.parts):
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        raw = re.sub(r"^---\n.*?\n---\n", "", raw, count=1, flags=re.S)
        file_title = path.stem.replace("-", " ").replace("_", " ")
        for piece in re.split(r"\n(?=#{2,3} )", raw):
            lines = piece.strip().splitlines()
            if not lines:
                continue
            heading = lines[0].lstrip("#").strip() if lines[0].startswith("#") else file_title
            if heading.lower() in SKIP_TITLES:
                continue
            body = "\n".join(lines[1:] if lines[0].startswith("#") else lines)
            text = _clip(body)
            if len(text) < 120:
                continue
            title = heading
            if lines[0].startswith("#") and file_title.lower() not in heading.lower():
                title = f"{file_title} · {heading}"
            chunks.append(
                {
                    "id": f"doc:{rel.as_posix()}#{_slug(heading)}",
                    "kind": "doc",
                    "where": "Docs",
                    "title": title[:160],
                    "url": _doc_url(rel, heading),
                    "text": text,
                }
            )
    return chunks


def build_index(docs_root: Path, community: list[dict]) -> Index:
    chunks = _chunk_docs(docs_root)
    for item in community:
        if item.get("kind") != "issue" or not item.get("url") or not item.get("text"):
            continue
        chunks.append(
            {
                "id": str(item["id"]),
                "kind": "issue",
                "where": "GitHub",
                "title": str(item["title"])[:160],
                "url": str(item["url"]),
                "text": _clip(str(item["text"])),
            }
        )
    df: dict[str, int] = {}
    docs = []
    for chunk in chunks:
        words = _tokens(f"{chunk['title']} {chunk['text']}")
        tf: dict[str, int] = {}
        for word in words:
            tf[word] = tf.get(word, 0) + 1
        for word in tf:
            df[word] = df.get(word, 0) + 1
        docs.append((chunk, tf, len(words) or 1))
    n = len(docs) or 1
    avg = sum(row[2] for row in docs) / n
    return Index(chunks=chunks, docs=docs, df=df, avg=avg, n=n)


def search(index: Index, query: str, facet: str = "all", limit: int = 8) -> list[dict]:
    terms = _tokens(query)
    if not terms:
        return []
    scored = []
    for chunk, tf, length in index.docs:
        if facet in ("doc", "issue") and chunk["kind"] != facet:
            continue
        score = 0.0
        for term in terms:
            freq = tf.get(term, 0)
            if not freq:
                continue
            seen = index.df.get(term, 0)
            idf = math.log(1 + (index.n - seen + 0.5) / (seen + 0.5))
            denom = freq + 1.2 * (1 - 0.75 + 0.75 * (length / index.avg))
            score += (idf * (freq * 2.2)) / denom
        title = chunk["title"].lower()
        for term in terms:
            if term in title:
                score += 0.6
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda row: -row[0])
    return [chunk for _, chunk in scored[:limit]]
