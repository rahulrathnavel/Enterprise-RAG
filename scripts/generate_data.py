from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.models import Base, Employee, Incident, InfrastructureAsset, Payroll
from src.db.session import build_session_factory, build_sqlite_engine

DATA_DIR = ROOT / "data"
PDF_DIR = DATA_DIR / "raw" / "pdfs"
LOG_DIR = DATA_DIR / "raw" / "logs"
DB_PATH = DATA_DIR / "generated" / "enterprise_demo.db"


def _write_pdf(path: Path, title: str, paragraphs: list[str]) -> None:
    """Create a readable synthetic PDF for ingestion tests and demos."""

    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=letter, title=title)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 14)]
    for paragraph in paragraphs:
        story.append(Paragraph(paragraph, styles["BodyText"]))
        story.append(Spacer(1, 10))
    doc.build(story)


def _seed_sqlite() -> None:
    """Rebuild the SQLite database with deterministic enterprise-like records."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    engine = build_sqlite_engine(DB_PATH)
    Base.metadata.create_all(engine)
    SessionLocal = build_session_factory(engine)

    employees = [
        Employee(employee_id="E-1001", name="Avery Rao", department="Finance", compensation_band="F4", manager="Mina Patel"),
        Employee(employee_id="E-1002", name="Jordan Kim", department="Human Resources", compensation_band="H3", manager="Priya Shah"),
        Employee(employee_id="E-1003", name="Riley Chen", department="Finance", compensation_band="F5", manager="Mina Patel"),
        Employee(employee_id="E-1004", name="Casey Morgan", department="People Operations", compensation_band="H2", manager="Jordan Kim"),
        Employee(employee_id="E-1005", name="Taylor Singh", department="Compensation", compensation_band="H4", manager="Jordan Kim"),
    ]

    payroll = [
        Payroll(employee_id="E-1001", period="2026-Q1", gross_pay=42500.00, tax_withheld=9600.00, net_pay=32900.00),
        Payroll(employee_id="E-1002", period="2026-Q1", gross_pay=35200.00, tax_withheld=7600.00, net_pay=27600.00),
        Payroll(employee_id="E-1003", period="2026-Q1", gross_pay=48750.00, tax_withheld=11200.00, net_pay=37550.00),
        Payroll(employee_id="E-1004", period="2026-Q1", gross_pay=29800.00, tax_withheld=6100.00, net_pay=23700.00),
        Payroll(employee_id="E-1005", period="2026-Q1", gross_pay=39100.00, tax_withheld=8700.00, net_pay=30400.00),
    ]

    assets = [
        InfrastructureAsset(asset_id="ASSET-K8S-001", service_name="payments-api", environment="production", owner_team="platform-sre", risk_level="high"),
        InfrastructureAsset(asset_id="ASSET-K8S-002", service_name="identity-gateway", environment="production", owner_team="security-engineering", risk_level="critical"),
        InfrastructureAsset(asset_id="ASSET-DB-003", service_name="analytics-sqlite-replica", environment="staging", owner_team="data-platform", risk_level="medium"),
        InfrastructureAsset(asset_id="ASSET-NET-004", service_name="edge-vpn", environment="production", owner_team="network-ops", risk_level="high"),
        InfrastructureAsset(asset_id="ASSET-CI-005", service_name="build-orchestrator", environment="development", owner_team="developer-platform", risk_level="low"),
    ]

    incidents = [
        Incident(
            incident_id="INC-2026-041",
            severity="SEV2",
            affected_service="payments-api",
            root_cause="Connection pool exhaustion after a deployment increased database fan-out.",
            remediation="Rolled back deployment, raised pool limits, and added circuit breaker telemetry.",
        ),
        Incident(
            incident_id="INC-2026-052",
            severity="SEV1",
            affected_service="identity-gateway",
            root_cause="Expired signing key caused authentication token validation failures.",
            remediation="Rotated key material, added expiry alerts, and shortened manual approval path.",
        ),
        Incident(
            incident_id="INC-2026-060",
            severity="SEV3",
            affected_service="build-orchestrator",
            root_cause="A runner image pinned to an obsolete package mirror delayed builds.",
            remediation="Updated base image, cached critical packages, and added mirror health checks.",
        ),
    ]

    with SessionLocal() as session:
        session.add_all(employees + payroll + assets + incidents)
        session.commit()


def _seed_pdfs() -> None:
    """Generate PDFs whose names encode the access group used by ingestion."""

    _write_pdf(
        PDF_DIR / "hr_finance_benefits_policy.pdf",
        "HR Benefits Policy",
        [
            "Access Group: HR_FINANCE. This policy describes health benefits, leave eligibility, payroll deductions, dependent coverage, and annual enrollment controls.",
            "Employee compensation bands are reviewed quarterly by Finance and Human Resources. Payroll adjustment requests require manager approval and audit review.",
            "Confidential HR information must be shared only with authorized Admin and HR_Finance users. Engineering and operations teams must not access employee compensation details.",
        ],
    )
    _write_pdf(
        PDF_DIR / "hr_finance_quarterly_controls.pdf",
        "Quarterly Finance Controls",
        [
            "Access Group: HR_FINANCE. Finance performs reconciliations on payroll liabilities, tax withholding, and benefit accrual accounts at quarter close.",
            "Exceptions above the materiality threshold are routed to the controller for review. Supporting evidence is retained for audit readiness.",
            "The policy classifies payroll extracts as restricted data and requires role-based access review before distribution.",
        ],
    )
    _write_pdf(
        PDF_DIR / "engineering_kubernetes_runbook.pdf",
        "Kubernetes Production Runbook",
        [
            "Access Group: ENGINEERING_OPS. The platform team monitors production namespaces, ingress health, pod crash loops, and horizontal pod autoscaler behavior.",
            "For payments-api incidents, first inspect deployment health, connection pool saturation, and database latency metrics before escalating.",
            "Runbook data is internal technical information available to Admin and Engineering_Ops users only.",
        ],
    )
    _write_pdf(
        PDF_DIR / "engineering_incident_response_sop.pdf",
        "Incident Response SOP",
        [
            "Access Group: ENGINEERING_OPS. SEV1 incidents require incident commander assignment, customer-impact assessment, and fifteen-minute executive updates.",
            "Postmortems must document root cause, detection gap, remediation owner, and regression test coverage.",
            "System logs and infrastructure event trails must not be exposed to HR_Finance roles.",
        ],
    )
    _write_pdf(
        PDF_DIR / "shared_enterprise_security_overview.pdf",
        "Enterprise Security Overview",
        [
            "Access Group: SHARED. The company uses least privilege, centralized audit logging, encrypted transport, and security review for privileged systems.",
            "All teams must classify data before ingestion into analytics or AI systems. Restricted data requires explicit approval and audit logging.",
            "This shared overview is visible to Admin, HR_Finance, and Engineering_Ops users.",
        ],
    )


def _seed_logs() -> None:
    """Create JSONL audit logs for the Engineering/Ops silo."""

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "system_audit_logs.jsonl"
    base = datetime(2026, 5, 28, 8, 0, tzinfo=timezone.utc)
    services = ["payments-api", "identity-gateway", "edge-vpn", "build-orchestrator"]
    severities = ["INFO", "WARN", "ERROR"]
    events = [
        ("DEPLOYMENT", "deployment completed with canary checks passing"),
        ("AUTH_FAILURE", "token validation failure exceeded alert threshold"),
        ("CONFIG_CHANGE", "connection pool max_size changed from 40 to 80"),
        ("NETWORK", "vpn tunnel latency crossed production warning threshold"),
        ("RUNTIME_ERROR", "worker traceback observed in queue processor"),
    ]

    with path.open("w", encoding="utf-8") as handle:
        for idx in range(40):
            event_type, message = random.choice(events)
            service = random.choice(services)
            record = {
                "timestamp": (base + timedelta(minutes=idx * 7)).isoformat(),
                "service": service,
                "environment": "production" if idx % 3 else "staging",
                "severity": random.choice(severities),
                "event_type": event_type,
                "actor": f"svc-{service}",
                "ip_address": f"10.24.{idx % 10}.{30 + idx}",
                "message": message,
                "trace_id": f"trace-{idx:04d}",
                "access_group": "ENGINEERING_OPS",
                "classification": "internal",
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def main() -> None:
    random.seed(42)
    _seed_sqlite()
    _seed_pdfs()
    _seed_logs()
    print(f"Generated demo SQLite database: {DB_PATH}")
    print(f"Generated demo PDFs: {PDF_DIR}")
    print(f"Generated demo JSON logs: {LOG_DIR}")


if __name__ == "__main__":
    main()
