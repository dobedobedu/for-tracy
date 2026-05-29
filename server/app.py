import os
import io
import csv
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse

from engine.orchestrator import ingest_csv, IngestionResult
from engine.parser import ScopeFilter
from engine.status import MILESTONE_ORDER, Milestone
from engine.comparison import compare_reports
from engine.summary import build_transition_summary
from store.sqlite_store import SQLiteStore
from store.postgres_store import PostgresStore
from store.interface import EventLogStore

app = FastAPI(title="PermitFlow")

# Enable CORS for the Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_URL = os.environ.get("DATABASE_URL", "permitflow.db")
if DB_URL.startswith("postgres://") or DB_URL.startswith("postgresql://"):
    store: EventLogStore = PostgresStore(DB_URL)
else:
    if DB_URL == "permitflow.db":
        DB_URL = os.path.join(os.path.dirname(os.path.dirname(__file__)), "permitflow.db")
    store: EventLogStore = SQLiteStore(DB_URL)
store.initialize()


def get_store() -> EventLogStore:
    return store


@app.on_event("startup")
async def startup():
    get_store().initialize()


@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    content = await file.read()
    scope = ScopeFilter()
    try:
        result = ingest_csv(content, file.filename, get_store(), scope)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "upload_id": result.upload_id,
        "filename": result.filename,
        "row_count_raw": result.row_count_raw,
        "row_count_after_scope": result.row_count_after_scope,
        "rows_dropped_by_scope": result.rows_dropped_by_scope,
        "new_permits": result.new_permits,
        "status_changes": result.status_changes,
        "unchanged": result.unchanged,
        "disappeared": result.disappeared,
        "tracked_milestone_hits": result.tracked_milestone_hits,
        "backward_moves": result.backward_moves,
        "unrecognized_statuses": result.unrecognized_statuses,
        "observation_count": result.observation_count,
    }


@app.get("/api/kanban")
async def get_kanban(
    community: str | None = Query(None),
    report_date: str | None = Query(None),
):
    s = get_store()
    
    if report_date:
        uploads = s.get_upload_history()
        matching = [u for u in uploads if u.report_date == report_date]
        if matching:
            matching.sort(key=lambda u: u.uploaded_at)
            upload_id = matching[0].id
            permits = s.get_all_permits()
            changes = s.get_latest_changes(upload_id)
            latest_upload = matching[0]
        else:
            permits = s.get_all_permits()
            latest_upload = s.get_latest_upload()
            changes = []
    else:
        permits = s.get_all_permits()
        latest_upload = s.get_latest_upload()
        changes = []
        if latest_upload:
            changes = s.get_latest_changes(latest_upload.id)

    if community:
        # Support multiple communities as comma-separated
        communities = [c.strip().upper() for c in community.split(",")]
        permits = [p for p in permits if any(c in p.address.upper() for c in communities)]

    changed_records = {}
    for c in changes:
        changed_records[c.record_number] = {
            "from_status": c.from_status,
            "to_status": c.to_status,
            "is_tracked_milestone": c.is_tracked_milestone,
            "is_backward": c.is_backward,
        }

    columns = {}
    for ms in MILESTONE_ORDER:
        columns[ms.value] = {
            "milestone": ms.value,
            "permits": [],
        }
    columns[Milestone.UNRECOGNIZED.value] = {
        "milestone": Milestone.UNRECOGNIZED.value,
        "permits": [],
    }

    closed_sub_statuses = {}
    for p in permits:
        col = p.current_milestone
        if col not in columns:
            col = Milestone.UNRECOGNIZED.value
        change_info = changed_records.get(p.record_number)
        card = {
            "record_number": p.record_number,
            "address": p.address,
            "city_state_zip": p.city_state_zip,
            "current_status": p.current_status,
            "current_milestone": p.current_milestone,
            "first_seen_date": p.first_seen_date,
            "last_seen_date": p.last_seen_date,
            "description": p.description,
            "changed": change_info is not None,
            "change_info": change_info,
        }
        columns[col]["permits"].append(card)
        
        # Track sub-statuses within Closed milestone
        if col == Milestone.CLOSED.value:
            sub = p.current_status
            closed_sub_statuses[sub] = closed_sub_statuses.get(sub, 0) + 1

    return {
        "columns": list(columns.values()),
        "closed_sub_statuses": closed_sub_statuses,
        "latest_upload": {
            "id": latest_upload.id,
            "filename": latest_upload.filename,
            "report_date": latest_upload.report_date,
            "uploaded_at": latest_upload.uploaded_at,
        } if latest_upload else None,
    }


@app.get("/api/permits/{record_number}/timeline")
async def get_timeline(record_number: str):
    s = get_store()
    timeline = s.get_timeline(record_number)
    permits = s.get_current_statuses()
    permit = permits.get(record_number)

    if not permit:
        raise HTTPException(status_code=404, detail="Permit not found")

    entries = []
    prev_status = None
    for t in timeline:
        is_change = t.status != prev_status
        entries.append({
            "observed_date": t.observed_date,
            "status": t.status,
            "milestone": t.milestone,
            "upload_id": t.upload_id,
            "is_status_change": is_change,
        })
        prev_status = t.status

    return {
        "permit": {
            "record_number": permit.record_number,
            "address": permit.address,
            "city_state_zip": permit.city_state_zip,
            "current_status": permit.current_status,
            "current_milestone": permit.current_milestone,
            "description": permit.description,
            "first_seen_date": permit.first_seen_date,
            "last_seen_date": permit.last_seen_date,
        },
        "timeline": entries,
    }


