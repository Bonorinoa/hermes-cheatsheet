# Cheatsheet — intent reframe (v1, capability-neutral)

Disposable mockup for the `desktop/plugin.js` UI reframe discussed 2026-10-09.
Not shippable code; a decision tool. Open `index.html` and use the state switcher
(or `?state=before|a|b&q=...`).

## The constraint that shapes this

Any change to the pinned plugin is a SHA-bump PR → re-review (catalog rule 4). The
review tracks the *diff*. So the goal is a **capability-neutral diff**: UI only, no
new `capabilities:` entries, no new data flow, no network. Then rule 6 (capabilities
match reality) and rule 13 (disclosure) stay satisfied, and the disclosure sentence
("…lists your commands, plugins and MCP servers via read-only gateway calls; no
network at runtime") remains literally true.

## The three states

### Before — as published (`266d7397`)
Title "Cheatsheet", search placeholder "Filter commands and plugins", flat
Core/Session/Tools list under a Commands/Plugins/Practices tab strip.
- Strong at: completeness; power users who already know the command name.
- Weak at: the confused user. It's a lookup table, not an answer.

### After · A — search-first
Reframes the field as intent ("What do you want to do?"), and on a query that
matches a curated intent, renders a **Suggested** block above the list: the command,
a one-line *why*, a docs anchor, and Copy. Label is honest — "curated shortcuts,
matched to your words" — because v1 is a static map, not a model.
- Strong at: the exact moment of confusion; the user's own example
  ("ask without interrupting the model" → `/btw` + why + source).
- Weak at: first open is still an empty field — a user who doesn't know what to
  type gets no help until they type.

### After · B — discover-first
Same mechanics as A, but the **open** state is a row of clickable intent chips
("Ask without interrupting the model", "Run something in the background", …)
above the full list. Clicking a chip runs the same suggestion path.
- Strong at: the zero-knowledge first open — the overwhelm case is the whole point.
- Weak at: chips are a fixed set; too many and it's just a different list.

## Head-to-head

| Dimension | Before | A · search-first | B · discover-first |
|---|---|---|---|
| First-open help | none | low | **high** |
| Answers "I want to…" | no | **yes** | yes |
| Guided toward a command | no | **yes** | yes |
| Risk of feeling like a switchboard | low | low | medium |
| Diff size vs published | — | small | small |
| Capability / disclosure delta | — | **none** | **none** |

**My take:** ship **B with A's result view** — i.e. the discover-first open state
(chips) that collapses into the search-first suggestion block once the user types.
It's one extra static array (`CHIPS`) over A, addresses the overwhelm goal at the
one moment that matters (first open), and stays capability-neutral. That is the
whole v1.

## Explicitly deferred (v2, separate, deliberate PR)
- `llm.oneshot` rerank + tl;dr → changes the disclosure line, adds cost/latency.
- `connectors.catalog` / `skills.manage` recommendations → extends the disclosure's
  enumerated list.
