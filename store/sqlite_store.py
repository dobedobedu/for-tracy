import sqlite3
from datetime import datetime, timezone

from store.interface import (
    EventLogStore, PermitRecord, Observation, Upload,
    StatusChangeRecord, TimelineEntry,
)
from engine.status import Milestone


class SQLiteStore(EventLogStore):
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
        return self.conn

    def initialize(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                report_date TEXT NOT NULL,
                row_count_raw INTEGER NOT NULL,
                row_count_after_scope INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL
            );

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
            );

            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_number TEXT NOT NULL,
                status TEXT NOT NULL,
                milestone TEXT NOT NULL,
                observed_date TEXT NOT NULL,
                upload_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (record_number) REFERENCES permits(record_number),
                FOREIGN KEY (upload_id) REFERENCES uploads(id)
            );

            CREATE TABLE IF NOT EXISTS status_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_number TEXT NOT NULL,
                from_status TEXT NOT NULL,
                to_status TEXT NOT NULL,
                from_milestone TEXT NOT NULL,
                to_milestone TEXT NOT NULL,
                detected_on_upload_id INTEGER NOT NULL,
                change_date TEXT NOT NULL,
                is_tracked_milestone INTEGER NOT NULL,
                is_backward INTEGER NOT NULL,
                FOREIGN KEY (record_number) REFERENCES permits(record_number),
                FOREIGN KEY (detected_on_upload_id) REFERENCES uploads(id)
            );

            CREATE INDEX IF NOT EXISTS idx_observations_record ON observations(record_number);
            CREATE INDEX IF NOT EXISTS idx_observations_upload ON observations(upload_id);
            CREATE INDEX IF NOT EXISTS idx_status_changes_upload ON status_changes(detected_on_upload_id);
        """)
        conn.commit()

    def get_current_statuses(self) -> dict[str, PermitRecord]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM permits").fetchall()
        result = {}
        for r in rows:
            try:
                community = r["community"]
            except KeyError:
                community = ""
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
                community=community,
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
        cursor = conn.execute(
            "INSERT INTO uploads (filename, report_date, row_count_raw, row_count_after_scope, uploaded_at) VALUES (?, ?, ?, ?, ?)",
            (upload.filename, upload.report_date, upload.row_count_raw, upload.row_count_after_scope, now),
        )
        conn.commit()
        return cursor.lastrowid

    def upsert_permit(self, permit: PermitRecord) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO permits (record_number, record_type, description, address, city_state_zip,
               first_seen_date, last_seen_date, current_status, current_milestone, community)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(record_number) DO UPDATE SET
               last_seen_date=excluded.last_seen_date,
               current_status=excluded.current_status,
               current_milestone=excluded.current_milestone,
               community=excluded.community""",
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
        conn.execute(
            "INSERT INTO observations (record_number, status, milestone, observed_date, upload_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (obs.record_number, obs.status, obs.milestone, obs.observed_date, obs.upload_id, now),
        )
        conn.commit()

    def record_status_change(self, change: StatusChangeRecord) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO status_changes (record_number, from_status, to_status, from_milestone,
               to_milestone, detected_on_upload_id, change_date, is_tracked_milestone, is_backward)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                change.record_number, change.from_status, change.to_status,
                change.from_milestone, change.to_milestone, change.detected_on_upload_id,
                change.change_date, int(change.is_tracked_milestone), int(change.is_backward),
            ),
        )
        conn.commit()

    def get_timeline(self, record_number: str) -> list[TimelineEntry]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT observed_date, status, milestone, upload_id FROM observations WHERE record_number = ? ORDER BY observed_date ASC, id ASC",
            (record_number,),
        ).fetchall()
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
        rows = conn.execute(
            "SELECT * FROM status_changes WHERE detected_on_upload_id = ? ORDER BY id",
            (upload_id,),
        ).fetchall()
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
                is_tracked_milestone=bool(r["is_tracked_milestone"]),
                is_backward=bool(r["is_backward"]),
            )
            for r in rows
        ]

    def get_all_permits(self) -> list[PermitRecord]:
        return list(self.get_current_statuses().values())

    def get_upload_history(self) -> list[Upload]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM uploads ORDER BY id DESC").fetchall()
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
        row = conn.execute("SELECT * FROM uploads ORDER BY id DESC LIMIT 1").fetchone()
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
        conn = self._get_conn()
        all_permits = self.get_current_statuses()
        return [p for rn, p in all_permits.items() if rn not in current_record_numbers]

    def get_permit_status_at_date(self, record_number: str, date: str) -> str | None:
        conn = self._get_conn()
        row = conn.execute(
            """SELECT o.status FROM observations o
               JOIN uploads u ON o.upload_id = u.id
               WHERE o.record_number = ? AND u.report_date <= ?
               ORDER BY u.report_date DESC, o.id DESC
               LIMIT 1""",
            (record_number, date),
        ).fetchone()
        return row["status"] if row else None

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
