from pathlib import Path

from app.csvio import parse_csv, render_csv
from app.triage import Policy, Rule, triage

DATA = Path(__file__).resolve().parents[2] / "data"

RULES = [
    Rule("Access & Permissions", ["access", "permission", "collaborator"], True, 0),
    Rule("System Integration", ["connect", "synchronise", "sync"], True, 1),
    Rule("Process Automation", ["automate", "automated", "reminder"], True, 2),
    Rule("Reporting & Analytics", ["dashboard", "summary", "engagement", "analytics"], True, 3),
    Rule("Content & Guidance", ["guide", "template", "publish", "announcement"], True, 4),
]

TEMPLATES = {
    "Access & Permissions": "We have received {request_id}, an Access & Permissions request, and will review it.",
    "Process Automation": "We have received {request_id}. Your Process Automation request is logged and will be reviewed.",
    "Reporting & Analytics": "We have received {request_id}. Your Reporting & Analytics request is logged and will be reviewed.",
    "System Integration": "We have received {request_id}. Your System Integration request is logged and will be reviewed.",
    "Content & Guidance": "We have received {request_id}. Your Content & Guidance request is logged and will be reviewed.",
    "missing_fields": "We have received {request_id}, but some required information is missing: {missing_fields}.",
    "completed": "{request_id} is already marked completed.",
    "uncategorised": "We have received {request_id}. The summary did not match a category rule.",
    "mismatch": "We have received {request_id}. The summary looks like {category}, which differs from {request_type}.",
    "default": "We have received {request_id} and will review it.",
}


def policy() -> Policy:
    return Policy(
        rules=RULES,
        templates=TEMPLATES,
        sensitive_keywords=["external collaborator", "finance", "expenses"],
        allowed_priorities={"Low", "Medium", "High"},
        allowed_channels={"Service Portal", "Email", "Teams"},
        allowed_statuses={"New", "In Review", "Assigned", "Planned", "In Progress", "Completed"},
        allowed_request_types={rule.category for rule in RULES},
        summary_min_length=15,
    )


def rows_from(name: str) -> list[dict[str, str]]:
    parsed = parse_csv((DATA / name).read_text(encoding="utf-8"))
    assert parsed.missing_columns == []
    return parsed.rows


def test_sample_requests_are_categorised_and_flagged():
    results = [triage(row, policy()) for row in rows_from("sample_requests.csv")]
    categories = [result.category for result in results]
    assert categories == [
        "Access & Permissions",
        "Process Automation",
        "Reporting & Analytics",
        "System Integration",
        "Content & Guidance",
        "Process Automation",
        "Access & Permissions",
        "Reporting & Analytics",
        "System Integration",
        "Content & Guidance",
    ]
    assert all(result.category_agrees for result in results)
    assert all(not result.missing_fields for result in results)
    flagged = [result.needs_human_review for result in results]
    assert flagged == [False, True, False, True, False, True, True, False, True, True]
    assert results[0].keyword == "access"
    assert any("priority is High" in reason for reason in results[1].review_reasons)
    assert any('mentions "finance"' in reason for reason in results[3].review_reasons)
    assert any('mentions "external collaborator"' in reason for reason in results[6].review_reasons)
    assert any("already marked Completed" in reason for reason in results[9].review_reasons)
    assert results[9].acknowledgement.startswith("REQ-010 is already marked completed")
    assert results[0].acknowledgement.startswith("We have received REQ-001")


def test_missing_information_and_invalid_priority():
    result = triage(rows_from("test_missing.csv")[0], policy())
    assert "Request Summary" in result.missing_fields
    assert "Priority (not in the allowed list)" in result.missing_fields
    assert result.category == "Uncategorised"
    assert result.needs_human_review is True
    assert result.acknowledgement.startswith("We have received REQ-101, but some required information is missing")
    assert "Urgent" not in result.acknowledgement or "Priority" in result.acknowledgement


def test_mismatch_high_priority_and_completed():
    mismatch, high, completed = [triage(row, policy()) for row in rows_from("test_attention.csv")]

    assert mismatch.category == "Access & Permissions"
    assert mismatch.category_agrees is False
    assert any("submitted as Content & Guidance" in reason for reason in mismatch.review_reasons)
    assert "looks like Access & Permissions" in mismatch.acknowledgement

    assert high.category == "Process Automation"
    assert high.category_agrees is True
    assert high.review_reasons == ["A person needs to look at this because the priority is High."]

    assert completed.category == "Content & Guidance"
    assert completed.category_agrees is True
    assert completed.review_reasons == [
        "A person needs to look at this because the request is already marked Completed, so a new acknowledgement may not be appropriate."
    ]
    assert completed.acknowledgement.startswith("REQ-203 is already marked completed")


def test_access_is_checked_before_dashboard():
    result = triage(
        {
            "request_id": "REQ-001",
            "submitted_date": "01/10/2026",
            "requester_role": "Student Services Officer",
            "request_type": "Access & Permissions",
            "request_summary": "Request access to the student enquiries dashboard for weekly reporting.",
            "priority": "Medium",
            "channel": "Service Portal",
            "status": "New",
        },
        policy(),
    )
    assert result.category == "Access & Permissions"
    assert result.keyword == "access"


def test_exported_file_can_be_uploaded_again():
    exported = render_csv(
        [
            {
                "Request ID": "REQ-301",
                "Submitted Date": "10/10/2026",
                "Requester Role": "Lecturer",
                "Request Type": "Content & Guidance",
                "Request Summary": "Publish a short guide for new staff.",
                "Priority": "Low",
                "Channel": "Email",
                "Status": "New",
                "Category": "Should be ignored",
                "Rule Matched": "guide",
                "Category Agrees": "Yes",
                "Missing Fields": "",
                "Acknowledgement": "Old sentence",
                "Human Intervention Needed": "No",
                "Why Human Intervention Is Needed": "",
            }
        ]
    )
    parsed = parse_csv(exported)
    assert parsed.missing_columns == []
    assert parsed.rows[0]["request_id"] == "REQ-301"
    assert parsed.rows[0]["request_summary"] == "Publish a short guide for new staff."
    result = triage(parsed.rows[0], policy())
    assert result.category == "Content & Guidance"
    assert result.acknowledgement != "Old sentence"


def test_formula_like_cells_are_guarded_and_restored():
    exported = render_csv(
        [
            {
                "Request ID": "REQ-302",
                "Submitted Date": "10/10/2026",
                "Requester Role": "Lecturer",
                "Request Type": "Reporting & Analytics",
                "Request Summary": "=a weekly summary of enquiries for the team",
                "Priority": "Medium",
                "Channel": "Email",
                "Status": "New",
                "Category": "",
                "Rule Matched": "",
                "Category Agrees": "No",
                "Missing Fields": "",
                "Acknowledgement": "",
                "Human Intervention Needed": "No",
                "Why Human Intervention Is Needed": "",
            }
        ]
    )
    assert "'=a weekly summary" in exported
    parsed = parse_csv(exported)
    assert parsed.rows[0]["request_summary"].startswith("=a weekly summary")
