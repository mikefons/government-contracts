"""Seed the database with a synthetic UK/EU sovereign-procurement dataset.
Idempotent: only seeds when tables are empty."""
from datetime import date
from sqlalchemy import select
from .database import SessionLocal, engine, Base
from . import models as m

OPPS = [
    dict(id="OPP-7741", ref="FTS-2026-0419-AI", title="Sovereign LLM platform for cross-departmental case triage",
         agency="Cabinet Office — CDDO", market="Federal", vehicle="G-Cloud 14", cpv="72212517",
         value=14_500_000, close=date(2026,7,2), incumbent="Faculty AI", region="London",
         desc="Air-gapped large-language-model platform to triage casework across HMPO, DWP and HMRC. Requires UK-hosted inference, full audit trail and OFFICIAL-SENSITIVE handling."),
    dict(id="OPP-7742", ref="DEFS-26-GRAPH-11", title="Graph intelligence layer for logistics network resilience",
         agency="DE&S — Defence Digital", market="Federal", vehicle="DE&S Direct", cpv="72316000",
         value=8_200_000, close=date(2026,6,24), incumbent="None (new requirement)", region="Bristol",
         desc="Temporal graph analytics over the defence supply network to predict single-points-of-failure and surface adversarial interdiction risk. SC clearance mandatory."),
    dict(id="OPP-7743", ref="NHS-SBS-FRWK-882", title="Predictive demand modelling for acute trust bed capacity",
         agency="NHS England", market="SLED", vehicle="NHS SBS", cpv="72246000",
         value=3_400_000, close=date(2026,7,15), incumbent="Palantir (Foundry)", region="Leeds",
         desc="Forecasting model for elective and emergency bed demand across 14 acute trusts. Strong appetite to reduce reliance on single US-hosted vendor."),
    dict(id="OPP-7744", ref="TED-2026-S-118-0337", title="EU border data-fusion & entity-resolution service",
         agency="Frontex", market="EU", vehicle="EU TED", cpv="72314000",
         value=21_000_000, close=date(2026,8,5), incumbent="Sopra Steria", region="Warsaw",
         desc="Entity resolution and link-analysis across Schengen datasets. GDPR-by-design, EU data-residency obligatory, no third-country processing."),
    dict(id="OPP-7745", ref="HO-2026-OSINT-204", title="OSINT collection & risk-scoring for serious organised crime",
         agency="Home Office", market="Federal", vehicle="Tech Services 3", cpv="79330000",
         value=6_700_000, close=date(2026,6,20), incumbent="BAE Systems Digital", region="London",
         desc="Automated open-source collection, deduplication and network risk scoring. Requires explainable scoring and human-in-the-loop adjudication."),
    dict(id="OPP-7746", ref="SCOTGOV-DDS-77", title="Citizen-services conversational assistant (Scots/Gaelic)",
         agency="Scottish Government — DDaS", market="SLED", vehicle="DOS 6", cpv="72413000",
         value=2_100_000, close=date(2026,7,28), incumbent="None (new requirement)", region="Edinburgh",
         desc="Multilingual assistant for devolved citizen services with on-prem hosting and Welsh/Gaelic language support."),
    dict(id="OPP-7747", ref="FTS-2026-0512-CYB", title="Continuous threat-exposure management across critical infra",
         agency="NCSC", market="Federal", vehicle="FTS / OJEU", cpv="72500000",
         value=11_300_000, close=date(2026,7,9), incumbent="Mandiant", region="London",
         desc="Graph-based attack-path analysis over OT/IT estate for CNI operators. Sovereign hosting and supply-chain assurance required."),
    dict(id="OPP-7748", ref="MOD-DSTL-AI-19", title="Causal inference engine for force-readiness analytics",
         agency="Dstl", market="Federal", vehicle="DE&S Direct", cpv="73110000",
         value=4_900_000, close=date(2026,8,19), incumbent="QinetiQ", region="Salisbury",
         desc="Do-calculus causal modelling to estimate intervention effects on readiness. Methodological transparency and reproducibility weighted heavily."),
    dict(id="OPP-7749", ref="WG-DIGI-2026-31", title="Fraud-network detection for grant disbursement",
         agency="Welsh Government", market="SLED", vehicle="Contracts Finder", cpv="72316000",
         value=1_650_000, close=date(2026,7,21), incumbent="None (new requirement)", region="Cardiff",
         desc="Community-detection and anomaly scoring across grant applicant graph to flag collusion rings before disbursement."),
    dict(id="OPP-7750", ref="TED-2026-S-121-0440", title="Pan-EU public-spending transparency knowledge graph",
         agency="European Commission — DIGIT", market="EU", vehicle="EU TED", cpv="72330000",
         value=18_400_000, close=date(2026,9,1), incumbent="Accenture", region="Brussels",
         desc="Unified knowledge graph linking TED awards, beneficial ownership and budget lines across member states. Open-standards and EU-residency mandatory."),
]

