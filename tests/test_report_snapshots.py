"""Regression fixtures derived from the verified October permit cases.

These are reduced CSV fixtures, not a replay of the unavailable raw exports.
All writes are isolated in-memory test data.
"""
import csv
import io
import os
import uuid
from dataclasses import asdict
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault('DATABASE_URL', ':memory:')
from server import app as api
from engine.comparison import compare_reports
from engine.orchestrator import ingest_csv
from engine.parser import normalize_street_community_map, resolve_community
from store.sqlite_store import SQLiteStore
from store.postgres_store import PostgresStore


@pytest.fixture(params=['sqlite', 'postgres'])
def fixture_store(request):
    if request.param == 'sqlite':
        s = SQLiteStore(':memory:')
        s.initialize()
        yield s
        s.close()
        return
    dsn = os.environ.get('TRACY_TEST_POSTGRES_URL')
    if not dsn:
        pytest.skip('Set TRACY_TEST_POSTGRES_URL for disposable local PostgreSQL regressions')
    assert urlparse(dsn).hostname in ('127.0.0.1', 'localhost'), 'Only a local fixture database is allowed'
    from psycopg2 import sql
    s = PostgresStore(dsn)
    schema = 'permit_fixture_' + uuid.uuid4().hex
    conn = s._get_conn()
    with conn.cursor() as cur:
        cur.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        cur.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(schema)))
    conn.commit()
    s.initialize()
    try:
        yield s
    finally:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
        conn.commit()
        s.close()


def set_legacy_field(s, column, value, record_number):
    assert column in ('first_seen_date', 'community')
    conn = s._get_conn()
    if isinstance(s, SQLiteStore):
        conn.execute(f'UPDATE permits SET {column} = ? WHERE record_number = ?', (value, record_number))
    else:
        with conn.cursor() as cur:
            cur.execute(f'UPDATE permits SET {column} = %s WHERE record_number = %s', (value, record_number))
    conn.commit()


NEW = [
    ('RES-NEW-26-001577', '2429 WATERFRONT Cir'),
    ('RES-NEW-26-001576', '8040 SCARLETBUSH Dr'),
    ('RES-NEW-26-001581', '10088 LADDER HORN Dr'),
    ('RES-NEW-26-001579', '113 BLUE MIST Way'),
    ('RES-NEW-26-001578', '217 BLUE PEARL Ct'),
]
VILLAS = [
    ('RES-NEW-25-002188', '*PP*9536 LUNAR DOVE Dr'),
    ('RES-NEW-25-002187', '*PP*9532 LUNAR DOVE Dr'),
    ('RES-NEW-25-002186', '*PP*9545 LUNAR DOVE Dr'),
    ('RES-NEW-25-002163', '*PP* 9541 LUNAR DOVE Dr'),
]
CORMACK = [
    ('RES-NEW-24-001348', '9081 CORMACK Ln', 'Closed - Complete'),
    ('RES-NEW-24-001349', '9085 CORMACK Ln', 'Closed - Complete'),
    ('RES-NEW-24-001518', '9089 CORMACK Ln', 'Closed - Complete'),
    ('RES-NEW-24-001351', '9093 CORMACK Ln', 'Closed - Complete'),
    ('RES-NEW-26-000394', '9092 CORMACK Ln', 'Closed - Complete'),
    ('RES-NEW-24-001544', '9088 CORMACK Ln', 'Inspection Phase'),
    ('RES-NEW-26-000395', '9084 CORMACK Ln', 'Inspection Phase'),
    ('RES-NEW-26-000229', '9080 CORMACK Ln', 'Ready to Issue'),
]


def csv_bytes(rows):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['Date', 'Record Number', 'Record Type', 'Description', 'Project Name', 'Status'])
    for rn, address, status, date in rows:
        w.writerow([date, rn, 'Residential New Construction Permit', 'Reduced regression fixture', address + ', Sarasota, FL 34240', status])
    return out.getvalue().encode()


def flatten(board):
    return {p['record_number']: p for c in board['columns'] for p in c['permits']}


