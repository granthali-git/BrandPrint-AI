"""Finding database model representing AI-detected brand compliance findings."""
import uuid
import enum
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class SeverityLevel(str, enum.Enum):
    low = "low"
    advisory = "advisory"
    medium = "medium"
    high = "high"
    critical = "critical"


class UserAction(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    edited = "edited"


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("content_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    rule_id = Column(Integer, ForeignKey("guideline_rules.id", ondelete="SET NULL"), nullable=True, index=True)
    severity = Column(
        Enum(SeverityLevel, name="finding_severity", native_enum=False),
        nullable=False,
        default=SeverityLevel.medium,
        index=True
    )
    issue_type = Column(String(100), nullable=False)
    category = Column(String(100), nullable=True)
    flagged_text = Column(Text, nullable=True)
    context_span = Column(Text, nullable=True)
    explanation = Column(Text, nullable=False)
    cited_quote = Column(Text, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    is_visual = Column(Boolean, default=False, nullable=True)
    visual_element = Column(String(255), nullable=True)
    observed_evidence = Column(Text, nullable=True)
    user_action = Column(
        Enum(UserAction, name="user_action", native_enum=False),
        nullable=False,
        default=UserAction.pending
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    submission = relationship("ContentSubmission", back_populates="findings")
    rule = relationship("GuidelineRule", back_populates="findings")

    def __repr__(self) -> str:
        return f"<Finding id={self.id} severity={self.severity} issue_type={self.issue_type}>"