@app.get("/api/changes")
async def get_changes(
    upload_id: int | None = Query(None),
    report_date: str | None = Query(None),
    tracked_only: bool = Query(False),
):
    s = get_store()
    if upload_id is None and report_date is None:
        latest = s.get_latest_upload()
        if not latest:
            return {"changes": [], "upload": None}
        upload_id = latest.id
    elif report_date:
        uploads = s.get_upload_history()
        matching = [u for u in uploads if u.report_date == report_date]
        if not matching:
            return {"changes": [], "upload": None}
        matching.sort(key=lambda u: u.uploaded_at)
        upload_id = matching[0].id

    changes = s.get_latest_changes(upload_id)
    if tracked_only:
        changes = [c for c in changes if c.is_tracked_milestone]

    uploads = s.get_upload_history()
    upload = next((u for u in uploads if u.id == upload_id), None)

    return {
        "changes": [
            {
                "id": c.id,
                "record_number": c.record_number,
                "from_status": c.from_status,
                "to_status": c.to_status,
                "from_milestone": c.from_milestone,
                "to_milestone": c.to_milestone,
                "change_date": c.change_date,
                "is_tracked_milestone": c.is_tracked_milestone,
                "is_backward": c.is_backward,
            }
            for c in changes
        ],
        "upload": {
            "id": upload.id,
            "filename": upload.filename,
            "report_date": upload.report_date,
            "row_count_raw": upload.row_count_raw,
            "row_count_after_scope": upload.row_count_after_scope,
            "uploaded_at": upload.uploaded_at,
        } if upload else None,
    }


@app.get("/api/changes/export")
async def export_changes(upload_id: int | None = Query(None)):
    s = get_store()
    if upload_id is None:
        latest = s.get_latest_upload()
        if not latest:
            raise HTTPException(status_code=404, detail="No uploads yet")
        upload_id = latest.id

    changes = s.get_latest_changes(upload_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Record Number", "From Status", "To Status",
        "From Milestone", "To Milestone", "Change Date",
        "Tracked Milestone", "Backward Move",
    ])
    for c in changes:
        writer.writerow([
            c.record_number, c.from_status, c.to_status,
            c.from_milestone, c.to_milestone, c.change_date,
            "Yes" if c.is_tracked_milestone else "No",
            "Yes" if c.is_backward else "No",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=status_changes.csv"},
    )


@app.get("/api/uploads")
async def get_uploads():
    s = get_store()
    uploads = s.get_upload_history()
    return {
        "uploads": [
            {
                "id": u.id,
                "filename": u.filename,
                "report_date": u.report_date,
                "row_count_raw": u.row_count_raw,
                "row_count_after_scope": u.row_count_after_scope,
                "uploaded_at": u.uploaded_at,
            }
            for u in uploads
        ]
    }


@app.get("/api/disappeared")
async def get_disappeared():
    s = get_store()
    latest = s.get_latest_upload()
    if not latest:
        return {"disappeared": []}

    from engine.parser import parse_csv, ScopeFilter
    permits = s.get_all_permits()
    latest_changes = s.get_latest_changes(latest.id)
    changed_rns = {c.record_number for c in latest_changes}

    all_permits = s.get_current_statuses()
    return {
        "disappeared": [
            {
                "record_number": p.record_number,
                "address": p.address,
                "current_status": p.current_status,
                "last_seen_date": p.last_seen_date,
            }
            for p in all_permits.values()
        ]
    }


@app.get("/api/compare")
async def get_compare(from_date: str = Query(...), to_date: str = Query(...)):
    s = get_store()
    result = compare_reports(s, from_date, to_date)
    if "error" in result:
        return result
    result["summary"] = build_transition_summary(result["transitions"])
    return result


@app.get("/api/communities")
async def get_communities(only_changed: bool = Query(False), from_date: str = Query(None), to_date: str = Query(None)):
    s = get_store()
    permits = s.get_all_permits()

    changed_record_numbers = set()
    if only_changed:
        if from_date and to_date:
            cmp = compare_reports(s, from_date, to_date)
            changed_record_numbers = {t["record_number"] for t in cmp.get("transitions", [])}
        else:
            latest_upload = s.get_latest_upload()
            if latest_upload:
                changes = s.get_latest_changes(latest_upload.id)
                changed_record_numbers = {c.record_number for c in changes}

    communities = {}
    for p in permits:
        if only_changed and p.record_number not in changed_record_numbers:
            continue
        comm = p.community or "Unknown"
        if comm not in communities:
            communities[comm] = {
                "name": comm,
                "count": 0,
                "permits": [],
            }
        communities[comm]["count"] += 1
        communities[comm]["permits"].append({
            "record_number": p.record_number,
            "address": p.address,
            "current_status": p.current_status,
            "current_milestone": p.current_milestone,
        })

    sorted_communities = sorted(
        communities.values(),
        key=lambda x: x["count"],
        reverse=True
    )

    return {"communities": sorted_communities}


@app.get("/api/calendar")
async def get_calendar():
    s = get_store()
    uploads = s.get_upload_history()
    
    activity = {}
    for u in uploads:
        date = u.report_date
        if date not in activity:
            activity[date] = {
                "date": date,
                "uploads": 0,
                "permits_observed": 0,
                "permits_changed": 0,
            }
        activity[date]["uploads"] += 1
        activity[date]["permits_observed"] += u.row_count_after_scope
    
    return {"activity": list(activity.values())}


static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
