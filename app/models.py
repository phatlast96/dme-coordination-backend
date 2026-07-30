from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(64), nullable=False)
    address: Mapped[str] = mapped_column(String(512), nullable=False)
    medicare_enrolled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    medicare_plan: Mapped[str] = mapped_column(String(255), nullable=False)
    equipment: Mapped[str] = mapped_column(String(255), nullable=False)
    pcp_name: Mapped[str] = mapped_column(String(255), nullable=False)
    pcp_clinic: Mapped[str] = mapped_column(String(255), nullable=False)
    pcp_phone: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="intake_loaded")
    billing_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    order_billing_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    coverage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_eta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    patient_owes_share: Mapped[float] = mapped_column(Float, default=0.20, nullable=False)
    status_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    followups: Mapped[list[ScheduledFollowUp]] = relationship(back_populates="case")
    call_logs: Mapped[list[CallLog]] = relationship(back_populates="case")
    supplier_contacts: Mapped[list[SupplierContact]] = relationship(back_populates="case")


class ScheduledFollowUp(Base):
    __tablename__ = "scheduled_followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    party: Mapped[str] = mapped_column(String(32), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped[Case] = relationship(back_populates="followups")


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    followup_id: Mapped[int | None] = mapped_column(ForeignKey("scheduled_followups.id"), nullable=True)
    party: Mapped[str] = mapped_column(String(32), nullable=False)
    to_phone: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_name: Mapped[str] = mapped_column(String(128), nullable=False)
    outcome_json: Mapped[str] = mapped_column(Text, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    transcript_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped[Case] = relationship(back_populates="call_logs")


class SupplierContact(Base):
    __tablename__ = "supplier_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    last_outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    case: Mapped[Case] = relationship(back_populates="supplier_contacts")
