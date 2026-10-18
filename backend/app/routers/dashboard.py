from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.auth import current_user
from app.db import get_db
from app.models import AdminUser, RequestRow, Rule
from app.service import split_reasons, to_api

router = APIRouter(prefix="/api", tags=["desk"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    rows = db.query(RequestRow).order_by(RequestRow.request_code).all()
    rules = db.query(Rule).options(selectinload(Rule.keywords)).order_by(Rule.sort_order, Rule.id).all()
    reason_counts: Counter[str] = Counter()
    for row in rows:
        for reason in split_reasons(row.review_reasons):
            reason_counts[reason] += 1

    def grouped(attr: str) -> list[dict]:
        counts: Counter[str] = Counter(getattr(row, attr) or "Not set" for row in rows)
        return [{"label": label, "count": count} for label, count in counts.most_common()]

    review_rows = [row for row in rows if row.needs_human_review]
    return {
        "total": len(rows),
        "needs_review": len(review_rows),
        "missing": sum(1 for row in rows if row.missing_fields),
        "agreed": sum(1 for row in rows if row.category_agrees),
        "mismatched": sum(1 for row in rows if row.category and not row.category_agrees),
        "by_category": grouped("category"),
        "by_priority": grouped("priority"),
        "by_status": grouped("status"),
        "by_channel": grouped("channel"),
        "review_reasons": [{"label": label, "count": count} for label, count in reason_counts.most_common()],
        "attention": [to_api(row) for row in review_rows[:6]],
        "rules": [
            {
                "category": rule.category,
                "enabled": rule.enabled,
                "keywords": [item.keyword for item in rule.keywords],
            }
            for rule in rules
        ],
    }
