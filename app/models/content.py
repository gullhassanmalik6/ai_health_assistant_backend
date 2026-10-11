"""Read-only AI doctor categories, concerns, and health tips."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    ai_title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    icon_key: Mapped[str] = mapped_column(String(64), nullable=False)
    tint_key: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    concerns: Mapped[list[Concern]] = relationship(
        "Concern",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Concern.sort_order",
    )
    health_tips: Mapped[list[HealthTip]] = relationship(
        "HealthTip",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="HealthTip.sort_order",
    )


class Concern(TimestampMixin, Base):
    __tablename__ = "concerns"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    category_slug: Mapped[str] = mapped_column(
        ForeignKey("categories.slug", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    tint_key: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    symptoms: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    suggested_questions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    category: Mapped[Category] = relationship("Category", back_populates="concerns")


class HealthTip(TimestampMixin, Base):
    __tablename__ = "health_tips"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    category_slug: Mapped[str] = mapped_column(
        ForeignKey("categories.slug", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    tint_key: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daily_habits: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    suggested_questions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    category: Mapped[Category] = relationship("Category", back_populates="health_tips")


class DailyTip(TimestampMixin, Base):
    __tablename__ = "daily_tips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
