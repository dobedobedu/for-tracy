import pytest
from engine.orchestrator import ingest_csv
from engine.comparison import compare_reports
from engine.parser import ScopeFilter
from store.sqlite_store import SQLiteStore


def test_compare_two_reports():
    store = SQLiteStore(":memory:")
    store.initialize()
    scope = ScopeFilter()

    csv1 = (
        b'Date,Record Number,Record Type,Description,Project Name,Status\n'
        b'3/3/2026,RES-001,Residential New Construction Permit,Test,123 MAIN St Sarasota FL 34240,Submitted\n'
    )
    csv2 = (
        b'Date,Record Number,Record Type,Description,Project Name,Status\n'
        b'3/16/2026,RES-001,Residential New Construction Permit,Test,123 MAIN St Sarasota FL 34240,Plan Review\n'
    )

    ingest_csv(csv1, "3.3.26_Report.csv", store, scope)
    ingest_csv(csv2, "3.16.26_Report.csv", store, scope)

    result = compare_reports(store, "2026-03-03", "2026-03-16")

    assert result["from_report"]["date"] == "2026-03-03"
    assert result["to_report"]["date"] == "2026-03-16"
    assert len(result["transitions"]) == 1
    assert result["transitions"][0]["from_status"] == "Submitted"
    assert result["transitions"][0]["to_status"] == "Plan Review"


def test_compare_reports_not_found():
    store = SQLiteStore(":memory:")
    store.initialize()

    result = compare_reports(store, "2026-03-03", "2026-03-16")
    assert "error" in result


def test_compare_no_changes():
    store = SQLiteStore(":memory:")
    store.initialize()
    scope = ScopeFilter()

    csv1 = (
        b'Date,Record Number,Record Type,Description,Project Name,Status\n'
        b'3/3/2026,RES-001,Residential New Construction Permit,Test,123 MAIN St Sarasota FL 34240,Plan Review\n'
    )
    csv2 = (
        b'Date,Record Number,Record Type,Description,Project Name,Status\n'
        b'3/16/2026,RES-001,Residential New Construction Permit,Test,123 MAIN St Sarasota FL 34240,Plan Review\n'
    )

    ingest_csv(csv1, "3.3.26_Report.csv", store, scope)
    ingest_csv(csv2, "3.16.26_Report.csv", store, scope)

    result = compare_reports(store, "2026-03-03", "2026-03-16")
    assert result["transitions"] == []
