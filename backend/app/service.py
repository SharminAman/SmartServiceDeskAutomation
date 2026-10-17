"""Load policy from Postgres and apply it to request rows."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.models import AllowedValue, RequestRow, Rule, Setting, Template
from app.triage import Policy, TriageResult, triage
from app.triage import Rule as PolicyRule

REASON_SEP = " | "


def _flag(settings: dict[str, str], key: str, default: bool = True) -> bool:
    raw = settings.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_policy(db: Session) -> Policy:
    rules = (
        db.query(Rule)
        .options(selectinload(Rule.keywords))
        .order_by(Rule.sort_order, Rule.id)
        .all()
    )
    templates = {row.template_key: row.body for row in db.query(Template).all()}
    settings = {row.key: row.value for row in db.query(Setting).all()}
    allowed: dict[str, set[str]] = {}
    for row in db.query(AllowedValue).all():
        allowed.setdefault(row.field_name, set()).add(row.value)

    phrases = [part.strip() for part in settings.get("sensitive_keywords", "").split("|")]
    try:
        minimum = int(settings.get("summary_min_length", "15"))
    except ValueError:
        minimum = 15

    return Policy(
        rules=[
            PolicyRule(
                category=rule.category,
                keywords=[item.keyword for item in rule.keywords],
                enabled=rule.enabled,
                sort_order=rule.sort_order,
            )
            for rule in rules
        ],
        templates=templates,
        flag_missing_fields=_flag(settings, "flag_missing_fields"),
        flag_category_mismatch=_flag(settings, "flag_category_mismatch"),
        flag_high_priority=_flag(settings, "flag_high_priority"),
        flag_completed=_flag(settings, "flag_completed"),
        sensitive_keywords=[phrase for phrase in phrases if phrase],
        allowed_priorities=allowed.get("priority", set()),
        allowed_channels=allowed.get("channel", set()),
        allowed_statuses=allowed.get("status", set()),
        allowed_request_types=allowed.get("request_type", set()),
        summary_min_length=minimum,
    )


def apply_result(row: RequestRow, result: TriageResult) -> None:
    row.missing_fields = REASON_SEP.join(result.missing_fields)
    row.category = result.category
    row.rule_matched = result.keyword
    row.category_agrees = result.category_agrees
    row.acknowledgement = result.acknowledgement
    row.needs_human_review = result.needs_human_review
    row.review_reasons = REASON_SEP.join(result.review_reasons)
    row.updated_at = datetime.now(timezone.utc)


def record_from_row(row: RequestRow) -> dict[str, str]:
    return {
        "request_id": row.request_code,
        "submitted_date": row.submitted_date,
        "requester_role": row.requester_role,
        "request_type": row.request_type,
        "request_summary": row.request_summary,
        "priority": row.priority,
        "channel": row.channel,
        "status": row.status,
    }


def triage_row(row: RequestRow, policy: Policy) -> None:
    apply_result(row, triage(record_from_row(row), policy))


def split_reasons(value: str) -> list[str]:
    return [part for part in value.split(REASON_SEP) if part]


def to_api(row: RequestRow) -> dict:
    return {
        "id": row.id,
        "request_id": row.request_code,
        "submitted_date": row.submitted_date,
        "requester_role": row.requester_role,
        "request_type": row.request_type,
        "request_summary": row.request_summary,
        "priority": row.priority,
        "channel": row.channel,
        "status": row.status,
        "missing_fields": split_reasons(row.missing_fields),
        "category": row.category,
        "rule_matched": row.rule_matched,
        "category_agrees": row.category_agrees,
        "acknowledgement": row.acknowledgement,
        "needs_human_review": row.needs_human_review,
        "review_reasons": split_reasons(row.review_reasons),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def to_csv_record(row: RequestRow) -> dict[str, str]:
    return {
        "Request ID": row.request_code,
        "Submitted Date": row.submitted_date,
        "Requester Role": row.requester_role,
        "Request Type": row.request_type,
        "Request Summary": row.request_summary,
        "Priority": row.priority,
        "Channel": row.channel,
        "Status": row.status,
        "Category": row.category,
        "Rule Matched": row.rule_matched,
        "Category Agrees": "Yes" if row.category_agrees else "No",
        "Missing Fields": row.missing_fields,
        "Acknowledgement": row.acknowledgement,
        "Human Intervention Needed": "Yes" if row.needs_human_review else "No",
        "Why Human Intervention Is Needed": row.review_reasons
        or "No human intervention is needed.",
    }
