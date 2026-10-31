"""Data models for AI transparency logging and guideline gap governance."""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AITransparencyLog(Base):
    __tablename__ = "ai_transparency_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    service_provider = Column(String(100), nullable=False)  # "Google Gemini Pro", "Local Ollama", "Tesseract OCR"
    model_name = Column(String(100), nullable=False)        # "gemini-1.5-pro", "llama3:latest", "tesseract-v5"
    redaction_applied = Column(Boolean, default=False, nullable=False)
    redactions_count = Column(Integer, default=0, nullable=False)
    redacted_fields = Column(Text, nullable=True)           # JSON string list e.g. '["email", "phone"]'
    tokens_or_bytes_sent = Column(Integer, default=0, nullable=False)
    prompt_hash = Column(String(64), nullable=True)         # SHA-256 hash
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    submission_id = Column(Integer, ForeignKey("content_submissions.id", ondelete="SET NULL"), nullable=True)

    user = relationship("User")
    submission = relationship("ContentSubmission")

    def __repr__(self) -> str:
        return f"<AITransparencyLog id={self.id} provider={self.service_provider} model={self.model_name}>"


class GuidelineGap(Base):
    __tablename__ = "guideline_gaps"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("content_submissions.id", ondelete="SET NULL"), nullable=True)
    claim = Column(Text, nullable=False)                    # Uncovered marketing statement or ambiguous rule
    gap_type = Column(String(50), nullable=False)           # "UNCOVERED_TOPIC" | "AMBIGUOUS_RULE"
    severity = Column(String(20), default="MEDIUM", nullable=False)  # "MEDIUM" | "HIGH" | "CRITICAL"
    suggested_rule_proposal = Column(Text, nullable=False)  # AI-generated concrete policy proposal
    status = Column(String(50), default="PENDING_DECISION", nullable=False, index=True)  # "PENDING_DECISION" | "ADOPTED" | "DISMISSED" | "REVISED"
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    brand = relationship("Brand")
    submission = relationship("ContentSubmission")

    def __repr__(self) -> str:
        return f"<GuidelineGap id={self.id} type={self.gap_type} status={self.status}>"