@pytest.fixture
def reports(monkeypatch, fixture_store):
    s = fixture_store
    for street, community in [('COMACK', 'Bungalow Walk'), ('Lunar Dove Drive', 'Shellstone'), ('BLUE SHELL', 'Shellstone'), ('BLUE SHELL', 'Wild Blue')]:
        s.upsert_street_community(street, community)
    baseline = [(rn, a, 'Ready to Issue', '9/25/2026') for rn, a in VILLAS]
    baseline += [(rn, a, status, '9/25/2026') for rn, a, status in CORMACK]
    baseline += [('SYN-OVERLAP', '1031 BLUE SHELL Loop', 'Inspection Phase', '9/25/2026')]
    target = [(rn, a, 'Inspection Phase', '9/25/2026') for rn, a in VILLAS]
    target += baseline[4:]
    target += [(rn, a, 'Plan Review', '9/29/2026') for rn, a in NEW]
    ingest_csv(csv_bytes(baseline), 'RecordList20260925.csv', s)
    ingest_csv(csv_bytes(target), 'RecordList20261001.csv', s)
    # Reproduce old persisted fields; the GET fixes must not rewrite them.
    for rn, a in NEW:
        set_legacy_field(s, 'first_seen_date', '2026-09-29', rn)
    for rn, a in VILLAS:
        set_legacy_field(s, 'community', a.rsplit(' ', 1)[0], rn)
    for rn, a, status in CORMACK:
        set_legacy_field(s, 'community', 'CORMACK', rn)
    monkeypatch.setattr(api, 'store', s)
    with TestClient(api.app) as client:
        yield s, client, baseline, target


def test_named_new_applications_share_board_and_summary_newness(reports):
    s, client, _, _ = reports
    cmp = client.get('/api/compare?from_date=2026-09-25&to_date=2026-10-01').json()
    board = client.get('/api/kanban?from_date=2026-09-25&report_date=2026-10-01').json()
    cards = flatten(board)
    new_ids = {t['record_number'] for t in cmp['transitions'] if t['is_new']}
    assert new_ids == {rn for rn, _ in NEW}
    for rn in new_ids:
        assert cards[rn]['changed'] and cards[rn]['change_info']['is_new']
        assert cards[rn]['first_seen_date'] == '2026-10-01'
    assert {rn for rn, p in cards.items() if p['changed']} == {t['record_number'] for t in cmp['transitions']}
    assert s.get_current_statuses()[NEW[0][0]].first_seen_date == '2026-09-29'


def test_villa_transitions_and_cormack_membership_are_correct_without_writes(reports):
    s, client, _, _ = reports
    before = {rn: asdict(p) for rn, p in s.get_current_statuses().items()}
    shell = flatten(client.get('/api/kanban?community=Shellstone&from_date=2026-09-25&report_date=2026-10-01').json())
    bungalow = flatten(client.get('/api/kanban?community=Bungalow%20Walk&report_date=2026-10-01').json())
    for rn, address in VILLAS:
        assert shell[rn]['address'] == address
        assert shell[rn]['current_status'] == 'Inspection Phase'
        assert shell[rn]['change_info']['from_status'] == 'Ready to Issue'
    assert set(bungalow) == {rn for rn, _, _ in CORMACK}
    communities = client.get('/api/communities?to_date=2026-10-01').json()['communities']
    assert next(c for c in communities if c['name'] == 'Bungalow Walk')['count'] == 8
    after = {rn: asdict(p) for rn, p in s.get_current_statuses().items()}
    assert before == after


def test_historical_membership_status_and_community_counts(reports):
    _, client, baseline, _ = reports
    cards = flatten(client.get('/api/kanban?report_date=2026-09-25').json())
    assert set(cards) == {r[0] for r in baseline}
    for rn, _ in VILLAS:
        assert cards[rn]['current_status'] == 'Ready to Issue'
        assert not cards[rn]['changed']
    comms = client.get('/api/communities?to_date=2026-09-25').json()['communities']
    assert sum(p['record_number'] in {rn for rn, _ in NEW} for c in comms for p in c['permits']) == 0


