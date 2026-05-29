import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pandas as pd

from engine.parser import parse_date, parse_address, parse_row, parse_csv, ScopeFilter
from engine.status import get_milestone, Milestone, is_backward_move, is_tracked_transition, STATUS_TO_MILESTONE
from engine.diff import detect_changes
from engine.orchestrator import ingest_csv
from engine.mock_data import generate_mock_data, snapshot_to_csv
from store.sqlite_store import SQLiteStore


class TestParseNormalizesDates:
    def test_standard_format(self):
        assert parse_date("2/27/2026") == "2026-02-27"

    def test_single_digit_month_day(self):
        assert parse_date("1/5/2026") == "2026-01-05"

    def test_double_digit(self):
        assert parse_date("12/31/2026") == "2026-12-31"

    def test_already_iso(self):
        assert parse_date("2026-03-15") == "2026-03-15"

    def test_whitespace_trimmed(self):
        assert parse_date("  3/1/2026  ") == "2026-03-01"


class TestParseStripsAddressSuffix:
    def test_trailing_colon_space(self):
        addr, csz = parse_address("1579 RUNNING TIDE Pl,  Sarasota, FL 34240 :")
        assert addr == "1579 RUNNING TIDE Pl"
        assert csz == "Sarasota, FL 34240"

    def test_double_spaces_normalized(self):
        addr, csz = parse_address("100  MAIN  ST,  Sarasota,  FL  34240 :")
        assert "  " not in addr
        assert "  " not in csz

    def test_no_suffix(self):
        addr, csz = parse_address("100 MAIN ST, Sarasota, FL 34240")
        assert addr == "100 MAIN ST"
        assert csz == "Sarasota, FL 34240"

    def test_no_comma(self):
        addr, csz = parse_address("100 MAIN ST")
        assert addr == "100 MAIN ST"
        assert csz == ""


class TestStatusMapsToCorrectMilestone:
    def test_all_known_statuses_mapped(self):
        expected = {
            "Submitted": Milestone.APPLICATION_REVIEW,
            "In Review": Milestone.APPLICATION_REVIEW,
            "Plan Review": Milestone.APPLICATION_REVIEW,
            "Revisions Required": Milestone.APPLICATION_REVIEW,
            "Additional Info Required": Milestone.APPLICATION_REVIEW,
            "Pending": Milestone.PENDING_NO_ISSUES,
            "Ready to Issue": Milestone.READY_TO_ISSUE,
            "Inspection Phase": Milestone.PERMIT_ISSUED,
            "Pending CO": Milestone.PENDING_CO,
            "TCO Issued": Milestone.TCO_ISSUED,
            "Closed - Complete": Milestone.CLOSED,
            "Closed - Approved": Milestone.CLOSED,
            "Closed - Issued": Milestone.CLOSED,
            "Closed - Withdrawn": Milestone.CLOSED,
            "Permit Expired": Milestone.PERMIT_EXPIRED,
        }
        for status, expected_ms in expected.items():
            assert get_milestone(status) == expected_ms, f"{status} should map to {expected_ms}"

    def test_unknown_status_returns_unrecognized(self):
        assert get_milestone("Some New Status") == Milestone.UNRECOGNIZED


class TestUnrecognizedStatusIsFlaggedNotDropped:
    def test_unrecognized_flagged(self):
        row = pd.Series({
            "Date": "3/1/2026",
            "Record Number": "RES-NEW-26-000001",
            "Record Type": "Residential New Construction Permit",
            "Description": "Test",
            "Project Name": "100 MAIN ST, Sarasota, FL 34240 :",
            "Status": "Future New Status",
            "Short Notes": "",
        })
        parsed = parse_row(row)
        assert parsed.is_unrecognized_status is True
        assert parsed.milestone == Milestone.UNRECOGNIZED

    def test_recognized_not_flagged(self):
        row = pd.Series({
            "Date": "3/1/2026",
            "Record Number": "RES-NEW-26-000001",
            "Record Type": "Residential New Construction Permit",
            "Description": "Test",
            "Project Name": "100 MAIN ST, Sarasota, FL 34240 :",
            "Status": "Submitted",
            "Short Notes": "",
        })
        parsed = parse_row(row)
        assert parsed.is_unrecognized_status is False


