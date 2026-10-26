"""ContentSubmission database model representing content submitted for brand verification."""
import uuid
import enum
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ContentType(str, enum.Enum):
    text = "text"
    file = "file"
    url = "url"


class SubmissionStatus(str, enum.Enum):
    draft = "draft"
    analyzing = "analyzing"
    findings_ready = "findings_ready"
    ready_for_review = "ready_for_review"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    changes_required = "changes_required"
    disputed = "disputed"


class ContentSubmission(Base):
    __tablename__ = "content_submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content_type = Column(
        Enum(ContentType, name="content_type", native_enum=False),
        nullable=False,
        default=ContentType.text
    )
    raw_content = Column(Text, nullable=False)
    status = Column(
        Enum(SubmissionStatus, name="submission_status", native_enum=False),
        nullable=False,
        default=SubmissionStatus.draft,
        index=True
    )
    current_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    brand = relationship("Brand", back_populates="submissions")
    creator = relationship("User", back_populates="submissions")
    findings = relationship("Finding", back_populates="submission", cascade="all, delete-orphan")
    review_decisions = relationship("ReviewDecision", back_populates="submission", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ContentSubmission id={self.id} status={self.status} version={self.current_version}>"