AWARDS = [
    dict(ref="FTS-2025-0981", title="Foundry deployment — DHSC analytics", agency="DHSC", vendor="Palantir UK", value=48_500_000, vehicle="FTS / OJEU", co="R. Adeyemi", date=date(2025,11,12)),
    dict(ref="DEFS-25-AI-07", title="Battlespace data platform", agency="DE&S", vendor="Helsing", value=32_000_000, vehicle="DE&S Direct", co="M. Howarth", date=date(2025,9,30)),
    dict(ref="HO-2025-CYB-77", title="Threat intelligence fusion", agency="Home Office", vendor="BAE Systems Digital", value=19_200_000, vehicle="Tech Services 3", co="S. Pillai", date=date(2025,12,4)),
    dict(ref="NHS-SBS-661", title="Population health graph", agency="NHS England", vendor="Faculty AI", value=7_800_000, vehicle="NHS SBS", co="L. Okonkwo", date=date(2026,1,21)),
    dict(ref="GC14-2026-118", title="Sovereign cloud inference", agency="Cabinet Office", vendor="Advanced (CGI)", value=12_400_000, vehicle="G-Cloud 14", co="R. Adeyemi", date=date(2026,2,18)),
    dict(ref="TED-2025-S-204", title="Customs risk engine", agency="HMRC", vendor="Sopra Steria", value=15_600_000, vehicle="FTS / OJEU", co="J. Whitfield", date=date(2025,10,8)),
]

SIGNALS = [
    dict(score=94, title="Treasury confirms £800M sovereign-AI compute allocation",
         body="Spring statement ring-fences capital for UK-hosted inference capacity across departments. Expect framework refreshes on G-Cloud and a wave of pre-market engagement in Q3.",
         tags=["Cabinet Office","Budget","CPV 72212"], when="2 days ago"),
    dict(score=88, title="NHS England signals move away from single-vendor analytics",
         body="Board minutes reference 'reducing concentration risk' in data platforms — a likely precursor to a competitive re-tender of the federated data estate.",
         tags=["NHS England","Pre-solicitation","Re-compete"], when="4 days ago"),
    dict(score=81, title="MOD publishes Defence AI roadmap update",
         body="Renewed emphasis on explainable, auditable models for decision support. RFIs expected through DE&S and Dstl within the quarter.",
         tags=["MOD","Dstl","Policy"], when="6 days ago"),
    dict(score=73, title="EU AI Act high-risk obligations bite for public deployments",
         body="Conformity-assessment requirements now apply to public-sector AI. Vendors with documented audit trails and provenance gain material advantage in TED bids.",
         tags=["EU TED","Compliance","Regulatory"], when="1 week ago"),
    dict(score=67, title="Scottish Government opens DDaS market engagement",
         body="Early-market questionnaire issued for citizen-services AI with explicit on-prem and minority-language requirements.",
         tags=["Scottish Gov","RFI","DOS 6"], when="1 week ago"),
]

BOARD = {
    "Identify": ["OPP-7744", "OPP-7750"],
    "Qualify": ["OPP-7747", "OPP-7746"],
    "Capture": ["OPP-7741", "OPP-7748"],
    "Proposal": ["OPP-7742"],
    "Submitted": ["OPP-7745"],
}

WORKFLOWS = [
    dict(name="New sovereign-AI solicitation alert", enabled=True,
         steps=[["trig","New FTS opportunity"],["","CPV starts 7221"],["","Notify capture team"],["","Draft qualify checklist"]]),
    dict(name="Deadline escalation", enabled=True,
         steps=[["trig","Close date < 7 days"],["","Flag amber on board"],["","Email bid lead"],["","Book go/no-go review"]]),
    dict(name="Incumbent re-compete watch", enabled=False,
         steps=[["trig","Award expiry detected"],["","Pull historical CO contacts"],["","Add to Identify column"]]),
    dict(name="Partner teaming request", enabled=False,
         steps=[["trig","Opportunity > £10M"],["","Match SME partner registry"],["","Open shared workspace"]]),
]


def bootstrap_admin():
    """Create the initial admin from settings if no users exist. Idempotent."""
    from .config import settings
    from .security import hash_password
    db = SessionLocal()
    try:
        if db.scalar(select(m.User).limit(1)):
            return False
        db.add(m.User(
            email=settings.admin_email,
            name="Administrator",
            password_hash=hash_password(settings.admin_password),
            role="admin",
        ))
        db.commit()
        return True
    finally:
        db.close()


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(m.Opportunity).limit(1)):
            return False  # already seeded
        db.add_all(m.Opportunity(**o) for o in OPPS)
        db.add_all(m.Award(**a) for a in AWARDS)
        db.add_all(m.Signal(**s) for s in SIGNALS)
        db.add_all(m.Workflow(**w) for w in WORKFLOWS)
        for stage, ids in BOARD.items():
            for pos, oid in enumerate(ids):
                db.add(m.Pursuit(opportunity_id=oid, stage=stage, position=pos))
        db.commit()
        return True
    finally:
        db.close()


if __name__ == "__main__":
    print("seeded" if seed() else "already seeded")