class TestScopeFilterExcludesOutOfScopeRows:
    def test_filters_by_record_type(self):
        df = pd.DataFrame([
            {"Date": "3/1/2026", "Record Number": "R1", "Record Type": "Residential New Construction Permit",
             "Description": "", "Project Name": "100 MAIN ST, Sarasota, FL 34240 :", "Status": "Submitted", "Short Notes": ""},
            {"Date": "3/1/2026", "Record Number": "R2", "Record Type": "Residential Pool/Spa Permit",
             "Description": "", "Project Name": "200 OAK ST, Sarasota, FL 34240 :", "Status": "Pending", "Short Notes": ""},
        ])
        scope = ScopeFilter(record_type="Residential New Construction Permit", zip_codes=[])
        filtered, dropped = parse_csv(df, scope)
        assert len(filtered) == 1
        assert filtered[0].record_number == "R1"
        assert dropped == 1

    def test_filters_by_zip(self):
        df = pd.DataFrame([
            {"Date": "3/1/2026", "Record Number": "R1", "Record Type": "Residential New Construction Permit",
             "Description": "", "Project Name": "100 MAIN ST, Sarasota, FL 34240 :", "Status": "Submitted", "Short Notes": ""},
            {"Date": "3/1/2026", "Record Number": "R2", "Record Type": "Residential New Construction Permit",
             "Description": "", "Project Name": "200 OAK ST, Sarasota, FL 34241 :", "Status": "Pending", "Short Notes": ""},
        ])
        scope = ScopeFilter(zip_codes=["34240"])
        filtered, dropped = parse_csv(df, scope)
        assert len(filtered) == 1
        assert dropped == 1


class TestNewPermitDetected:
    def test_new_permit(self):
        store = SQLiteStore()
        store.initialize()
        csv_content = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv_content += '3/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Submitted,\n'
        result = ingest_csv(csv_content, "test.csv", store, ScopeFilter(zip_codes=["34240"]))
        assert result.new_permits == 1
        assert result.status_changes == 0
        permits = store.get_current_statuses()
        assert "RES-NEW-26-000001" in permits


