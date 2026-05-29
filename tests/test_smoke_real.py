import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from engine.orchestrator import ingest_csv
from engine.parser import ScopeFilter
from store.sqlite_store import SQLiteStore

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
MARCH3_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "3.3.26_Raw_RecordList20260302 (1).csv")
MARCH16_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "3.16.26_Raw RecordList20260316.csv")


@pytest.mark.skipif(not os.path.exists(MARCH3_FILE), reason="Real data files not available")
class TestSmokeRealData:
    def test_ingest_march3_baseline(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter()

        with open(MARCH3_FILE, "rb") as f:
            content = f.read()

        result = ingest_csv(content, "march3.csv", store, scope)

        assert result.row_count_raw > 2000
        assert result.row_count_after_scope > 0
        assert result.new_permits > 0
        assert result.status_changes == 0
        assert result.observation_count == result.row_count_after_scope

        permits = store.get_current_statuses()
        assert len(permits) == result.new_permits

    def test_ingest_march3_then_march16(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter()

        with open(MARCH3_FILE, "rb") as f:
            content1 = f.read()
        r1 = ingest_csv(content1, "march3.csv", store, scope)
        assert r1.new_permits > 0

        with open(MARCH16_FILE, "rb") as f:
            content2 = f.read()
        r2 = ingest_csv(content2, "march16.csv", store, scope)

        assert r2.rows_dropped_by_scope > 0
        assert r2.row_count_after_scope > 0

        assert r2.status_changes >= 10
        assert r2.status_changes <= 500

        assert r2.new_permits >= 0

        assert r2.observation_count == r2.row_count_after_scope

        changes = store.get_latest_changes(r2.upload_id)
        assert len(changes) == r2.status_changes

        tracked = [c for c in changes if c.is_tracked_milestone]
        assert len(tracked) > 0

        permits = store.get_current_statuses()
        assert len(permits) > r1.new_permits

    def test_timeline_after_real_ingest(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter()

        with open(MARCH3_FILE, "rb") as f:
            ingest_csv(f.read(), "march3.csv", store, scope)
        with open(MARCH16_FILE, "rb") as f:
            ingest_csv(f.read(), "march16.csv", store, scope)

        permits = store.get_all_permits()
        assert len(permits) > 0

        sample = permits[0]
        timeline = store.get_timeline(sample.record_number)
        assert len(timeline) >= 1
