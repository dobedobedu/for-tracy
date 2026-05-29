import pytest
from engine.orchestrator import ingest_csv
from engine.parser import ScopeFilter
from store.sqlite_store import SQLiteStore


def test_upload_uses_filename_date():
    store = SQLiteStore(":memory:")
    store.initialize()
    scope = ScopeFilter()

    csv_content = (
        b'Date,Record Number,Record Type,Description,Project Name,Status\n'
        b'3/3/2026,RES-NEW-26-001,Residential New Construction Permit,Test,123 MAIN St Sarasota FL 34240,Submitted\n'
    )
    result = ingest_csv(csv_content, "3.3.26_Report.csv", store, scope)

    # The report_date should be from filename (2026-03-03)
    upload = store.get_upload_history()[0]
    assert upload.report_date == "2026-03-03"


def test_upload_with_different_filename_date():
    store = SQLiteStore(":memory:")
    store.initialize()
    scope = ScopeFilter()

    csv_content = (
        b'Date,Record Number,Record Type,Description,Project Name,Status\n'
        b'12/25/2025,RES-NEW-25-001,Residential New Construction Permit,Test,123 MAIN St Sarasota FL 34240,Submitted\n'
    )
    result = ingest_csv(csv_content, "12.25.25_Holiday.csv", store, scope)

    upload = store.get_upload_history()[0]
    assert upload.report_date == "2025-12-25"


def test_upload_fallback_date_for_random_filename():
    from datetime import date
    store = SQLiteStore(":memory:")
    store.initialize()
    scope = ScopeFilter()

    csv_content = (
        b'Date,Record Number,Record Type,Description,Project Name,Status\n'
        b'3/3/2026,RES-NEW-26-001,Residential New Construction Permit,Test,123 MAIN St Sarasota FL 34240,Submitted\n'
    )
    result = ingest_csv(csv_content, "SomeRandomFile.csv", store, scope)

    upload = store.get_upload_history()[0]
    assert upload.report_date == date.today().isoformat()
