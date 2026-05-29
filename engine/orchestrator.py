import io
from dataclasses import dataclass

import pandas as pd

from engine.parser import parse_csv, ScopeFilter, ParsedRow
from engine.diff import detect_changes, DiffResult
from engine.status import Milestone
from engine.filename_parser import parse_report_date_from_filename
from store.interface import (
    EventLogStore, Upload, PermitRecord, Observation, StatusChangeRecord,
)


@dataclass
class IngestionResult:
    upload_id: int
    filename: str
    row_count_raw: int
    row_count_after_scope: int
    rows_dropped_by_scope: int
    new_permits: int
    status_changes: int
    unchanged: int
    disappeared: int
    tracked_milestone_hits: int
    backward_moves: int
    unrecognized_statuses: list[str]
    observation_count: int
    new_permit_records: list[tuple[str, str]] = None


def ingest_csv(
    file_content: bytes | str,
    filename: str,
    store: EventLogStore,
    scope: ScopeFilter | None = None,
) -> IngestionResult:
    if isinstance(file_content, bytes):
        df = pd.read_csv(io.BytesIO(file_content), dtype=str)
    else:
        df = pd.read_csv(io.StringIO(file_content), dtype=str)

    df = df.fillna("")
    row_count_raw = len(df)

    if scope is None:
        scope = ScopeFilter()

    parsed_rows, dropped = parse_csv(df, scope)
    row_count_after_scope = len(parsed_rows)

    report_date = parse_report_date_from_filename(filename)

    upload = Upload(
        id=None,
        filename=filename,
        report_date=report_date,
        row_count_raw=row_count_raw,
        row_count_after_scope=row_count_after_scope,
    )
    upload_id = store.record_upload(upload)

    prior_statuses, prior_milestones, prior_dates = store.get_current_status_map()
    prior_records = store.get_current_statuses()

    diff = detect_changes(parsed_rows, prior_statuses, prior_milestones, prior_dates)

    for np in diff.new_permits:
        permit = PermitRecord(
            record_number=np.record_number,
            record_type=np.record_type,
            description=np.description,
            address=np.address,
            city_state_zip=np.city_state_zip,
            first_seen_date=np.observed_date,
            last_seen_date=np.observed_date,
            current_status=np.status,
            current_milestone=np.milestone.value,
            community=np.community,
        )
        store.upsert_permit(permit)
        store.append_observation(Observation(
            id=None,
            record_number=np.record_number,
            status=np.status,
            milestone=np.milestone.value,
            observed_date=np.observed_date,
            upload_id=upload_id,
        ))

    for sc in diff.status_changes:
        store.record_status_change(StatusChangeRecord(
            id=None,
            record_number=sc.record_number,
            from_status=sc.from_status,
            to_status=sc.to_status,
            from_milestone=sc.from_milestone.value,
            to_milestone=sc.to_milestone.value,
            detected_on_upload_id=upload_id,
            change_date=sc.change_date,
            is_tracked_milestone=sc.is_tracked_milestone,
            is_backward=sc.is_backward,
        ))
        row = next(r for r in parsed_rows if r.record_number == sc.record_number)
        prior_rec = prior_records.get(sc.record_number)
        first_seen = prior_rec.first_seen_date if prior_rec else sc.change_date
        store.upsert_permit(PermitRecord(
            record_number=sc.record_number,
            record_type=row.record_type,
            description=row.description,
            address=row.address,
            city_state_zip=row.city_state_zip,
            first_seen_date=first_seen,
            last_seen_date=sc.change_date,
            current_status=sc.to_status,
            current_milestone=sc.to_milestone.value,
            community=row.community,
        ))
        store.append_observation(Observation(
            id=None,
            record_number=sc.record_number,
            status=sc.to_status,
            milestone=sc.to_milestone.value,
            observed_date=sc.change_date,
            upload_id=upload_id,
        ))

    for rn in diff.unchanged:
        row = next(r for r in parsed_rows if r.record_number == rn)
        prior_rec = prior_records[rn]
        store.upsert_permit(PermitRecord(
            record_number=rn,
            record_type=row.record_type,
            description=row.description,
            address=row.address,
            city_state_zip=row.city_state_zip,
            first_seen_date=prior_rec.first_seen_date,
            last_seen_date=row.date,
            current_status=row.status,
            current_milestone=row.milestone.value,
            community=row.community,
        ))
        store.append_observation(Observation(
            id=None,
            record_number=rn,
            status=row.status,
            milestone=row.milestone.value,
            observed_date=row.date,
            upload_id=upload_id,
        ))

    tracked = sum(1 for sc in diff.status_changes if sc.is_tracked_milestone)
    backward = sum(1 for sc in diff.status_changes if sc.is_backward)
    new_permit_tuples = [(np.record_number, np.status) for np in diff.new_permits]

    return IngestionResult(
        upload_id=upload_id,
        filename=filename,
        row_count_raw=row_count_raw,
        row_count_after_scope=row_count_after_scope,
        rows_dropped_by_scope=dropped,
        new_permits=len(diff.new_permits),
        status_changes=len(diff.status_changes),
        unchanged=len(diff.unchanged),
        disappeared=len(diff.disappeared),
        tracked_milestone_hits=tracked,
        backward_moves=backward,
        unrecognized_statuses=diff.unrecognized_statuses,
        observation_count=diff.observation_count,
        new_permit_records=new_permit_tuples,
    )