def test_repeated_upload_and_out_of_order_backfill_keep_same_view(reports):
    s, client, baseline, target = reports
    initial = client.get('/api/compare?from_date=2026-09-25&to_date=2026-10-01').json()['transitions']
    ingest_csv(csv_bytes(target), 'RecordList20261001.csv', s)
    ingest_csv(csv_bytes([(rn, a, 'Plan Review', date) for rn, a, _, date in baseline]), 'RecordList20260920.csv', s)
    explicit = client.get('/api/kanban?from_date=2026-09-25&report_date=2026-10-01').json()
    default = client.get('/api/kanban').json()
    assert explicit['latest_upload']['report_date'] == default['latest_upload']['report_date'] == '2026-10-01'
    assert flatten(explicit) == flatten(default)
    assert client.get('/api/compare?from_date=2026-09-25&to_date=2026-10-01').json()['transitions'] == initial
    assert all(s.get_current_statuses()[rn].current_status == 'Inspection Phase' for rn, _ in VILLAS)
    assert {p['record_number'] for c in client.get('/api/communities?only_changed=true').json()['communities'] for p in c['permits']} == {t['record_number'] for t in initial}


def test_failed_revision_does_not_publish_partial_snapshot(reports, monkeypatch):
    s, client, _, target = reports
    before_uploads = [asdict(u) for u in s.get_upload_history()]
    before_permits = {rn: asdict(p) for rn, p in s.get_current_statuses().items()}
    before_board = client.get('/api/kanban').json()
    append = s.append_observation
    count = 0

    def fail_during_import(observation):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError('Injected fixture storage failure')
        append(observation)

    monkeypatch.setattr(s, 'append_observation', fail_during_import)
    with pytest.raises(RuntimeError, match='Injected fixture'):
        ingest_csv(csv_bytes([(rn, a, 'Plan Review', date) for rn, a, _, date in target]), 'RecordList20261001.csv', s)
    assert [asdict(u) for u in s.get_upload_history()] == before_uploads
    assert {rn: asdict(p) for rn, p in s.get_current_statuses().items()} == before_permits
    assert client.get('/api/kanban').json() == before_board


def test_shared_street_remains_in_both_communities_and_known_omission_is_not_new(reports):
    s, client, baseline, target = reports
    for community in ['Shellstone', 'Wild Blue']:
        assert 'SYN-OVERLAP' in flatten(client.get('/api/kanban', params={'community': community}).json())
    # An incomplete intervening export must not invent a new application.
    ingest_csv(csv_bytes([r for r in baseline if r[0] != 'SYN-OVERLAP']), 'RecordList20260927.csv', s)
    cmp = compare_reports(s, '2026-09-27', '2026-10-01')
    assert not any(t['record_number'] == 'SYN-OVERLAP' for t in cmp['transitions'])


def test_selected_range_includes_change_before_latest_upload(reports):
    s, client, _, target = reports
    ingest_csv(csv_bytes(target), 'RecordList20261002.csv', s)
    cmp = client.get('/api/compare?from_date=2026-09-25&to_date=2026-10-02').json()
    board = flatten(client.get('/api/kanban?from_date=2026-09-25&report_date=2026-10-02').json())
    assert {rn for rn, p in board.items() if p['changed']} == {t['record_number'] for t in cmp['transitions']}
    assert all(board[rn]['changed'] for rn, _ in VILLAS + NEW)


@pytest.mark.parametrize('address', ['*PP*9536 LUNAR DOVE Dr', '*PP* 9541 LUNAR DOVE Dr', '**PP* 9504 Lunar Dove CT Sarasota Fl 34240 - Lot 659'])
def test_prefix_forms_and_reference_alias(address):
    mapping = normalize_street_community_map({'Lunar Dove Drive': ['Shellstone'], 'COMACK': ['Bungalow Walk', 'Another community']})
    assert resolve_community(address, mapping) == 'Shellstone'
    assert resolve_community('9085 CORMACK Ln', mapping) == 'Bungalow Walk'
    assert resolve_community('1 UNKNOWN St', mapping) == 'UNKNOWN'


def test_missing_and_reversed_report_ranges_are_rejected(reports):
    _, client, _, _ = reports
    assert client.get('/api/kanban?report_date=2020-01-01').status_code == 404
    assert client.get('/api/kanban?from_date=2026-10-01&report_date=2026-09-25').status_code == 400
