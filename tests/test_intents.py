import json
from pathlib import Path

import pytest

import cheatsheet_intents as m

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "desktop_commands.json"


def _desktop_commands() -> set[str]:
    return set(json.loads(FIXTURE.read_text(encoding="utf-8"))["commands"])


def test_eval_suite_passes():
    failures = []
    for case in m.EVAL:
        got = m.match(case["q"])["cmds"]
        if case.get("none"):
            ok = got == []
        else:
            ok = all(name in got for name in case["cmds"])
        if not ok:
            failures.append((case["q"], got))
    assert not failures, failures


def test_unambiguous_queries_return_exactly_one_intent():
    cases = {
        "stop": ["stop"],
        "plan": ["plan"],
        "profile": ["profile"],
        "usage": ["usage"],
        "tools": ["tools"],
        "sessions": ["sessions"],
        "personality": ["personality"],
        "wake": ["wake"],
        "skills": ["skills"],
        "switch profile": ["profile"],
    }
    for query, expected in cases.items():
        assert m.match(query)["cmds"] == expected, (query, m.match(query)["cmds"])


def test_keys_match_on_word_boundaries_not_substrings():
    assert m.match("unstoppable progress")["cmds"] == []
    assert m.match("the machine stopped")["cmds"] == []
    assert m.match("explain the plan to me")["cmds"] == ["plan"]


def test_short_query_returns_nothing():
    assert m.match("") == {"cmds": []}
    assert m.match("ab") == {"cmds": []}


def test_union_preserves_intent_order_and_dedupes():
    assert m.match("ask a quick question without interrupting the model")["cmds"] == ["btw", "bg"]


def test_every_intent_command_is_desktop_visible():
    """Every curated id must be a command the desktop surface actually advertises.

    An id that is real but hidden (terminal/messaging/hidden) can never render, so
    the desktop would drop it silently. This is the guard for that class of bug.
    """
    visible = _desktop_commands()
    bad = sorted({name for intent in m.INTENTS for name in intent["cmds"] if name not in visible})
    assert not bad, f"curated ids not advertised on the desktop surface: {bad}"


def test_ids_are_bare_lowercase_names():
    for intent in m.INTENTS:
        assert intent["cmds"], intent
        for name in intent["cmds"]:
            assert name == name.lower() and " " not in name and not name.startswith("/"), name


def test_chips_are_labeled_and_carry_a_phrase():
    assert len(m.CHIPS) >= 5
    for chip in m.CHIPS:
        assert chip["label"] and chip["q"]


def test_fixture_matches_live_registry_when_available():
    """Drift detector: the committed snapshot must equal the live desktop-visible set.

    Skipped where hermes_cli is not importable (a bare plugin venv), so it runs on a
    machine with Hermes installed and goes stale loudly instead of silently.
    """
    C = pytest.importorskip("hermes_cli.commands")
    hidden = {"terminal", "messaging", "hidden"}
    live = sorted(
        cmd.name
        for cmd in C.COMMAND_REGISTRY
        if C.command_desktop_meta(cmd).get("desktop") not in hidden and not getattr(cmd, "gateway_only", False)
    )
    assert live == json.loads(FIXTURE.read_text(encoding="utf-8"))["commands"]
