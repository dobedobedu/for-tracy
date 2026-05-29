from collections import Counter


def build_transition_summary(transitions: list[dict]) -> list[dict]:
    """Group transitions by from_status -> to_status and count occurrences.

    Returns list sorted by count descending.
    """
    pairs = [(t["from_status"], t["to_status"]) for t in transitions]
    counts = Counter(pairs)
    return [
        {"from": f, "to": t, "count": c}
        for (f, t), c in counts.most_common()
    ]
