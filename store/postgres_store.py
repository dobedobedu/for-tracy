import os
import re
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

from store.interface import (
    EventLogStore, PermitRecord, Observation, Upload,
    StatusChangeRecord, TimelineEntry,
)
from engine.status import Milestone


class PostgresStore(EventLogStore):
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.environ.get("DATABASE_URL", "")
        self.conn = None

    def _get_conn(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.dsn, cursor_factory=RealDictCursor)
        return self.conn

    def initialize(self) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS uploads (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    report_date TEXT NOT NULL,
                    row_count_raw INTEGER NOT NULL,
                    row_count_after_scope INTEGER NOT NULL,
                    uploaded_at TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS permits (
                    record_number TEXT PRIMARY KEY,
                    record_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    address TEXT NOT NULL,
                    city_state_zip TEXT NOT NULL,
                    first_seen_date TEXT NOT NULL,
                    last_seen_date TEXT NOT NULL,
                    current_status TEXT NOT NULL,
                    current_milestone TEXT NOT NULL,
                    community TEXT NOT NULL DEFAULT ''
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id SERIAL PRIMARY KEY,
                    record_number TEXT NOT NULL REFERENCES permits(record_number),
                    status TEXT NOT NULL,
                    milestone TEXT NOT NULL,
                    observed_date TEXT NOT NULL,
                    upload_id INTEGER NOT NULL REFERENCES uploads(id),
                    created_at TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS status_changes (
                    id SERIAL PRIMARY KEY,
                    record_number TEXT NOT NULL REFERENCES permits(record_number),
                    from_status TEXT NOT NULL,
                    to_status TEXT NOT NULL,
                    from_milestone TEXT NOT NULL,
                    to_milestone TEXT NOT NULL,
                    detected_on_upload_id INTEGER NOT NULL REFERENCES uploads(id),
                    change_date TEXT NOT NULL,
                    is_tracked_milestone BOOLEAN NOT NULL,
                    is_backward BOOLEAN NOT NULL
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_observations_record
                ON observations(record_number)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_observations_upload
                ON observations(upload_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_status_changes_upload
                ON status_changes(detected_on_upload_id)
            """)
        conn.commit()

    def get_current_statuses(self) -> dict[str, PermitRecord]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM permits")
            rows = cur.fetchall()
        result = {}
        for r in rows:
            result[r["record_number"]] = PermitRecord(
                record_number=r["record_number"],
                record_type=r["record_type"],
                description=r["description"],
                address=r["address"],
                city_state_zip=r["city_state_zip"],
                first_seen_date=r["first_seen_date"],
                last_seen_date=r["last_seen_date"],
                current_status=r["current_status"],
                current_milestone=r["current_milestone"],
                community=r.get("community") or "",
            )
        return result

    def get_current_status_map(self) -> tuple[dict[str, str], dict[str, Milestone], dict[str, str]]:
        permits = self.get_current_statuses()
        status_map = {}
        milestone_map = {}
        date_map = {}
        for rn, p in permits.items():
            status_map[rn] = p.current_status
            try:
                milestone_map[rn] = Milestone(p.current_milestone)
            except ValueError:
                milestone_map[rn] = Milestone.UNRECOGNIZED
            date_map[rn] = p.last_seen_date
        return status_map, milestone_map, date_map

    def record_upload(self, upload: Upload) -> int:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO uploads (filename, report_date, row_count_raw, row_count_after_scope, uploaded_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (upload.filename, upload.report_date, upload.row_count_raw, upload.row_count_after_scope, now),
            )
            row = cur.fetchone()
        conn.commit()
        return row["id"]

    def upsert_permit(self, permit: PermitRecord) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO permits (record_number, record_type, description, address, city_state_zip,
                   first_seen_date, last_seen_date, current_status, current_milestone, community)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (record_number) DO UPDATE SET
                   last_seen_date = EXCLUDED.last_seen_date,
                   current_status = EXCLUDED.current_status,
                   current_milestone = EXCLUDED.current_milestone,
                   community = EXCLUDED.community
                """,
                (
                    permit.record_number, permit.record_type, permit.description,
                    permit.address, permit.city_state_zip, permit.first_seen_date,
                    permit.last_seen_date, permit.current_status, permit.current_milestone,
                    permit.community,
                ),
            )
        conn.commit()

    def append_observation(self, obs: Observation) -> None:
        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO observations (record_number, status, milestone, observed_date, upload_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (obs.record_number, obs.status, obs.milestone, obs.observed_date, obs.upload_id, now),
            )
        conn.commit()

    def record_status_change(self, change: StatusChangeRecord) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO status_changes (record_number, from_status, to_status, from_milestone,
                   to_milestone, detected_on_upload_id, change_date, is_tracked_milestone, is_backward)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    change.record_number, change.from_status, change.to_status,
                    change.from_milestone, change.to_milestone, change.detected_on_upload_id,
                    change.change_date, change.is_tracked_milestone, change.is_backward,
                ),
            )
        conn.commit()

    def get_timeline(self, record_number: str) -> list[TimelineEntry]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT observed_date, status, milestone, upload_id
                FROM observations
                WHERE record_number = %s
                ORDER BY observed_date ASC, id ASC
                """,
                (record_number,),
            )
            rows = cur.fetchall()
        return [
            TimelineEntry(
                observed_date=r["observed_date"],
                status=r["status"],
                milestone=r["milestone"],
                upload_id=r["upload_id"],
            )
            for r in rows
        ]

    def get_latest_changes(self, upload_id: int) -> list[StatusChangeRecord]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM status_changes
                WHERE detected_on_upload_id = %s
                ORDER BY id
                """,
                (upload_id,),
            )
            rows = cur.fetchall()
        return [
            StatusChangeRecord(
                id=r["id"],
                record_number=r["record_number"],
                from_status=r["from_status"],
                to_status=r["to_status"],
                from_milestone=r["from_milestone"],
                to_milestone=r["to_milestone"],
                detected_on_upload_id=r["detected_on_upload_id"],
                change_date=r["change_date"],
                is_tracked_milestone=r["is_tracked_milestone"],
                is_backward=r["is_backward"],
            )
            for r in rows
        ]

    def get_all_permits(self) -> list[PermitRecord]:
        return list(self.get_current_statuses().values())

    def get_upload_history(self) -> list[Upload]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM uploads ORDER BY id DESC")
            rows = cur.fetchall()
        return [
            Upload(
                id=r["id"],
                filename=r["filename"],
                report_date=r["report_date"],
                row_count_raw=r["row_count_raw"],
                row_count_after_scope=r["row_count_after_scope"],
                uploaded_at=r["uploaded_at"],
            )
            for r in rows
        ]

    def get_latest_upload(self) -> Upload | None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM uploads ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
        if row is None:
            return None
        return Upload(
            id=row["id"],
            filename=row["filename"],
            report_date=row["report_date"],
            row_count_raw=row["row_count_raw"],
            row_count_after_scope=row["row_count_after_scope"],
            uploaded_at=row["uploaded_at"],
        )

    def get_disappeared_permits(self, current_record_numbers: set[str]) -> list[PermitRecord]:
        all_permits = self.get_current_statuses()
        return [p for rn, p in all_permits.items() if rn not in current_record_numbers]

    def get_permit_status_at_date(self, record_number: str, date: str) -> str | None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT o.status FROM observations o
                JOIN uploads u ON o.upload_id = u.id
                WHERE o.record_number = %s AND u.report_date <= %s
                ORDER BY u.report_date DESC, o.id DESC
                LIMIT 1
                """,
                (record_number, date),
            )
            row = cur.fetchone()
        return row["status"] if row else None

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
