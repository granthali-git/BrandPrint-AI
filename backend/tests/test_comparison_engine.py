"""Comprehensive test suite for 3-Way Multi-Asset & Version Comparison Engine."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.guideline import GuidelineRule
from app.services.comparison_service import compare_assets_or_texts


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed baseline guideline rules
    r1 = GuidelineRule(
        brand_id=1,
        title="No Absolute Availability Guarantees",
        category="prohibited_claim",
        rule_text="Never state or guarantee 100% uptime, zero downtime, or infallible service without SLA caveats.",
        rule_code="POL-AVAIL-01",
        is_active=True,
    )
    r2 = GuidelineRule(
        brand_id=1,
        title="No Absolute Security Claims",
        category="prohibited_claim",
        rule_text="Never claim zero security breaches or unhackable infrastructure.",
        rule_code="POL-SEC-01",
        is_active=True,
    )
    r3 = GuidelineRule(
        brand_id=1,
        title="No Unverified Accreditations",
        category="prohibited_claim",
        rule_text="Never claim NASA, DoD, or military certifications without clearance.",
        rule_code="POL-CERT-01",
        is_active=True,
    )
    session.add_all([r1, r2, r3])
    session.commit()
    yield session
    session.close()


def test_three_way_comparison_produces_distinct_findings(db_session):
    """Verify that different inputs receive strictly distinct findings, scores, and tone metrics."""
    # Slot A: Baseline with superlatives and uptime claim
    text_a = (
        "Discover AstraForge Enterprise Cloud! We are the cheapest solution and guaranteed "
        "#1 platform on the market with 100% infallible uptime. Call right now to claim "
        "your exclusive 50% limited promotion discount!"
    )
    # Slot B: Extreme claims (100% guaranteed uptime, zero breaches, NASA certified)
    text_b = (
        "AstraForge is the world's number one platform with 100% guaranteed uptime, "
        "zero security breaches, and official NASA certification!"
    )
    # Slot C: Compliant, verified copy
    text_c = (
        "AstraForge Enterprise Cloud delivers high-availability infrastructure engineered "
        "for mission-critical operations. Review our published SOC 2 Type II report and "
        "third-party verified 99.99% uptime metrics."
    )

    res = compare_assets_or_texts(
        db=db_session,
        brand_id=1,
        text_a=text_a,
        text_b=text_b,
        text_c=text_c,
        slot_a={"source_type": "text", "text_content": text_a},
        slot_b={"source_type": "text", "text_content": text_b},
        slot_c={"source_type": "text", "text_content": text_c},
    )

    item_a = res["item_a"]
    item_b = res["item_b"]
    item_c = res["item_c"]

    # 1. Verify separate analysis & distinct findings
    assert item_a is not None
    assert item_b is not None
    assert item_c is not None

    # Slot A and Slot B must have violations detected
    assert item_a["violations_count"] > 0
    assert item_b["violations_count"] > 0

    # Slot C must be significantly cleaner and higher scoring
    assert item_c["score"] > item_a["score"]
    assert item_c["score"] > item_b["score"]
    assert item_c["compliance_level"] == "Clean"

    # Slot B must catch the extreme claims
    flagged_b = [f["flagged_text"].lower() for f in item_b["findings"]]
    assert any("100% guaranteed uptime" in f for f in flagged_b)
    assert any("zero security breaches" in f for f in flagged_b)
    assert any("nasa" in f for f in flagged_b)

    # 2. Verify Best Variant is Slot C
    assert res["best_variant"] == "slot_c"

    # 3. Verify Matrix displays actual, non-identical values
    matrix = res["matrix"]
    score_row = next(r for r in matrix if r["metric"] == "Safety Score")
    assert score_row["slot_c"] != score_row["slot_b"]
    assert score_row["best"] == "slot_c"

    violations_row = next(r for r in matrix if r["metric"] == "Violations Count")
    assert violations_row["slot_c"] < violations_row["slot_b"]
    assert violations_row["best"] == "slot_c"


def test_two_way_comparison_fallback(db_session):
    """Verify fallback behavior for 2-way comparisons without Slot C."""
    text_a = "100% infallible uptime guaranteed #1 cheapest on earth."
    text_b = "Verified 99.99% uptime with published SOC 2 reports."

    res = compare_assets_or_texts(
        db=db_session,
        brand_id=1,
        text_a=text_a,
        text_b=text_b,
        slot_a={"source_type": "text", "text_content": text_a},
        slot_b={"source_type": "text", "text_content": text_b},
    )

    assert res["item_c"] is None
    assert res["best_variant"] == "slot_b"
    assert res["score_delta"] > 0
    assert len(res["results"]) == 2
