from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import current_user
from app.csvio import parse_csv, render_csv
from app.db import get_db
from app.models import AdminUser, AllowedValue, RequestRow, Rule
from app.service import load_policy, to_api, to_csv_record, triage_row

router = APIRouter(prefix="/api", tags=["requests"])

MAX_BYTES = 2_000_000
MAX_ROWS = 5_000


class RequestIn(BaseModel):
    request_id: str = Field(default="", max_length=64)
    submitted_date: str = Field(default="", max_length=32)
    requester_role: str = Field(default="", max_length=200)
    request_type: str = Field(default="", max_length=200)
    request_summary: str = Field(default="", max_length=4000)
    priority: str = Field(default="", max_length=64)
    channel: str = Field(default="", max_length=64)
    status: str = Field(default="", max_length=64)


def _apply_filters(
    db: Session,
    review: str | None,
    missing: str | None,
    match: str | None,
    category: str | None,
    priority: str | None,
    status: str | None,
    channel: str | None,
    q: str | None,
):
    query = db.query(RequestRow)
    if review == "yes":
        query = query.filter(RequestRow.needs_human_review.is_(True))
    elif review == "no":
        query = query.filter(RequestRow.needs_human_review.is_(False))
    if missing == "yes":
        query = query.filter(RequestRow.missing_fields != "")
    elif missing == "no":
        query = query.filter(RequestRow.missing_fields == "")
    if match == "yes":
        query = query.filter(RequestRow.category_agrees.is_(True))
    elif match == "no":
        query = query.filter(RequestRow.category_agrees.is_(False))
    if category:
        query = query.filter(RequestRow.category == category)
    if priority:
        query = query.filter(RequestRow.priority == priority)
    if status:
        query = query.filter(RequestRow.status == status)
    if channel:
        query = query.filter(RequestRow.channel == channel)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                RequestRow.request_code.ilike(like),
                RequestRow.requester_role.ilike(like),
                RequestRow.request_summary.ilike(like),
                RequestRow.category.ilike(like),
            )
        )
    return query.order_by(RequestRow.request_code, RequestRow.id)


def _facets(db: Session) -> dict:
    rows = db.query(RequestRow).all()
    rules = db.query(Rule).order_by(Rule.sort_order, Rule.id).all()

    def unique(values: list[str]) -> list[str]:
        seen: list[str] = []
        for value in values:
            if value and value not in seen:
                seen.append(value)
        return seen

    categories = unique([rule.category for rule in rules] + [row.category for row in rows])
    return {
        "categories": categories,
        "priorities": unique([row.value for row in db.query(AllowedValue).filter(AllowedValue.field_name == "priority")] + [row.priority for row in rows]),
        "statuses": unique([row.value for row in db.query(AllowedValue).filter(AllowedValue.field_name == "status")] + [row.status for row in rows]),
        "channels": unique([row.value for row in db.query(AllowedValue).filter(AllowedValue.field_name == "channel")] + [row.channel for row in rows]),
        "request_types": unique([row.value for row in db.query(AllowedValue).filter(AllowedValue.field_name == "request_type")]),
    }


def _fill(row: RequestRow, body: RequestIn, code: str) -> None:
    row.request_code = code
    row.submitted_date = body.submitted_date.strip()
    row.requester_role = body.requester_role.strip()
    row.request_type = body.request_type.strip()
    row.request_summary = body.request_summary.strip()
    row.priority = body.priority.strip()
    row.channel = body.channel.strip()
    row.status = body.status.strip()


def _next_code(db: Session) -> str:
    numbers: list[int] = []
    for (code,) in db.query(RequestRow.request_code).all():
        head, sep, tail = (code or "").partition("-")
        if sep and head.upper() == "REQ" and tail.isdigit():
            numbers.append(int(tail))
    nxt = max(numbers) + 1 if numbers else 1
    return f"REQ-{nxt:03d}"


