"""Read and write the request spreadsheet format."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

CANONICAL = {
    "request id": "request_id",
    "submitted date": "submitted_date",
    "requester role": "requester_role",
    "request type": "request_type",
    "request summary": "request_summary",
    "priority": "priority",
    "channel": "channel",
    "status": "status",
}

REQUIRED_KEYS = (
    "request_id",
    "submitted_date",
    "requester_role",
    "request_type",
    "request_summary",
    "priority",
    "channel",
    "status",
)

LABELS = {
    "request_id": "Request ID",
    "submitted_date": "Submitted Date",
    "requester_role": "Requester Role",
    "request_type": "Request Type",
    "request_summary": "Request Summary",
    "priority": "Priority",
    "channel": "Channel",
    "status": "Status",
}

EXPORT_HEADERS = [
    "Request ID",
    "Submitted Date",
    "Requester Role",
    "Request Type",
    "Request Summary",
    "Priority",
    "Channel",
    "Status",
    "Category",
    "Rule Matched",
    "Category Agrees",
    "Missing Fields",
    "Acknowledgement",
    "Human Intervention Needed",
    "Why Human Intervention Is Needed",
]


@dataclass
class ParsedCsv:
    rows: list[dict[str, str]]
    missing_columns: list[str]


def _restore_formula_guard(value: str) -> str:
    if value.startswith("'") and len(value) > 1 and value[1] in "=+-@":
        return value[1:]
    return value


def parse_csv(text: str) -> ParsedCsv:
    sample = text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(sample))
    if not reader.fieldnames:
        return ParsedCsv(rows=[], missing_columns=["Header row"])

    header_map: dict[str, str] = {}
    for name in reader.fieldnames:
        key = CANONICAL.get((name or "").strip().lower())
        if key and name not in header_map:
            header_map[name] = key

    found = set(header_map.values())
    missing = [LABELS[key] for key in REQUIRED_KEYS if key not in found]
    if missing:
        return ParsedCsv(rows=[], missing_columns=missing)

    rows: list[dict[str, str]] = []
    for raw in reader:
        if raw is None:
            continue
        item = {key: "" for key in REQUIRED_KEYS}
        blank = True
        for original, key in header_map.items():
            value = _restore_formula_guard((raw.get(original) or "").strip())
            item[key] = value
            if value:
                blank = False
        if not blank:
            rows.append(item)
    return ParsedCsv(rows=rows, missing_columns=[])


def guard_cell(value: str) -> str:
    if value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def render_csv(records: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_HEADERS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow({key: guard_cell(record.get(key, "")) for key in EXPORT_HEADERS})
    return buffer.getvalue()
