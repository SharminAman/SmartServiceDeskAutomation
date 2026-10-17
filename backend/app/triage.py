"""Rule-based triage for service requests.

The engine is pure. It receives one request and the current policy, and it
returns a result. Categories, templates, and review switches are supplied by
the caller (the database, in the running app). Nothing here is fixed to the
five starter categories.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

PLACEHOLDERS = (
    "request_id",
    "category",
    "priority",
    "request_type",
    "missing_fields",
    "status",
)


@dataclass
class Rule:
    category: str
    keywords: list[str]
    enabled: bool = True
    sort_order: int = 0


@dataclass
class Policy:
    rules: list[Rule]
    templates: dict[str, str]
    flag_missing_fields: bool = True
    flag_category_mismatch: bool = True
    flag_high_priority: bool = True
    flag_completed: bool = True
    sensitive_keywords: list[str] = field(default_factory=list)
    allowed_priorities: set[str] = field(default_factory=set)
    allowed_channels: set[str] = field(default_factory=set)
    allowed_statuses: set[str] = field(default_factory=set)
    allowed_request_types: set[str] = field(default_factory=set)
    summary_min_length: int = 15


@dataclass
class TriageResult:
    missing_fields: list[str]
    category: str
    keyword: str
    category_agrees: bool
    acknowledgement: str
    needs_human_review: bool
    review_reasons: list[str]


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key in PLACEHOLDERS:
        rendered = rendered.replace("{" + key + "}", values.get(key, ""))
    return rendered


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _valid_date(value: str) -> bool:
    try:
        datetime.strptime(value.strip(), "%d/%m/%Y")
        return True
    except ValueError:
        return False


def _request_id_ok(value: str) -> bool:
    head, sep, tail = value.partition("-")
    return bool(sep) and head.upper() == "REQ" and tail.isdigit() and len(tail) > 0


def match_rule(summary: str, rules: list[Rule]) -> tuple[Rule | None, str]:
    text = summary.lower()
    ordered = sorted((rule for rule in rules if rule.enabled), key=lambda rule: rule.sort_order)
    for rule in ordered:
        hits = [kw.strip() for kw in rule.keywords if kw.strip() and kw.strip().lower() in text]
        if hits:
            hits.sort(key=len, reverse=True)
            return rule, hits[0]
    return None, ""


def triage(record: dict[str, str], policy: Policy) -> TriageResult:
    request_id = _clean(record.get("request_id"))
    submitted = _clean(record.get("submitted_date"))
    role = _clean(record.get("requester_role"))
    request_type = _clean(record.get("request_type"))
    summary = _clean(record.get("request_summary"))
    priority = _clean(record.get("priority"))
    channel = _clean(record.get("channel"))
    status = _clean(record.get("status"))

    issues: list[str] = []
    if not request_id:
        issues.append("Request ID")
    elif not _request_id_ok(request_id):
        issues.append("Request ID (unexpected format)")
    if not submitted:
        issues.append("Submitted Date")
    elif not _valid_date(submitted):
        issues.append("Submitted Date (invalid)")
    if not role:
        issues.append("Requester Role")
    if not request_type:
        issues.append("Request Type")
    elif policy.allowed_request_types and request_type not in policy.allowed_request_types:
        issues.append("Request Type (not in the allowed list)")
    if not summary:
        issues.append("Request Summary")
    elif len(summary) < policy.summary_min_length:
        issues.append("Request Summary (too short)")
    if not priority:
        issues.append("Priority")
    elif policy.allowed_priorities and priority not in policy.allowed_priorities:
        issues.append("Priority (not in the allowed list)")
    if not channel:
        issues.append("Channel")
    elif policy.allowed_channels and channel not in policy.allowed_channels:
        issues.append("Channel (not in the allowed list)")
    if not status:
        issues.append("Status")
    elif policy.allowed_statuses and status not in policy.allowed_statuses:
        issues.append("Status (not in the allowed list)")

    rule, keyword = match_rule(summary, policy.rules)
    category = rule.category if rule else "Uncategorised"
    agrees = bool(rule) and category == request_type

    reasons: list[str] = []
    if policy.flag_missing_fields and issues:
        reasons.append(
            "A person needs to look at this because some required information is missing or not valid: "
            + ", ".join(issues)
            + "."
        )
    if summary and policy.flag_category_mismatch and not rule:
        reasons.append(
            "A person needs to look at this because the summary did not match any category rule, so the desk could not choose a category."
        )
    elif policy.flag_category_mismatch and rule and request_type and category != request_type:
        reasons.append(
            f"A person needs to look at this because the summary looks like {category}, but the request was submitted as {request_type}."
        )
    if policy.flag_high_priority and priority.lower() == "high":
        reasons.append("A person needs to look at this because the priority is High.")
    if policy.flag_completed and status.lower() == "completed":
        reasons.append(
            "A person needs to look at this because the request is already marked Completed, so a new acknowledgement may not be appropriate."
        )
    summary_l = summary.lower()
    seen_phrases: set[str] = set()
    for phrase in policy.sensitive_keywords:
        cleaned = phrase.strip()
        key = cleaned.lower()
        if cleaned and key not in seen_phrases and key in summary_l:
            seen_phrases.add(key)
            reasons.append(
                f'A person needs to look at this because the summary mentions "{cleaned}", which this desk treats as sensitive.'
            )

    values = {
        "request_id": request_id or "this request",
        "category": category,
        "priority": priority or "an unset priority",
        "request_type": request_type or "an unset type",
        "missing_fields": ", ".join(issues) if issues else "none",
        "status": status or "an unset status",
    }

    if issues and policy.templates.get("missing_fields"):
        template = policy.templates["missing_fields"]
    elif status.lower() == "completed" and policy.templates.get("completed"):
        template = policy.templates["completed"]
    elif not rule and policy.templates.get("uncategorised"):
        template = policy.templates["uncategorised"]
    elif rule and request_type and category != request_type and policy.templates.get("mismatch"):
        template = policy.templates["mismatch"]
    else:
        template = (
            policy.templates.get(category)
            or policy.templates.get("default")
            or "We have received {request_id} and will review it."
        )

    return TriageResult(
        missing_fields=issues,
        category=category,
        keyword=keyword,
        category_agrees=agrees,
        acknowledgement=render_template(template, values),
        needs_human_review=bool(reasons),
        review_reasons=reasons,
    )
