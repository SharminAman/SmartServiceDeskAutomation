from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    keywords: Mapped[list["RuleKeyword"]] = relationship(
        back_populates="rule",
        cascade="all, delete-orphan",
        order_by="RuleKeyword.id",
    )


class RuleKeyword(Base):
    __tablename__ = "rule_keywords"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(120), nullable=False)
    rule: Mapped[Rule] = relationship(back_populates="keywords")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")


class AllowedValue(Base):
    __tablename__ = "allowed_values"
    __table_args__ = (UniqueConstraint("field_name", "value", name="uq_allowed_field_value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    field_name: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(160), nullable=False)


class RequestRow(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    submitted_date: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    requester_role: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    request_type: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    request_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    priority: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    channel: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    missing_fields: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(200), nullable=False, default="", index=True)
    rule_matched: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    category_agrees: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledgement: Mapped[str] = mapped_column(Text, nullable=False, default="")
    needs_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    review_reasons: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
