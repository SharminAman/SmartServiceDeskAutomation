"""Write the three sample result files from the same rules the tests use."""

from pathlib import Path

from app.csvio import render_csv
from app.triage import triage
from tests.test_triage import policy, rows_from

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FILES = (
    ("sample_requests.csv", "sample_results.csv"),
    ("test_missing.csv", "test_missing_results.csv"),
    ("test_attention.csv", "test_attention_results.csv"),
)


def record(row: dict[str, str]) -> dict[str, str]:
    result = triage(row, policy())
    return {
        "Request ID": row["request_id"],
        "Submitted Date": row["submitted_date"],
        "Requester Role": row["requester_role"],
        "Request Type": row["request_type"],
        "Request Summary": row["request_summary"],
        "Priority": row["priority"],
        "Channel": row["channel"],
        "Status": row["status"],
        "Category": result.category,
        "Rule Matched": result.keyword,
        "Category Agrees": "Yes" if result.category_agrees else "No",
        "Missing Fields": " | ".join(result.missing_fields),
        "Acknowledgement": result.acknowledgement,
        "Human Intervention Needed": "Yes" if result.needs_human_review else "No",
        "Why Human Intervention Is Needed": " | ".join(result.review_reasons)
        or "No human intervention is needed.",
    }


def main() -> None:
    for source, target in FILES:
        rows = [record(row) for row in rows_from(source)]
        (DATA / target).write_text("\ufeff" + render_csv(rows), encoding="utf-8")
        print(f"Wrote {target} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
