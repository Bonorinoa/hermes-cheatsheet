# Cheatsheet — Intent Reframe Implementation Plan

> **For Hermes:** implement task-by-task; verify each task before moving on. This is a
> capability-neutral UI/data change to a plugin already published in the Hermes catalog
> (entry pinned `sha: 266d739701203713367ed72491b5564b1140527b`).

**Goal:** Turn the published "Cheatsheet" desktop plugin into an intent-first surface —
"I want to do …" → a cited command / plugin / doc passage — while changing **no
capabilities**, so catalog rules 6 (capabilities match reality) and 13 (disclosure) stay
satisfied and the re-pin is a small, boring review.

**Architecture:** Two halves, both already present.
- Desktop half (`desktop/plugin.js`, React via `jsx()` on the `@hermes/plugin-sdk`): renders
  the dialog, calls gateway RPCs (`commands.catalog`, `plugins.manage`, `mcp.servers.list`)
  and the plugin's own local route via `pluginCtx.rest(...)`.
- Backend half (`dashboard/plugin_api.py` → `cheatsheet_index.py`): a local, network-free
  route that does BM25 over the install's `website/docs` (query-time, mtime-cached) plus a
  frozen `community.json`.

The reframe adds a **curated intent map** (query phrases → command ids and doc/issue ids)
and renders a "Suggested" block. No new network, no new tools/hooks/env, no `llm.oneshot`.

**Tech stack:** Python 3 + FastAPI (backend route), pytest (tests), ESM JavaScript with
`jsx()` (desktop half), `hermes plugins validate` (admission).

**Reference artifacts (design intent, already built):**
- `sketches/001-intent-reframe/index.html` — the working mockup (Before / After·A / After·B),
  with the expanded test corpus and a built-in eval suite (`?selftest=1`).
- `sketches/001-intent-reframe/README.md` — the three stances + the review-cost reasoning.

---

## Scope decisions (locked)

- **Stance:** discover-first ("After · B") open state (intent chips when the query is empty)
  that collapses into the search-first "After · A" result view once the user types.
- **Capability-neutral:** `capabilities:` stays all empty. No `llm.oneshot`. No runtime
  network. The disclosure sentence in the README and the catalog entry does **not** change.
- **Name/id unchanged:** `cheatsheet`, tier `community`, category `desktop`. Do not rename
  (rule 16 — one listing per lineage).
- **Practices stays** and is *reused*, not replaced: the doc/issue passages the intent search
  surfaces come from the existing `/practices` route. The Practices tab keeps its own
  browse/facet mode. This is what stops Practices looking "stale" — it becomes the retrieval
  source for the search instead of a dead list. (It was never stale server-side: the docs
  half re-reads `website/docs` at query time; only `community.json` is frozen by design.)
- **v2 (explicitly deferred, separate PR):** `llm.oneshot` rerank + tl;dr, and
  `connectors.catalog` / `skills.manage` recommendations. Both move the disclosure.

---

## Task 1: Extract the curated intent map into a testable Python module

**Objective:** Put the phrase→id map and the eval suite where pytest can reach them.

**Files:**
- Create: `cheatsheet_intents.py`
- Reference: the mockup's `INTENTS` and `EVAL` arrays in `sketches/001-intent-reframe/index.html`

**Step 1: Write the module**

```python
"""Curated intent map for the cheatsheet. Data only — no network, no I/O."""
from __future__ import annotations

from typing import Any

# phrase → command ids / doc ids / issue ids. Hits are validated against the live set before render.
INTENTS: list[dict[str, Any]] = [
    {"keys": ["without interrupting", "side question", "quick question", "by the way"], "cmds": ["btw", "bg"], "docs": ["doc:commands#background"]},
    {"keys": ["in the background", "background", "without blocking", "long job"], "cmds": ["bg"], "docs": ["doc:commands#background"]},
    {"keys": ["schedule", "recurring", "every day", "remind me", "cron job", "daily"], "cmds": ["cron"], "docs": ["doc:automation/cron"]},
    # … port every entry from the mockup's INTENTS (20 entries)
]

# eval suite: query → ids that MUST appear in the match result (regression guard)
EVAL: list[dict[str, Any]] = [
    {"q": "ask a quick question without interrupting the model", "cmds": ["btw", "bg"]},
    {"q": "schedule a daily reminder", "cmds": ["cron"]},
    {"q": "how do I not break the prompt cache", "docs": ["doc:concepts/prompt-cache"]},
    # … port every entry from the mockup's EVAL (16 entries, incl. the {"none": True} precision case)
]


def match(query: str) -> dict[str, list[str]]:
    """Rank intents by the longest contained phrase; union the top 3."""
    n = (query or "").strip().lower()
    out: dict[str, list[str]] = {"cmds": [], "docs": [], "issues": []}
    if len(n) < 4:
        return out
    scored = []
    for it in INTENTS:
        s = sum(len(k) + 2 for k in it["keys"] if k in n)
        if s:
            scored.append((s, it))
    scored.sort(key=lambda row: -row[0])
    for _, it in scored[:3]:
        for kind in ("cmds", "docs", "issues"):
            for h in it.get(kind, []):
                if h not in out[kind]:
                    out[kind].append(h)
    return out
```

