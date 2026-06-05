from engine.parser import resolve_community, extract_community


def test_extract_community_unchanged():
    assert extract_community("8504 ANTHIRIUM Loop, Sarasota, FL 34240") == "ANTHIRIUM"
    assert extract_community("240 BLUE MIST Way, Sarasota, FL 34240") == "BLUE MIST"


def test_resolve_community_from_map_match():
    m = {"ANTHIRIUM": ["Windward"], "BLUE MIST": ["Wild Blue"]}
    assert resolve_community("8504 ANTHIRIUM Loop, Sarasota, FL 34240", m) == "Windward"
    assert resolve_community("240 BLUE MIST Way, Sarasota, FL 34240", m) == "Wild Blue"


def test_resolve_community_case_insensitive():
    # Map keys are uppercased by the store; resolve_community uppercases the
    # heuristic street portion before lookup.
    m = {"ANTHIRIUM": ["Windward"]}
    assert resolve_community("8504 anthirium Loop, Sarasota, FL 34240", m) == "Windward"


def test_resolve_community_falls_back_to_heuristic():
    m = {"ANTHIRIUM": ["Windward"]}
    assert resolve_community("8504 SOMETHING_NEW Loop, Sarasota, FL 34240", m) == "SOMETHING_NEW"


def test_resolve_community_no_map_uses_heuristic():
    assert resolve_community("8504 ANTHIRIUM Loop, Sarasota, FL 34240", None) == "ANTHIRIUM"
    assert resolve_community("8504 ANTHIRIUM Loop, Sarasota, FL 34240", {}) == "ANTHIRIUM"


def test_resolve_community_multi_community_joined():
    m = {"BLUE SHELL": ["Shellstone", "Wild Blue"]}
    assert resolve_community("1031 BLUE SHELL Loop, Sarasota, FL 34240", m) == "Shellstone | Wild Blue"
