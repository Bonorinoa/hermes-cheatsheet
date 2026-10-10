"""Curated intent map for the cheatsheet desktop plugin.

Data only: no network, no I/O. The desktop half asks the plugin route
(`GET /suggest`) which command ids a phrase maps to, then validates those ids
against the live ``commands.catalog`` before rendering. The cited passages shown
beside a suggestion come from the existing docs index (see ``cheatsheet_index``).
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
    {
        "keys": ["schedule", "recurring", "every day", "remind me", "cron job", "daily", "weekly"],
        "cmds": ["cron"],
    },
    {"keys": ["add a skill", "reusable", "skill library", "automate a prompt"], "cmds": ["skills"]},
    {
        "keys": ["change model", "switch model", "smarter model", "cheaper model", "different model", "stronger model"],
        "cmds": ["model"],
    },
    {
        "keys": ["out of context", "too long", "compress", "save tokens", "context limit", "running out of", "context window"],
        "cmds": ["compact", "context"],
    },
    {"keys": ["remember", "memory", "note that", "keep in mind"], "cmds": ["memory"]},
    {"keys": ["dark mode", "light mode", "change colors", "recolor", "theme", "skin"], "cmds": ["skin", "theme"]},
    {"keys": ["run a command", "shell", "terminal", "on my machine"], "cmds": ["shell"]},
    {"keys": ["attach a file", "upload", "send a file", "add a document"], "cmds": ["attach", "pdf", "image"]},
    {"keys": ["start fresh", "new conversation", "clear everything", "begin again"], "cmds": ["new", "clear"]},
    {"keys": ["voice", "dictate", "speech", "talk to it"], "cmds": ["voice"]},
    {"keys": ["resume", "pick up where", "previous session", "continue earlier"], "cmds": ["resume"]},
    {"keys": ["interrupt it", "cancel", "stop it", "abort", "stop that", "stop the"], "cmds": ["stop"]},
    {"keys": ["undo", "revert", "take that back"], "cmds": ["undo"]},
    {"keys": ["export", "save the conversation", "download transcript"], "cmds": ["export"]},
    {"keys": ["rename this", "name this session"], "cmds": ["title"]},
]

# Opening prompts. `q` is the phrase a click types into the field.
CHIPS: list[dict[str, str]] = [
    {"label": "Ask without interrupting the model", "q": "ask a question without interrupting the model"},
    {"label": "Run something in the background", "q": "run this in the background"},
    {"label": "Schedule a recurring job", "q": "schedule a recurring job"},
    {"label": "Switch to a cheaper model", "q": "switch to a cheaper model"},
    {"label": "The conversation is getting long", "q": "the conversation is getting too long"},
    {"label": "Add a reusable skill", "q": "add a reusable skill"},
    {"label": "Connect Gmail or Notion", "q": "connect my gmail"},
    {"label": "Hot-reload a plugin I am editing", "q": "hot reload a plugin"},
    {"label": "Delegate this to parallel agents", "q": "delegate this to parallel agents"},
    {"label": "Don't break the prompt cache", "q": "how do I not break the prompt cache"},
]

# Eval suite: query -> command ids that MUST appear (or `none`). Regression guard.
EVAL: list[dict[str, Any]] = [
    {"q": "ask a quick question without interrupting the model", "cmds": ["btw", "bg"]},
    {"q": "run this in the background", "cmds": ["bg"]},
    {"q": "schedule a daily reminder", "cmds": ["cron"]},
    {"q": "the context is getting too long", "cmds": ["compact"]},
    {"q": "switch to a cheaper model", "cmds": ["model"]},
    {"q": "add a reusable skill", "cmds": ["skills"]},
    {"q": "make everything dark mode", "cmds": ["skin", "theme"]},
    {"q": "run a command on my machine", "cmds": ["shell"]},
    {"q": "resume my previous session", "cmds": ["resume"]},
    {"q": "turn on voice input", "cmds": ["voice"]},
    {"q": "start a new conversation", "cmds": ["new", "clear"]},
    {"q": "upload a pdf", "cmds": ["attach", "pdf", "image"]},
    {"q": "undo that", "cmds": ["undo"]},
    {"q": "rename this", "cmds": ["title"]},
    {"q": "xyzzy frobnicate the widget", "none": True},
]


def match(query: str) -> dict[str, list[str]]:
    """Rank intents by the longest contained phrase; union the top three."""
    needle = (query or "").strip().lower()
    out: dict[str, list[str]] = {"cmds": []}
    if len(needle) < 4:
        return out
    scored = []
    for intent in INTENTS:
        score = sum(len(key) + 2 for key in intent["keys"] if key in needle)
        if score:
            scored.append((score, intent))
    scored.sort(key=lambda row: -row[0])
    for _, intent in scored[:3]:
        for name in intent["cmds"]:
            if name not in out["cmds"]:
                out["cmds"].append(name)
    return out
