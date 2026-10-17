"""First-run contents for an empty database. Later edits happen in the admin desk."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.csvio import parse_csv
from app.models import AdminUser, AllowedValue, RequestRow, Rule, RuleKeyword, Setting, Template
from app.service import load_policy, triage_row

import os
from pathlib import Path

def _sample_path() -> Path | None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "data" / "sample_requests.csv",
        here.parents[1] / "data" / "sample_requests.csv",
        Path("/data/sample_requests.csv"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None

STARTER_RULES = [
    ("Access & Permissions", ["access", "permission", "collaborator"]),
    ("System Integration", ["connect", "synchronise", "sync"]),
    ("Process Automation", ["automate", "automated", "reminder"]),
    ("Reporting & Analytics", ["dashboard", "summary", "engagement", "analytics"]),
    ("Content & Guidance", ["guide", "template", "publish", "announcement"]),
]

TEMPLATES = {
    "Access & Permissions": "We have received {request_id}, an Access & Permissions request, and will review it.",
    "Process Automation": "We have received {request_id}. Your Process Automation request is logged and will be reviewed.",
    "Reporting & Analytics": "We have received {request_id}. Your Reporting & Analytics request is logged and will be reviewed.",
    "System Integration": "We have received {request_id}. Your System Integration request is logged and will be reviewed.",
    "Content & Guidance": "We have received {request_id}. Your Content & Guidance request is logged and will be reviewed.",
    "missing_fields": "We have received {request_id}, but some required information is missing: {missing_fields}. Please send the missing details so we can continue.",
    "completed": "{request_id} is already marked completed. A person will confirm that no further acknowledgement is needed.",
    "uncategorised": "We have received {request_id}. The summary did not match a category rule, so a person will review it.",
    "mismatch": "We have received {request_id}. The summary looks like {category}, which differs from the selected type {request_type}, so a person will check it.",
    "default": "We have received {request_id} and will review it.",
}

LISTS = {
    "priority": ["Low", "Medium", "High"],
    "channel": ["Service Portal", "Email", "Teams"],
    "status": ["New", "In Review", "Assigned", "Planned", "In Progress", "Completed"],
    "request_type": [name for name, _ in STARTER_RULES],
}

SETTINGS = {
    "flag_missing_fields": "true",
    "flag_category_mismatch": "true",
    "flag_high_priority": "true",
    "flag_completed": "true",
    "sensitive_keywords": "external collaborator|finance|expenses",
    "summary_min_length": "15",
}


def seed(db: Session) -> None:
    if db.query(AdminUser).count() == 0:
        username = os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"
        password = os.getenv("ADMIN_PASSWORD", "RequestDesk!2026")
        db.add(AdminUser(username=username, password_hash=hash_password(password)))
        db.commit()

    if db.query(Rule).count() > 0:
        return

    for index, (category, keywords) in enumerate(STARTER_RULES):
        rule = Rule(category=category, sort_order=index, enabled=True)
        rule.keywords = [RuleKeyword(keyword=keyword) for keyword in keywords]
        db.add(rule)

    for key, body in TEMPLATES.items():
        db.add(Template(template_key=key, body=body))

    for key, value in SETTINGS.items():
        db.add(Setting(key=key, value=value))

    for field_name, values in LISTS.items():
        for value in values:
            db.add(AllowedValue(field_name=field_name, value=value))

    db.commit()

    sample = _sample_path()
    if sample is None or db.query(RequestRow).count() > 0:
        return

    parsed = parse_csv(sample.read_text(encoding="utf-8"))
    policy = load_policy(db)
    for item in parsed.rows:
        row = RequestRow(
            request_code=item["request_id"],
            submitted_date=item["submitted_date"],
            requester_role=item["requester_role"],
            request_type=item["request_type"],
            request_summary=item["request_summary"],
            priority=item["priority"],
            channel=item["channel"],
            status=item["status"],
        )
        triage_row(row, policy)
        db.add(row)
    db.commit()
