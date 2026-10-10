import cheatsheet_intents as m


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


def test_every_intent_command_is_a_plausible_slash_name():
    for intent in m.INTENTS:
        assert intent["cmds"], intent
        for name in intent["cmds"]:
            assert name == name.lower() and " " not in name


def test_chips_are_labeled_and_carry_a_phrase():
    assert len(m.CHIPS) >= 5
    for chip in m.CHIPS:
        assert chip["label"] and chip["q"]
