import json
from pathlib import Path

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
