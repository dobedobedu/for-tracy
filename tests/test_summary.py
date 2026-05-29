from engine.summary import build_transition_summary


def test_groups_transitions_and_counts():
    transitions = [
        {"from_status": "Submitted", "to_status": "Plan Review"},
        {"from_status": "Submitted", "to_status": "Plan Review"},
        {"from_status": "Plan Review", "to_status": "Ready to Issue"},
        {"from_status": "Pending", "to_status": "Closed - Complete"},
    ]

    summary = build_transition_summary(transitions)
    assert summary == [
        {"from": "Submitted", "to": "Plan Review", "count": 2},
        {"from": "Plan Review", "to": "Ready to Issue", "count": 1},
        {"from": "Pending", "to": "Closed - Complete", "count": 1},
    ]


def test_empty_transitions():
    assert build_transition_summary([]) == []


def test_single_transition():
    transitions = [{"from_status": "Submitted", "to_status": "Plan Review"}]
    assert build_transition_summary(transitions) == [
        {"from": "Submitted", "to": "Plan Review", "count": 1}
    ]
