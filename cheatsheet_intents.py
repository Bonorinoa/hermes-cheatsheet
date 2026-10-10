"""Curated intent map for the cheatsheet desktop plugin.

Data only: no network, no I/O. The desktop half asks the plugin route
(`GET /suggest`) which command ids a phrase maps to, then validates those ids
against the live ``commands.catalog`` before rendering. The cited passages shown
beside a suggestion come from the existing docs index (see ``cheatsheet_index``).

Every id here MUST be a command the *desktop* surface advertises. The catalog
hides commands whose ``desktop`` meta is terminal/messaging/hidden, so an id that
is real but hidden (``cron``, ``model``, ``clear``) can never render. The guard is
``tests/test_intents.py`` against ``tests/fixtures/desktop_commands.json``.
"""

from __future__ import annotations

from typing import Any

# phrase -> command ids. Every id is validated against the live catalog before render.
INTENTS: list[dict[str, Any]] = [
    {
        "keys": [
            "without interrupting",
            "side question",
            "quick question",
            "by the way",
            "interrupt the model",
            "while you work",
        ],
        "cmds": ["btw", "bg"],
    },
    {
        "keys": ["in the background", "background", "without blocking", "long job", "keep working", "asynchronously"],
        "cmds": ["bg"],
    },
    {"keys": ["add a skill", "reusable", "skill library", "automate a prompt"], "cmds": ["skills"]},
    {
        "keys": ["out of context", "too long", "compress", "compact", "save tokens", "context limit", "context window"],
        "cmds": ["compress", "context"],
    },
    {"keys": ["remember", "memory", "note that", "keep in mind"], "cmds": ["memory"]},
    {"keys": ["dark mode", "light mode", "change colors", "recolor", "theme", "skin"], "cmds": ["skin"]},
    {"keys": ["start fresh", "new conversation", "clear everything", "begin again", "fresh session"], "cmds": ["new"]},
    {"keys": ["voice", "dictate", "speech", "talk to it"], "cmds": ["voice"]},
    {"keys": ["resume", "pick up where", "previous session", "continue earlier"], "cmds": ["resume"]},
    {"keys": ["make it stop", "stop it", "stop that", "stop the", "interrupt it", "cancel", "halt", "abort", "stop"], "cmds": ["stop"]},
    {"keys": ["undo", "revert", "take that back"], "cmds": ["undo"]},
    {"keys": ["export", "save the conversation", "download transcript"], "cmds": ["export"]},
    {"keys": ["rename this", "name this session"], "cmds": ["title"]},
    {"keys": ["switch profile", "different profile", "change profile", "switch workspace"], "cmds": ["profile"]},
    {"keys": ["list sessions", "past conversations", "my sessions", "session history"], "cmds": ["sessions"]},
    {"keys": ["make a plan", "plan this", "plan mode", "draft a plan"], "cmds": ["plan"]},
    {"keys": ["change personality", "agent personality", "different personality"], "cmds": ["personality"]},
    {"keys": ["wake word", "hey hermes", "always listening"], "cmds": ["wake"]},
    {"keys": ["token usage", "how much have i used", "cost so far", "usage report"], "cmds": ["usage"]},
    {"keys": ["what tools", "list tools", "available tools"], "cmds": ["tools"]},
]

# Opening prompts. `q` is the phrase a click types into the field.
CHIPS: list[dict[str, str]] = [
    {"label": "Ask without interrupting the model", "q": "ask a question without interrupting the model"},
    {"label": "Run something in the background", "q": "run this in the background"},
    {"label": "Schedule a recurring job", "q": "schedule a recurring job"},
    {"label": "The conversation is getting long", "q": "the conversation is getting too long"},
    {"label": "Add a reusable skill", "q": "add a reusable skill"},
    {"label": "Make everything dark", "q": "make everything dark mode"},
    {"label": "Switch profile", "q": "switch profile"},
    {"label": "Connect Gmail or Notion", "q": "connect my gmail"},
    {"label": "Hot-reload a plugin I am editing", "q": "hot reload a plugin"},
    {"label": "Don't break the prompt cache", "q": "how do I not break the prompt cache"},
]

# Eval suite: query -> command ids that MUST appear (or `none`). Regression guard.
EVAL: list[dict[str, Any]] = [
    {"q": "ask a quick question without interrupting the model", "cmds": ["btw", "bg"]},
    {"q": "run this in the background", "cmds": ["bg"]},
    {"q": "the context is getting too long", "cmds": ["compress"]},
    {"q": "add a reusable skill", "cmds": ["skills"]},
    {"q": "make everything dark mode", "cmds": ["skin"]},
    {"q": "start a new conversation", "cmds": ["new"]},
    {"q": "turn on voice input", "cmds": ["voice"]},
    {"q": "resume my previous session", "cmds": ["resume"]},
    {"q": "make it stop", "cmds": ["stop"]},
    {"q": "stop", "cmds": ["stop"]},
    {"q": "undo that", "cmds": ["undo"]},
    {"q": "rename this", "cmds": ["title"]},
    {"q": "switch profile", "cmds": ["profile"]},
    {"q": "how much have I used", "cmds": ["usage"]},
    {"q": "what tools do I have", "cmds": ["tools"]},
    {"q": "xyzzy frobnicate the widget", "none": True},
]


def match(query: str) -> dict[str, list[str]]:
    """Rank intents by their longest matched phrase; ties broken by match count."""
    needle = (query or "").strip().lower()
    out: dict[str, list[str]] = {"cmds": []}
    if len(needle) < 4:
        return out
    scored = []
    for intent in INTENTS:
        matched = [key for key in intent["keys"] if key in needle]
        if matched:
            scored.append((max(len(key) for key in matched), len(matched), intent))
    scored.sort(key=lambda row: (-row[0], -row[1]))
    for _, _, intent in scored[:3]:
        for name in intent["cmds"]:
            if name not in out["cmds"]:
                out["cmds"].append(name)
    return out
