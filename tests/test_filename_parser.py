import pytest
from engine.filename_parser import parse_report_date_from_filename


def test_parses_m_d_yy_format():
    assert parse_report_date_from_filename("3.3.26_Raw_RecordList20260302.csv") == "2026-03-03"
    assert parse_report_date_from_filename("3.16.26_Raw RecordList20260316.csv") == "2026-03-16"
    assert parse_report_date_from_filename("12.25.25_Holiday_Report.csv") == "2025-12-25"


def test_parses_mm_dd_yyyy_format():
    assert parse_report_date_from_filename("03-03-2026_Report.csv") == "2026-03-03"


def test_falls_back_to_upload_date():
    from datetime import date
    today = date.today().isoformat()
    assert parse_report_date_from_filename("SomeRandomFile.csv") == today


def test_parses_leading_date_only():
    assert parse_report_date_from_filename("3.3.26.csv") == "2026-03-03"
