import pytest
from store.sqlite_store import SQLiteStore


@pytest.fixture
def store():
    s = SQLiteStore(":memory:")
    s.initialize()
    return s


def test_get_empty_street_map(store):
    assert store.get_street_community_map() == {}


def test_upsert_single_street(store):
    store.upsert_street_community("Anthirium Loop", "Windward")
    m = store.get_street_community_map()
    assert m == {"ANTHIRIUM LOOP": ["Windward"]}


def test_upsert_same_pair_is_idempotent(store):
    store.upsert_street_community("Anthirium Loop", "Windward")
    store.upsert_street_community("Anthirium Loop", "Windward")
    m = store.get_street_community_map()
    assert m == {"ANTHIRIUM LOOP": ["Windward"]}


def test_multi_community_street(store):
    store.upsert_street_community("Blue Shell Loop", "Shellstone")
    store.upsert_street_community("Blue Shell Loop", "Wild Blue")
    m = store.get_street_community_map()
    assert set(m["BLUE SHELL LOOP"]) == {"Shellstone", "Wild Blue"}


def test_list_street_communities(store):
    store.upsert_street_community("Anthirium Loop", "Windward")
    store.upsert_street_community("Blue Shell Loop", "Shellstone")
    rows = store.list_street_communities()
    assert len(rows) == 2
    by_id = {r.community_name: r for r in rows}
    assert by_id["Windward"].street_name == "Anthirium Loop"
    assert by_id["Shellstone"].street_name == "Blue Shell Loop"


def test_delete_street_community(store):
    store.upsert_street_community("Anthirium Loop", "Windward")
    rows = store.list_street_communities()
    target_id = rows[0].id
    store.delete_street_community(target_id)
    assert store.get_street_community_map() == {}


def test_replace_all_street_communities(store):
    store.upsert_street_community("Old Street", "Old Community")
    store.replace_all_street_communities([
        ("New Street 1", "New Community A"),
        ("New Street 2", "New Community B"),
    ])
    m = store.get_street_community_map()
    assert m == {"NEW STREET 1": ["New Community A"], "NEW STREET 2": ["New Community B"]}
