from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLite demo tables."""


class Employee(Base):
    """HR/Finance-only employee records."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(80), index=True)
    compensation_band: Mapped[str] = mapped_column(String(40))
    manager: Mapped[str] = mapped_column(String(120))
    access_group: Mapped[str] = mapped_column(String(40), default="HR_FINANCE", index=True)
    classification: Mapped[str] = mapped_column(String(40), default="confidential")


class Payroll(Base):
    """Restricted payroll data available only to Admin and HR_Finance."""

    __tablename__ = "payroll"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(String(24), index=True)
    period: Mapped[str] = mapped_column(String(20), index=True)
    gross_pay: Mapped[float] = mapped_column(Float)
    tax_withheld: Mapped[float] = mapped_column(Float)
    net_pay: Mapped[float] = mapped_column(Float)
    access_group: Mapped[str] = mapped_column(String(40), default="HR_FINANCE", index=True)
    classification: Mapped[str] = mapped_column(String(40), default="restricted")


class InfrastructureAsset(Base):
    """Engineering/Ops infrastructure inventory."""

    __tablename__ = "infrastructure_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    service_name: Mapped[str] = mapped_column(String(120), index=True)
    environment: Mapped[str] = mapped_column(String(40), index=True)
    owner_team: Mapped[str] = mapped_column(String(80), index=True)
    risk_level: Mapped[str] = mapped_column(String(40), index=True)
    access_group: Mapped[str] = mapped_column(String(40), default="ENGINEERING_OPS", index=True)
    classification: Mapped[str] = mapped_column(String(40), default="internal")


class Incident(Base):
    """Engineering/Ops incident records."""

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    affected_service: Mapped[str] = mapped_column(String(120), index=True)
    root_cause: Mapped[str] = mapped_column(Text)
    remediation: Mapped[str] = mapped_column(Text)
    access_group: Mapped[str] = mapped_column(String(40), default="ENGINEERING_OPS", index=True)
    classification: Mapped[str] = mapped_column(String(40), default="internal")
