"""Unit and integration tests for BrandPrint AI models, security, and authentication."""
import os
import sys
from datetime import datetime, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.models.user import User, UserRole
from app.models.brand import Brand
from app.models.guideline import GuidelineRule, RuleCategory
from app.models.submission import ContentSubmission, ContentType, SubmissionStatus
from app.models.finding import Finding, SeverityLevel, UserAction
from app.models.review import ReviewDecision, ReviewDecisionType
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.main import app
from tests.conftest import TestingSessionLocal, client




def test_password_hashing():
    raw_password = "SecureBrandPassword123!"
    hashed = get_password_hash(raw_password)
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_lifecycle():
    data = {"sub": "user-uuid-1234", "email": "test@brandprint.ai", "role": "BrandManager"}
    token = create_access_token(data)
    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "user-uuid-1234"
    assert decoded["email"] == "test@brandprint.ai"
    assert decoded["role"] == "BrandManager"
    assert "exp" in decoded


def test_database_models_lifecycle():
    db = TestingSessionLocal()

    # 1. Create User
    user = User(
        email="manager@acme.com",
        hashed_password=get_password_hash("SecretAcmePass!"),
        role=UserRole.BrandManager
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.id is not None
    assert user.role == UserRole.BrandManager

    # 2. Create Brand
    brand = Brand(
        name="Acme Corp",
        description="Global innovation leader in consumer tech",
        created_by=user.id
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    assert brand.id is not None
    assert brand.creator.id == user.id

    # 3. Create GuidelineRule
    rule = GuidelineRule(
        brand_id=brand.id,
        category=RuleCategory.tone,
        title="Active Voice Required",
        rule_text="All marketing copy must maintain an active, forward-looking tone.",
        rule_code="TONE-001",
        source_file="guidelines_2026.pdf",
        is_active=True,
        version=1
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    assert rule.id is not None
    assert rule.category == RuleCategory.tone
    assert rule.brand.name == "Acme Corp"

    # 4. Create ContentSubmission
    submission = ContentSubmission(
        brand_id=brand.id,
        creator_id=user.id,
        content_type=ContentType.text,
        raw_content="Acme delivers revolutionary quantum computing for everyday homes.",
        status=SubmissionStatus.analyzing,
        current_version=1
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    assert submission.id is not None
    assert submission.status == SubmissionStatus.analyzing

    # 5. Create Finding
    finding = Finding(
        submission_id=submission.id,
        version=1,
        rule_id=rule.id,
        severity=SeverityLevel.medium,
        issue_type="Passive Tone",
        flagged_text="quantum computing for everyday homes",
        explanation="Claims about quantum computing must be qualified with regulatory disclosures.",
        cited_quote="quantum computing for everyday homes",
        suggested_fix="quantum computing solutions designed for enterprise and everyday homes",
        user_action=UserAction.pending
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    assert finding.id is not None
    assert finding.severity == SeverityLevel.medium
    assert finding.user_action == UserAction.pending
    assert finding.rule.id == rule.id

    # 6. Create ReviewDecision
    reviewer = User(
        email="reviewer@acme.com",
        hashed_password=get_password_hash("ReviewerPass123!"),
        role=UserRole.Reviewer
    )
    db.add(reviewer)
    db.commit()
    db.refresh(reviewer)

    review = ReviewDecision(
        submission_id=submission.id,
        version=1,
        reviewer_id=reviewer.id,
        decision=ReviewDecisionType.changes_required,
        comment="Please adjust the quantum claim wording as suggested."
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    assert review.id is not None
    assert review.decision == ReviewDecisionType.changes_required
    assert review.reviewer.email == "reviewer@acme.com"

    db.close()


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "http://localhost:5173" in data["cors_origins"]


def test_auth_registration_and_login_flow():
    # Register a new Creator user
    reg_payload = {
        "email": "creator@acme.com",
        "password": "CreatorPassword123!",
        "role": "Creator"
    }
    reg_response = client.post("/auth/register", json=reg_payload)
    assert reg_response.status_code == 201, reg_response.text
    reg_data = reg_response.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "creator@acme.com"
    assert reg_data["user"]["role"] == "Creator"

    token = reg_data["access_token"]

    # Verify /auth/me with Bearer token
    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "creator@acme.com"
    assert me_data["role"] == "Creator"

    # Verify login with JSON credentials
    login_response = client.post(
        "/auth/login",
        json={"email": "creator@acme.com", "password": "CreatorPassword123!"}
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data

    # Verify login failure with wrong password
    bad_login = client.post(
        "/auth/login",
        json={"email": "creator@acme.com", "password": "WrongPassword!"}
    )
    assert bad_login.status_code == 401


def test_role_based_access_control():
    from fastapi import Depends
    from app.core.security import require_role

    # Register BrandManager user
    bm_res = client.post("/auth/register", json={
        "email": "manager_rbac@acme.com",
        "password": "Password123!",
        "role": "BrandManager"
    })
    bm_token = bm_res.json()["access_token"]

    # Register Creator user
    cr_res = client.post("/auth/register", json={
        "email": "creator_rbac@acme.com",
        "password": "Password123!",
        "role": "Creator"
    })
    cr_token = cr_res.json()["access_token"]

    # Define temporary test route requiring BrandManager
    @app.get("/test-brand-manager-only")
    def bm_route(current_user: User = Depends(require_role(UserRole.BrandManager))):
        return {"allowed": True, "email": current_user.email}

    # BrandManager accessing endpoint -> 200
    res_bm = client.get("/test-brand-manager-only", headers={"Authorization": f"Bearer {bm_token}"})
    assert res_bm.status_code == 200
    assert res_bm.json()["allowed"] is True

    # Creator accessing endpoint -> 403 Forbidden
    res_cr = client.get("/test-brand-manager-only", headers={"Authorization": f"Bearer {cr_token}"})
    assert res_cr.status_code == 403

    # Unauthenticated access -> 401 Unauthorized
    res_unauth = client.get("/test-brand-manager-only")
    assert res_unauth.status_code == 401



if __name__ == "__main__":
    print("Running tests directly...")
    test_password_hashing()
    print("[PASS] Password hashing passed")
    test_jwt_token_lifecycle()
    print("[PASS] JWT lifecycle passed")
    test_database_models_lifecycle()
    print("[PASS] Database models lifecycle passed")
    test_health_check_endpoint()
    print("[PASS] Health check endpoint passed")
    test_auth_registration_and_login_flow()
    print("[PASS] Auth registration and login flow passed")
    print("ALL TESTS PASSED SUCCESSFULLY!")