**Step 2: Sanity-run**

Run: `python3 -c "import cheatsheet_intents as m; print(m.match('schedule a daily reminder'))"`
Expected: `{'cmds': ['cron'], 'docs': [...], 'issues': []}`

**Step 3: Commit**

```bash
git add cheatsheet_intents.py
git commit -m "feat(intents): curated intent map + eval suite as data"
```

---

## Task 2: Regression test the intent map (the eval suite)

**Objective:** Make the eval suite pass in CI, so recall regressions fail the build.

**Files:**
- Create: `tests/test_intents.py`

**Step 1: Write the failing test**

```python
import cheatsheet_intents as m


def test_all_eval_cases_pass():
    failures = []
    for c in m.EVAL:
        r = m.match(c["q"])
        got = r["cmds"] + r["docs"] + r["issues"]
        if c.get("none"):
            ok = got == []
        else:
            ok = all(x in got for x in c.get("cmds", []) + c.get("docs", []) + c.get("issues", []))
        if not ok:
            failures.append((c["q"], got))
    assert not failures, failures
```

**Step 2: Run**

Run: `.venv/bin/python -m pytest tests/test_intents.py -v`
Expected: PASS (port the mockup's 16 cases; adjust doc ids to the real `doc:` scheme).

**Step 3: Commit**

```bash
git add tests/test_intents.py
git commit -m "test(intents): eval-suite regression guard"
```

---

## Task 3: Serve the map from the plugin route

**Objective:** Let the desktop half ask the backend "what ids does this query map to?"

**Files:**
- Modify: `dashboard/plugin_api.py` (add one route; reuse the existing importlib loader)

**Step 1: Add the route**

```python
_INTENTS_MODULE = _load_named_module("cheatsheet_intents", _PLUGIN_DIR / "cheatsheet_intents.py")


@router.get("/suggest")
async def suggest(q: str = Query(default="")):
    return _INTENTS_MODULE.match(q)
```

(Refactor `_load_index_module` into a small `_load_named_module(name, path)` helper so both
modules load through the same spec-from-file path.)

**Step 2: Run the route locally**

Run: `python3 -c "import sys; sys.path.insert(0,'.'); from cheatsheet_intents import match; print(match('hot reload a plugin'))"`
Expected: `{'cmds': [], 'docs': ['doc:plugins/desktop-plugins'], 'issues': []}`

**Step 3: Commit**

```bash
git add dashboard/plugin_api.py
git commit -m "feat(api): /suggest route over the curated intent map"
```

---

## Task 4: Reframe the desktop half — intent field + Suggested block

**Objective:** Reframe copy, add the Suggested block, and wire it to live data.

**Files:**
- Modify: `desktop/plugin.js` (one file; the primary diff)

**Step 1: Static data (top of file)**

Add `const CHIPS = [...]` (port the mockup's 10 chips) — the only new static data on the
desktop side. The map itself stays server-side (Task 3).

**Step 2: Reframe copy (no logic)**

- Dialog title stays `Cheatsheet`.
- Description → "Describe what you want to do. Suggestions point to a real command, plugin,
  or guide — nothing is generated, nothing invented."
- Search placeholder (non-practices) → "What do you want to do?  e.g. ask a question without
  interrupting the model".
- Empty/error states → intent phrasing.

**Step 3: Wire the Suggested block**

On query change (debounced ~200 ms, same pattern as `loadPractices`):

```js
// commands: already-fetched catalog filtered to the suggested ids
const suggestion = await pluginCtx.rest(`/suggest?q=${encodeURIComponent(query)}`)
const docIds = suggestion.docs.concat(suggestion.issues)
const passages = docIds.length
  ? (await pluginCtx.rest(`/practices?q=${encodeURIComponent(query)}`)).hits
  : []
// render: commands (validated against the live commands.catalog) + passages (PassageRow)
```

**Hard rule:** every suggested command id is checked against the live `commands.catalog`
before render; unknown ids are dropped. This is structural grounding — the model-free
version of "never invent".

**Step 4: Discover-first open state**

When the `commands` tab is active and the query is empty, render `CHIPS` above the list
(clicking a chip sets the query). When the query is non-empty, render Suggested + results.

**Step 5: Degrade gracefully**

If `pluginCtx.rest('/suggest')` is unavailable (backend half off — the two-toggle), fall
back to commands-only matching against `commands.catalog`, and render nothing for passages.
Never show fake data; show the exact "enable the backend" sentence instead.

**Step 6: Verify visually**

Run: `hermes plugins install <repo> --ref <working-sha> --force` then ⌘K → Reload desktop
plugins, and check the three states against `sketches/001-intent-reframe/*.png`.

**Step 7: Commit**

```bash
git add desktop/plugin.js
git commit -m "feat(ui): intent-first field + cited Suggested block"
```

---

## Task 5: Admission + tests

**Objective:** Pass every gate the catalog requires.

**Files:** none (verification only)

**Step 1:** `.venv/bin/python -m pytest -q` → expect all pass (incl. Task 2).
**Step 2:** `hermes plugins validate . --install-deps` → expect green: manifest, loadable
entry, `security scan` (no new findings — no network added), `no core override`,
`desktop surface` (only SDK/react imports; no `eval`, no DOM reach into core markup).
**Step 3:** Confirm `capabilities:` in the catalog entry is still all-`[]` and the README
disclosure sentence is byte-identical.

---

## Task 6: Re-pin the catalog entry (do NOT push until approved)

**Objective:** Stage the SHA-bump PR without opening it.

**Files:**
- Modify (in `NousResearch/hermes-agent` fork branch): `plugin-catalog/cheatsheet.yaml`

**Step 1:** Bump `sha:` to the new commit; leave `description`, `tier`, `category`,
`version` (bump `version` to `0.2.0`) otherwise intact — the disclosure text is unchanged.
**Step 2:** Run `hermes plugins validate` at the pinned commit (CI parity).
**Step 3:** Present the diff + fresh screenshots to Augusto. Open the PR only on approval.

---

## Files likely to change

| File | Change |
|---|---|
| `cheatsheet_intents.py` | **new** — curated map + eval suite |
| `tests/test_intents.py` | **new** — eval-suite regression |
| `dashboard/plugin_api.py` | add `/suggest`; factor the module loader |
| `desktop/plugin.js` | reframe copy, CHIPS, Suggested block, discover-first open state |
| `README.md` | describe the intent search (disclosure line unchanged) |
| `plugin-catalog/cheatsheet.yaml` (other repo) | bump `sha`, `version` |

Not changed: `cheatsheet_index.py`, `community.json`, `plugin.yaml`, `capabilities:`.

## Risks / tradeoffs / open questions

- **Recall vs precision of a phrase map.** The mockup's eval caught one real miss
  ("where do I install plugins from"). Mitigation: the eval suite (Task 2) guards this; every
  new gap becomes a key variant. This is the honest ceiling of a *curated* map — it will miss
  unseen phrasings by design. v2 (`llm.oneshot` rerank over the same candidates) is the fix,
  at the cost of the disclosure change.
- **Map size / reviewability.** Keep it curated (~20–40 intents). A huge map is un-auditable
  and re-opens the "is this still a cheatsheet?" question.
- **Two-toggle dependency.** Passage hits need the backend half enabled. The UI must degrade
  to commands-only cleanly (Task 4, step 5).
- **Docs freshness.** The `/practices` index reflects the *installed* Hermes docs; on an old
  install, a passage may not exist. Acceptable — it is the same surface the Practices tab
  already ships.
- **Review cost.** Diff touches one new Python module, one new test, one route, and the
  desktop file. No capability/disclosure change → a proportional, small review.
- **Open question for Augusto:** should the curated map ship its *chips* server-side too
  (so chips and phrases stay in one data file), or keep chips inline in `plugin.js`? Inline is
  a smaller diff; server-side is more DRY and testable. Recommend server-side (same `/suggest`
  route can return `chips`).
