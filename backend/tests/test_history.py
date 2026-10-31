"""Unit tests for Session & Audit History endpoints and persistence."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.routes.history import (
    save_history_session,
    list_history_sessions,
    get_history_session,
    delete_history_session,
    clear_all_history,
)
from app.schemas.history import HistorySessionCreate


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_history_save_and_retrieve(db_session):
    payload = HistorySessionCreate(
        session_type="SINGLE_AUDIT",
        title="AstraForge Serum Poster vs V2",
        summary="3 Violations Flagged • 65% Safety Score",
        inputs_payload={
            "tab": "file",
            "file_name": "poster_v2.png",
            "extracted_text": "AstraForge Serum guarantees 100% cure for aging.",
        },
        results_payload={
            "compliance_score": 65,
            "total_findings": 3,
            "findings": [
                {
                    "id": "f-1",
                    "rule_name": "No absolute medical claims",
                    "severity": "critical",
                    "quote": "guarantees 100% cure",
                }
            ],
        },
        brand_id=1,
    )

    # 1. Save
    res = save_history_session(payload, db=db_session)
    assert res.status == "saved"
    assert res.id is not None
    session_id = res.id

    # 2. List
    items = list_history_sessions(db=db_session)
    assert len(items) >= 1
    found = next((i for i in items if i.id == session_id), None)
    assert found is not None
    assert found.title == "AstraForge Serum Poster vs V2"
    assert "3 Violations" in found.summary

    # 3. Filter by type
    items_type = list_history_sessions(type="SINGLE_AUDIT", db=db_session)
    assert any(i.id == session_id for i in items_type)

    # 4. Search by keyword
    items_search = list_history_sessions(search="Serum", db=db_session)
    assert any(i.id == session_id for i in items_search)

    # 5. Detail for UI restoration
    detail = get_history_session(session_id, db=db_session)
    assert detail.id == session_id
    assert detail.inputs_payload["file_name"] == "poster_v2.png"
    assert detail.results_payload["compliance_score"] == 65

    # 6. Delete
    deleted = delete_history_session(session_id, db=db_session)
    assert deleted["status"] == "deleted"

    # 7. Check deleted
    with pytest.raises(Exception):
        get_history_session(session_id, db=db_session)


def test_history_comparisons_and_clear(db_session):
    payload = HistorySessionCreate(
        session_type="THREE_WAY_COMPARISON",
        title="Sunscreen SPF 70 Tri-Variant Comparison",
        summary="Slot C Winner • 94% Compliance",
        inputs_payload={
            "slot_a": {"sourceType": "text", "content": "100% infallible sun blocker"},
            "slot_b": {"sourceType": "text", "content": "Broad spectrum SPF 70 protection"},
            "slot_c": {"sourceType": "text", "content": "Dermatologist-tested broad spectrum SPF 70"},
        },
        results_payload={
            "best_variant": "slot_c",
            "best_variant_title": "Slot C",
            "matrix": [
                {"category": "Medical Claims", "slot_a_val": "Violates", "slot_b_val": "Complies", "slot_c_val": "Complies"}
            ],
        },
        brand_id=1,
    )

    res = save_history_session(payload, db=db_session)
    session_id = res.id

    # Filter with COMPARISON category
    comp_items = list_history_sessions(type="COMPARISON", db=db_session)
    assert any(i.id == session_id for i in comp_items)

    # Clear all
    cleared = clear_all_history(db=db_session)
    assert cleared["status"] == "cleared"

    empty_items = list_history_sessions(db=db_session)
    assert len(empty_items) == 0
