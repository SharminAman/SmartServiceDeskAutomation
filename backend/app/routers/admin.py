from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, selectinload

from app.auth import current_user
from app.db import get_db
from app.models import AdminUser, AllowedValue, Rule, RuleKeyword, Setting, Template

router = APIRouter(prefix="/api/admin", tags=["admin"])

SPECIAL_TEMPLATES = ("missing_fields", "completed", "uncategorised", "mismatch", "default")


class RuleIn(BaseModel):
    category: str = Field(max_length=160)
    enabled: bool = True
    keywords: list[str] = Field(default_factory=list)


class RulesIn(BaseModel):
    rules: list[RuleIn]


class TemplateIn(BaseModel):
    template_key: str = Field(max_length=160)
    body: str = Field(max_length=2000)


class TemplatesIn(BaseModel):
    templates: list[TemplateIn]


class SettingsIn(BaseModel):
    flag_missing_fields: bool
    flag_category_mismatch: bool
    flag_high_priority: bool
    flag_completed: bool
    sensitive_keywords: list[str] = Field(default_factory=list)
    summary_min_length: int = Field(default=15, ge=0, le=500)


class ListsIn(BaseModel):
    priorities: list[str]
    channels: list[str]
    statuses: list[str]
    request_types: list[str]


def _clean_terms(values: list[str], label: str, required: bool = True) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = value.strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        cleaned.append(text)
    if required and not cleaned:
        raise HTTPException(status_code=400, detail=f"Keep at least one {label}")
    return cleaned


def policy_payload(db: Session) -> dict:
    rules = db.query(Rule).options(selectinload(Rule.keywords)).order_by(Rule.sort_order, Rule.id).all()
    templates = db.query(Template).order_by(Template.id).all()
    settings = {row.key: row.value for row in db.query(Setting).all()}
    lists: dict[str, list[str]] = {"priority": [], "channel": [], "status": [], "request_type": []}
    for row in db.query(AllowedValue).order_by(AllowedValue.id).all():
        lists.setdefault(row.field_name, []).append(row.value)
    phrases = [part.strip() for part in settings.get("sensitive_keywords", "").split("|") if part.strip()]
    try:
        minimum = int(settings.get("summary_min_length", "15"))
    except ValueError:
        minimum = 15
    return {
        "rules": [
            {
                "category": rule.category,
                "enabled": rule.enabled,
                "keywords": [item.keyword for item in rule.keywords],
            }
            for rule in rules
        ],
        "templates": [{"template_key": row.template_key, "body": row.body} for row in templates],
        "settings": {
            "flag_missing_fields": settings.get("flag_missing_fields", "true") == "true",
            "flag_category_mismatch": settings.get("flag_category_mismatch", "true") == "true",
            "flag_high_priority": settings.get("flag_high_priority", "true") == "true",
            "flag_completed": settings.get("flag_completed", "true") == "true",
            "sensitive_keywords": phrases,
            "summary_min_length": minimum,
        },
        "lists": {
            "priorities": lists.get("priority", []),
            "channels": lists.get("channel", []),
            "statuses": lists.get("status", []),
            "request_types": lists.get("request_type", []),
        },
    }


@router.get("/policy")
def get_policy(db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    return policy_payload(db)


@router.put("/rules")
def save_rules(body: RulesIn, db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    if len(body.rules) > 40:
        raise HTTPException(status_code=400, detail="Keep the rule list to 40 categories or fewer")
    cleaned: list[tuple[str, bool, list[str]]] = []
    seen: set[str] = set()
    for rule in body.rules:
        category = rule.category.strip()
        if not category:
            raise HTTPException(status_code=400, detail="Every rule needs a category name")
        if category.lower() in seen:
            raise HTTPException(status_code=400, detail=f"{category} is listed twice")
        if category.lower() in {key.lower() for key in SPECIAL_TEMPLATES}:
            raise HTTPException(status_code=400, detail=f"{category} is reserved for a shared template")
        seen.add(category.lower())
        keywords = _clean_terms(rule.keywords, f"keyword on {category}")
        cleaned.append((category, rule.enabled, keywords[:30]))

    db.query(RuleKeyword).delete(synchronize_session=False)
    db.query(Rule).delete(synchronize_session=False)
    db.flush()
    for index, (category, enabled, keywords) in enumerate(cleaned):
        row = Rule(category=category, enabled=enabled, sort_order=index)
        row.keywords = [RuleKeyword(keyword=keyword) for keyword in keywords]
        db.add(row)
        exists = db.query(Template).filter(Template.template_key == category).one_or_none()
        if exists is None:
            db.add(
                Template(
                    template_key=category,
                    body=(
                        "We have received {request_id}. Your "
                        + category
                        + " request is logged and will be reviewed."
                    ),
                )
            )
    db.commit()
    return policy_payload(db)


@router.put("/templates")
def save_templates(body: TemplatesIn, db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    cleaned: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in body.templates:
        key = item.template_key.strip()
        text = item.body.strip()
        if not key:
            raise HTTPException(status_code=400, detail="Every template needs a name")
        if not text:
            raise HTTPException(status_code=400, detail=f"The {key} template is empty")
        if key.lower() in seen:
            raise HTTPException(status_code=400, detail=f"{key} is listed twice")
        seen.add(key.lower())
        cleaned.append((key, text))
    missing = [key for key in SPECIAL_TEMPLATES if key.lower() not in seen]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Keep these shared templates: " + ", ".join(missing),
        )
    db.query(Template).delete()
    for key, text in cleaned:
        db.add(Template(template_key=key, body=text))
    db.commit()
    return policy_payload(db)


@router.put("/settings")
def save_settings(body: SettingsIn, db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    phrases = _clean_terms(body.sensitive_keywords, "sensitive phrase", required=False)
    values = {
        "flag_missing_fields": "true" if body.flag_missing_fields else "false",
        "flag_category_mismatch": "true" if body.flag_category_mismatch else "false",
        "flag_high_priority": "true" if body.flag_high_priority else "false",
        "flag_completed": "true" if body.flag_completed else "false",
        "sensitive_keywords": "|".join(phrases),
        "summary_min_length": str(body.summary_min_length),
    }
    for key, value in values.items():
        row = db.get(Setting, key)
        if row is None:
            db.add(Setting(key=key, value=value))
        else:
            row.value = value
    db.commit()
    return policy_payload(db)


@router.put("/lists")
def save_lists(body: ListsIn, db: Session = Depends(get_db), _: AdminUser = Depends(current_user)):
    groups = {
        "priority": _clean_terms(body.priorities, "priority"),
        "channel": _clean_terms(body.channels, "channel"),
        "status": _clean_terms(body.statuses, "status"),
        "request_type": _clean_terms(body.request_types, "request type"),
    }
    db.query(AllowedValue).delete()
    for field_name, values in groups.items():
        for value in values:
            db.add(AllowedValue(field_name=field_name, value=value))
    db.commit()
    return policy_payload(db)