class TestStatusChangeDetectedWithFromAndTo:
    def test_change_detected(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter(zip_codes=["34240"])

        csv1 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv1 += '2/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Submitted,\n'
        ingest_csv(csv1, "snap1.csv", store, scope)

        csv2 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv2 += '3/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Inspection Phase,\n'
        result = ingest_csv(csv2, "snap2.csv", store, scope)

        assert result.status_changes == 1
        changes = store.get_latest_changes(result.upload_id)
        assert len(changes) == 1
        assert changes[0].from_status == "Submitted"
        assert changes[0].to_status == "Inspection Phase"


class TestUnchangedPermitProducesObservationButNoChange:
    def test_unchanged(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter(zip_codes=["34240"])

        csv1 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv1 += '2/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Submitted,\n'
        ingest_csv(csv1, "snap1.csv", store, scope)

        csv2 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv2 += '3/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Submitted,\n'
        result = ingest_csv(csv2, "snap2.csv", store, scope)

        assert result.status_changes == 0
        assert result.unchanged == 1
        timeline = store.get_timeline("RES-NEW-26-000001")
        assert len(timeline) == 2


class TestBackwardMoveFlagged:
    def test_backward(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter(zip_codes=["34240"])

        csv1 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv1 += '2/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Inspection Phase,\n'
        ingest_csv(csv1, "snap1.csv", store, scope)

        csv2 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv2 += '3/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Revisions Required,\n'
        result = ingest_csv(csv2, "snap2.csv", store, scope)

        assert result.backward_moves == 1
        changes = store.get_latest_changes(result.upload_id)
        assert changes[0].is_backward is True


class TestDisappearedPermitFlaggedNotDeleted:
    def test_disappeared(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter(zip_codes=["34240"])

        csv1 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv1 += '2/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Submitted,\n'
        csv1 += '2/1/2026,RES-NEW-26-000002,Residential New Construction Permit,Test,"200 OAK ST, Sarasota, FL 34240 :",Pending,\n'
        ingest_csv(csv1, "snap1.csv", store, scope)

        csv2 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv2 += '3/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Submitted,\n'
        result = ingest_csv(csv2, "snap2.csv", store, scope)

        assert result.disappeared == 1
        permits = store.get_current_statuses()
        assert "RES-NEW-26-000002" in permits


class TestTrackedMilestoneTransitionsFlagged:
    def test_permit_issued(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter(zip_codes=["34240"])

        csv1 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv1 += '2/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Ready to Issue,\n'
        ingest_csv(csv1, "snap1.csv", store, scope)

        csv2 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv2 += '3/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Inspection Phase,\n'
        result = ingest_csv(csv2, "snap2.csv", store, scope)

        assert result.tracked_milestone_hits == 1
        changes = store.get_latest_changes(result.upload_id)
        assert changes[0].is_tracked_milestone is True

    def test_co_pending(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter(zip_codes=["34240"])

        csv1 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv1 += '2/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Inspection Phase,\n'
        ingest_csv(csv1, "snap1.csv", store, scope)

        csv2 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv2 += '3/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Pending CO,\n'
        result = ingest_csv(csv2, "snap2.csv", store, scope)

        assert result.tracked_milestone_hits == 1

    def test_co_issued(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter(zip_codes=["34240"])

        csv1 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv1 += '2/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Pending CO,\n'
        ingest_csv(csv1, "snap1.csv", store, scope)

        csv2 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv2 += '3/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Closed - Complete,\n'
        result = ingest_csv(csv2, "snap2.csv", store, scope)

        assert result.tracked_milestone_hits == 1


class TestObservationCountInvariant:
    def test_every_scoped_row_gets_one_observation(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter(zip_codes=["34240"])

        csv1 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv1 += '2/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Submitted,\n'
        csv1 += '2/1/2026,RES-NEW-26-000002,Residential New Construction Permit,Test,"200 OAK ST, Sarasota, FL 34240 :",Pending,\n'
        csv1 += '2/1/2026,RES-NEW-26-000003,Residential New Construction Permit,Test,"300 ELM ST, Sarasota, FL 34240 :",Plan Review,\n'
        r1 = ingest_csv(csv1, "snap1.csv", store, scope)
        assert r1.observation_count == 3

        csv2 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv2 += '3/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Inspection Phase,\n'
        csv2 += '3/1/2026,RES-NEW-26-000002,Residential New Construction Permit,Test,"200 OAK ST, Sarasota, FL 34240 :",Pending,\n'
        csv2 += '3/1/2026,RES-NEW-26-000003,Residential New Construction Permit,Test,"300 ELM ST, Sarasota, FL 34240 :",Ready to Issue,\n'
        csv2 += '3/1/2026,RES-NEW-26-000004,Residential New Construction Permit,Test,"400 PINE ST, Sarasota, FL 34240 :",Submitted,\n'
        r2 = ingest_csv(csv2, "snap2.csv", store, scope)
        assert r2.observation_count == 4


class TestFullChangelogMatchesGroundTruth:
    def test_engine_matches_ground_truth(self):
        snapshots = generate_mock_data(num_permits=50, num_snapshots=4, seed=42)
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter(zip_codes=["34240"])

        all_engine_changes = []
        all_ground_truth = []

        for i, snap in enumerate(snapshots):
            csv_str = snapshot_to_csv(snap)
            result = ingest_csv(csv_str, f"snap_{i}.csv", store, scope)

            if i > 0:
                engine_changes = store.get_latest_changes(result.upload_id)
                engine_change_set = set()
                for ec in engine_changes:
                    engine_change_set.add((ec.record_number, ec.from_status, ec.to_status))
                for rn, status in (result.new_permit_records or []):
                    engine_change_set.add((rn, "", status))

                gt_change_set = set()
                for gc in snap.ground_truth_changes:
                    if not gc.is_disappeared:
                        gt_change_set.add((gc.record_number, gc.from_status, gc.to_status))

                all_engine_changes.extend(engine_change_set)
                all_ground_truth.extend(gt_change_set)

        engine_set = set(all_engine_changes)
        gt_set = set(all_ground_truth)

        missed = gt_set - engine_set
        phantom = engine_set - gt_set

        assert len(missed) == 0, f"Missed changes: {missed}"
        assert len(phantom) == 0, f"Phantom changes: {phantom}"


class TestTimelineReconstructedFromObservations:
    def test_timeline(self):
        store = SQLiteStore()
        store.initialize()
        scope = ScopeFilter(zip_codes=["34240"])

        statuses = ["Submitted", "Plan Review", "Ready to Issue", "Inspection Phase", "Pending CO", "Closed - Complete"]
        for i, status in enumerate(statuses):
            csv = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
            csv += f'{i+1}/15/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",{status},\n'
            ingest_csv(csv, f"snap_{i}.csv", store, scope)

        timeline = store.get_timeline("RES-NEW-26-000001")
        assert len(timeline) == 6
        assert timeline[0].status == "Submitted"
        assert timeline[-1].status == "Closed - Complete"
        for i in range(len(timeline) - 1):
            assert timeline[i].observed_date <= timeline[i + 1].observed_date


class TestPersistenceAcrossSessions:
    def test_data_persists(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        scope = ScopeFilter(zip_codes=["34240"])

        store1 = SQLiteStore(db_path)
        store1.initialize()
        csv1 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv1 += '2/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Submitted,\n'
        ingest_csv(csv1, "snap1.csv", store1, scope)
        store1.close()

        store2 = SQLiteStore(db_path)
        store2.initialize()
        permits = store2.get_current_statuses()
        assert "RES-NEW-26-000001" in permits
        assert permits["RES-NEW-26-000001"].current_status == "Submitted"

        timeline = store2.get_timeline("RES-NEW-26-000001")
        assert len(timeline) == 1

        csv2 = "Date,Record Number,Record Type,Description,Project Name,Status,Short Notes\n"
        csv2 += '3/1/2026,RES-NEW-26-000001,Residential New Construction Permit,Test,"100 MAIN ST, Sarasota, FL 34240 :",Inspection Phase,\n'
        result = ingest_csv(csv2, "snap2.csv", store2, scope)
        assert result.status_changes == 1
        store2.close()
