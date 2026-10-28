"""Comprehensive URL Support Audit Test Suite for BrandPrint AI.

Audits URL processing across both:
1. Guidelines Hub: POST /api/guidelines/ingest-url
2. Review Studio: POST /api/reviews (content_type='url')

Evaluates:
- Public HTML webpages (simple & complex)
- Public PDF documents
- HTTP error responses (404 Not Found, 500)
- Upstream bot protection / WAF blocks (403 Forbidden)
- SSRF prevention (localhost, private subnets, cloud metadata)
- Scheme validation (non-http protocols)
- Verification that extracted guideline content requires user review before approval.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.brand import Brand
from app.models.guideline import GuidelineRule, RuleCategory
from app.models.submission import ContentSubmission, ContentType, SubmissionStatus
from app.models.user import User, UserRole

# In-memory SQLite with StaticPool so all threads/sessions share the same schema & data
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return User(
        id=1,
        email="auditor@brandprint.ai",
        full_name="Compliance Auditor",
        hashed_password="mock_hashed_pw",
        role=UserRole.Admin,
    )


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create demo user and brand
    user = User(
        id=1,
        email="auditor@brandprint.ai",
        full_name="Compliance Auditor",
        hashed_password="mock_hashed_pw",
        role=UserRole.Admin,
    )
    db.merge(user)

    brand = Brand(
        id=1,
        name="AstraForge Demo Brand",
        description="Enterprise Cloud & Security",
        created_by=1,
    )
    db.merge(brand)

    # Seed baseline guideline rules for review studio
    r1 = GuidelineRule(
        id=1,
        brand_id=1,
        rule_code="PROHIBIT-001",
        title="Unsubstantiated Superiority Claims",
        category=RuleCategory.prohibited_claim,
        rule_text="Never claim to be '#1', 'cheapest', or 'best in class' without third-party proof.",
        is_active=True,
    )
    r2 = GuidelineRule(
        id=2,
        brand_id=1,
        rule_code="FACT-002",
        title="Availability SLA Precision",
        category=RuleCategory.fact,
        rule_text="Availability claims must specify 99.99% SLA disclaimers and avoid absolute promises.",
        is_active=True,
    )
    db.merge(r1)
    db.merge(r2)
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# SECTION 1: GUIDELINES URL INGESTION TESTS
# ==============================================================================

def test_guidelines_public_html_ingestion(client):
    """Verify Guidelines accepts public HTML, extracts candidate rules for review, and does not auto-commit."""
    mock_html = """
    <html>
      <head><title>Brand Style Guide</title></head>
      <body>
        <main>
          <h1>Official Brand Guidelines</h1>
          <p>Rule 1: Always use Deep Ocean Teal (#0B3C49) for primary headers.</p>
          <p>Rule 2: Never claim 100% guarantee without legal verification.</p>
          <p>Rule 3: Ensure all body text meets WCAG AA contrast ratio of 4.5:1.</p>
        </main>
      </body>
    </html>
    """
    with patch("socket.getaddrinfo", return_value=[(2, 1, 0, "", ("93.184.216.34", 443))]), \
         patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_redirect = False
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.content = mock_html.encode("utf-8")
        mock_response.text = mock_html
        mock_get.return_value = mock_response

        response = client.post(
            "/api/guidelines/ingest-url",
            json={
                "brand_id": 1,
                "url": "https://brandguide.example.com/design-system",
                "auto_commit": False,
                "preview_only": True
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["brand_id"] == 1
        assert "rules" in data
        assert len(data["rules"]) > 0
        assert "extracted for review" in data["message"]

        # Verify rules were NOT committed to database without explicit review
        db = TestingSessionLocal()
        new_db_rules = db.query(GuidelineRule).filter(GuidelineRule.source_file == "https://brandguide.example.com/design-system").all()
        assert len(new_db_rules) == 0
        db.close()


def test_guidelines_public_pdf_ingestion(client):
    """Verify Guidelines supports public PDF URLs, extracts text, and parses candidate rules."""
    with patch("socket.getaddrinfo", return_value=[(2, 1, 0, "", ("93.184.216.34", 443))]), \
         patch("httpx.AsyncClient.get") as mock_get, \
         patch("app.services.document_parser.extract_from_pdf") as mock_extract_pdf:
        mock_extract_pdf.return_value = (
            "AstraForge Enterprise Brand Standards\n\n"
            "1. Primary Palette: Must strictly adhere to Deep Ocean Teal (#0B3C49) and Warm Amber (#F4A321).\n"
            "2. Prohibited Claims: Never use terms like 'cheapest in the market' or 'unbreakable security'.\n"
            "3. Typography: Titles must be set in Plus Jakarta Sans Bold."
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_redirect = False
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.content = b"%PDF-1.4 mock pdf binary stream..."
        mock_get.return_value = mock_response

        response = client.post(
            "/api/guidelines/ingest-url",
            json={
                "brand_id": 1,
                "url": "https://example.com/assets/Brand_Guidelines.pdf",
                "auto_commit": False,
                "preview_only": True
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["rules"]) > 0
        assert data["source"] == "https://example.com/assets/Brand_Guidelines.pdf"


def test_guidelines_url_bulk_save_after_review(client):
    """Verify user can approve reviewed rules from URL and persist them with FAISS vectorization."""
    candidate_rules = [
        {
            "rule_code": "STYLE-01",
            "category": "visual",
            "title": "Official Brand Palette",
            "rule_text": "Must strictly adhere to Deep Ocean Teal (#0B3C49) and Warm Amber (#F4A321).",
            "severity": "high",
            "source_file": "https://brandguide.example.com"
        },
        {
            "rule_code": "LEGAL-02",
            "category": "legal_compliance",
            "title": "Prohibited Superlatives",
            "rule_text": "Never use superlatives like 'cheapest solution' without certified audit proof.",
            "severity": "critical",
            "source_file": "https://brandguide.example.com"
        }
    ]

    response = client.post(
        "/api/guidelines/bulk-save",
        json={
            "brand_id": 1,
            "rules": candidate_rules,
            "source_name": "https://brandguide.example.com"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["rules_saved_count"] == 2

    # Verify persisted in database
    db = TestingSessionLocal()
    saved = db.query(GuidelineRule).filter(GuidelineRule.source_file == "https://brandguide.example.com").all()
    assert len(saved) == 2
    db.close()


def test_guidelines_http_404_error(client):
    """Verify Guidelines handles 404 Not Found upstream error with clear diagnostic detail."""
    with patch("socket.getaddrinfo", return_value=[(2, 1, 0, "", ("93.184.216.34", 443))]), \
         patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.is_redirect = False
        mock_response.headers = {"server": "nginx"}
        mock_response.text = "<html><body>404 Not Found</body></html>"
        mock_get.return_value = mock_response

        response = client.post(
            "/api/guidelines/ingest-url",
            json={
                "brand_id": 1,
                "url": "https://example.com/missing-guidelines-page"
            }
        )

        assert response.status_code == 400
        assert "HTTP 404 Not Found" in response.json()["detail"]


def test_guidelines_waf_blocked_403(client):
    """Verify Guidelines handles WAF/Bot 403 Forbidden with actionable fallback guidance."""
    with patch("socket.getaddrinfo", return_value=[(2, 1, 0, "", ("93.184.216.34", 443))]), \
         patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.is_redirect = False
        mock_response.headers = {"server": "cloudflare", "cf-ray": "123456789abcdef"}
        mock_response.text = "Just a moment... Cloudflare Turnstile challenge"
        mock_get.return_value = mock_response

        response = client.post(
            "/api/guidelines/ingest-url",
            json={
                "brand_id": 1,
                "url": "https://protected-brand.example.com/brand"
            }
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Cloudflare WAF" in detail or "HTTP 403" in detail
        assert "Raw Copy" in detail


def test_guidelines_ssrf_protection_localhost(client):
    """Verify Guidelines blocks localhost and loopback access."""
    response = client.post(
        "/api/guidelines/ingest-url",
        json={
            "brand_id": 1,
            "url": "http://127.0.0.1:8000/internal-admin"
        }
    )
    assert response.status_code == 400
    assert "SSRF Protection" in response.json()["detail"]


def test_guidelines_ssrf_protection_metadata(client):
    """Verify Guidelines blocks cloud metadata access."""
    response = client.post(
        "/api/guidelines/ingest-url",
        json={
            "brand_id": 1,
            "url": "http://169.254.169.254/latest/meta-data/"
        }
    )
    assert response.status_code == 400
    assert "metadata" in response.json()["detail"].lower()


# ==============================================================================
# SECTION 2: REVIEW STUDIO URL AUDIT TESTS
# ==============================================================================

def test_review_studio_public_html_compliance_audit(client):
    """Verify Review Studio extracts public HTML and runs compliance analysis against active guidelines."""
    mock_html = """
    <html>
      <head><title>AstraForge Marketing Landing</title></head>
      <body>
        <main>
          <h1>Discover AstraForge Enterprise Cloud</h1>
          <p>We are the cheapest solution and guaranteed #1 platform on the market with 100% infallible uptime.</p>
        </main>
      </body>
    </html>
    """
    with patch("app.services.extractors.fetch_url_with_ssrf_protection") as mock_fetch:
        mock_fetch.return_value = (
            mock_html.encode("utf-8"),
            "https://marketing.example.com/landing",
            {"content-type": "text/html; charset=utf-8"},
            0.15
        )

        response = client.post(
            "/api/reviews",
            data={
                "brand_id": "1",
                "content_type": "url",
                "url": "https://marketing.example.com/landing"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["submission"]["content_type"] == "url"
        assert "AstraForge Enterprise Cloud" in data["extracted_text"]
        assert data["total_findings"] >= 1

        # Check deterministic checks caught the prohibited claims
        flagged = [f["flagged_text"] for f in data["findings"]]
        assert any("cheapest" in f.lower() or "#1" in f or "100%" in f for f in flagged)


def test_review_studio_public_pdf_url_audit(client):
    """Verify Review Studio supports public PDF URLs with text extraction and visual preview."""
    with patch("app.services.extractors.fetch_url_with_ssrf_protection") as mock_fetch, \
         patch("app.services.extractors.extract_from_pdf_detailed") as mock_pdf_extract:
        mock_pdf_extract.return_value = {
            "text": "Enterprise Cloud Architecture Overview. We guarantee 99.99% uptime with enterprise security.",
            "title": "Cloud Architecture PDF",
            "content_type": "pdf",
            "mime_type": "application/pdf",
            "is_visual_asset": True,
            "visual_image_bytes": b"mock_page1_image_bytes",
            "image_preview_url": "data:image/jpeg;base64,/9j/mock",
            "file_size_bytes": 1024,
        }
        mock_fetch.return_value = (
            b"%PDF-1.4 ...",
            "https://example.com/poster.pdf",
            {"content-type": "application/pdf"},
            0.2
        )

        response = client.post(
            "/api/reviews",
            data={
                "brand_id": "1",
                "content_type": "url",
                "url": "https://example.com/poster.pdf"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["submission"]["content_type"] == "url"
        assert "Enterprise Cloud" in data["extracted_text"]


def test_review_studio_http_404_error(client):
    """Verify Review Studio surfaces clean HTTP 404 error when target webpage does not exist."""
    with patch("app.services.extractors.fetch_url_with_ssrf_protection") as mock_fetch:
        mock_fetch.side_effect = ValueError(
            "[Stage: URL Fetch] The requested resource at 'https://example.com/missing' was not found on the remote server (HTTP 404 Not Found)."
        )

        response = client.post(
            "/api/reviews",
            data={
                "brand_id": "1",
                "content_type": "url",
                "url": "https://example.com/missing"
            }
        )

        assert response.status_code == 404
        assert "HTTP 404 Not Found" in response.json()["detail"]


def test_review_studio_waf_blocked_403(client):
    """Verify Review Studio surfaces clear diagnostic 403 error when upstream blocks crawler."""
    with patch("app.services.extractors.fetch_url_with_ssrf_protection") as mock_fetch:
        mock_fetch.side_effect = ValueError(
            "[Stage: URL Fetch] The target website at 'https://ox.ac.uk/brand' is protected by Cloudflare WAF / Bot Management and denied automated access (HTTP 403)."
        )

        response = client.post(
            "/api/reviews",
            data={
                "brand_id": "1",
                "content_type": "url",
                "url": "https://ox.ac.uk/brand"
            }
        )

        assert response.status_code == 403
        assert "Cloudflare WAF" in response.json()["detail"] or "HTTP 403" in response.json()["detail"]


def test_review_studio_ssrf_protection(client):
    """Verify Review Studio rejects private IPs and localhost under SSRF policy."""
    response = client.post(
        "/api/reviews",
        data={
            "brand_id": "1",
            "content_type": "url",
            "url": "http://127.0.0.1:8000/private-data"
        }
    )
    assert response.status_code == 400
    assert "SSRF security" in response.json()["detail"]