@router.get("/meta")
def meta(db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    facets = _facets(db)
    return {
        "priorities": facets["priorities"],
        "channels": facets["channels"],
        "statuses": facets["statuses"],
        "request_types": facets["request_types"],
        "categories": facets["categories"],
        "next_id": _next_code(db),
    }


@router.get("/requests")
def list_requests(
    review: str | None = None,
    missing: str | None = None,
    match: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    channel: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(current_user),
):
    rows = _apply_filters(db, review, missing, match, category, priority, status, channel, q).all()
    return {"items": [to_api(row) for row in rows], "total": len(rows), "facets": _facets(db)}


@router.get("/requests/next-id")
def next_id(db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    return {"request_id": _next_code(db)}


@router.get("/requests/export")
def export_requests(
    scope: str = Query(default="all"),
    review: str | None = None,
    missing: str | None = None,
    match: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    channel: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(current_user),
):
    if scope == "view":
        rows = _apply_filters(db, review, missing, match, category, priority, status, channel, q).all()
        filename = "request-desk-view.csv"
    else:
        rows = db.query(RequestRow).order_by(RequestRow.request_code, RequestRow.id).all()
        filename = "request-desk-all.csv"
    payload = "\ufeff" + render_csv([to_csv_record(row) for row in rows])
    return Response(
        content=payload,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/requests")
def create_request(body: RequestIn, db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    code = body.request_id.strip()
    if not code:
        raise HTTPException(status_code=400, detail="A request needs an ID before it can be saved")
    if db.query(RequestRow).filter(RequestRow.request_code == code).one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"{code} is already on the desk. Choose another ID, or upload a file to update it.",
        )
    row = RequestRow(request_code=code)
    _fill(row, body, code)
    triage_row(row, load_policy(db))
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_api(row)


@router.post("/requests/upload")
async def upload_requests(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(current_user),
):
    name = (file.filename or "").lower()
    if name and not name.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Save the spreadsheet as a .csv file, then upload that file")
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="That file is larger than 2 MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="The file needs to be saved as UTF-8")
    parsed = parse_csv(text)
    if parsed.missing_columns:
        raise HTTPException(
            status_code=400,
            detail="This file is missing columns: " + ", ".join(parsed.missing_columns),
        )
    if len(parsed.rows) > MAX_ROWS:
        raise HTTPException(status_code=400, detail="This file has more than 5000 requests")

    policy = load_policy(db)
    inserted = 0
    updated = 0
    failed: list[dict] = []
    pending: dict[str, RequestRow] = {}
    for index, item in enumerate(parsed.rows, start=2):
        code = item["request_id"].strip()
        if not code:
            failed.append({"row": index, "error": "Request ID is empty"})
            continue
        row = pending.get(code)
        if row is None:
            existing = db.query(RequestRow).filter(RequestRow.request_code == code).one_or_none()
            if existing is None:
                row = RequestRow(request_code=code)
                db.add(row)
                inserted += 1
            else:
                row = existing
                updated += 1
            pending[code] = row
        row.submitted_date = item["submitted_date"]
        row.requester_role = item["requester_role"]
        row.request_type = item["request_type"]
        row.request_summary = item["request_summary"]
        row.priority = item["priority"]
        row.channel = item["channel"]
        row.status = item["status"]
        triage_row(row, policy)
    db.commit()
    return {"inserted": inserted, "updated": updated, "failed": failed, "total": db.query(RequestRow).count()}


@router.post("/requests/reanalyse")
def reanalyse(db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    policy = load_policy(db)
    rows = db.query(RequestRow).all()
    for row in rows:
        triage_row(row, policy)
    db.commit()
    return {"updated": len(rows)}


@router.get("/requests/{request_id}")
def get_request(request_id: int, db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    row = db.get(RequestRow, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="That request is not on the desk")
    return to_api(row)


@router.delete("/requests/{request_id}")
def delete_request(request_id: int, db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    row = db.get(RequestRow, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="That request is not on the desk")
    db.delete(row)
    db.commit()
    return {"ok": True}
