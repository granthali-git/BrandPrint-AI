"""ReviewDecision database model representing reviewer evaluations."""
import uuid
import enum
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ReviewDecisionType(str, enum.Enum):
    approved = "approved"
    changes_required = "changes_required"
    rejected = "rejected"


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(Integer, ForeignKey("content_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    decision = Column(
        Enum(ReviewDecisionType, name="review_decision_type", native_enum=False),
        nullable=False
    )
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    submission = relationship("ContentSubmission", back_populates="review_decisions")
    reviewer = relationship("User", back_populates="reviews")

    def __repr__(self) -> str:
        return f"<ReviewDecision id={self.id} decision={self.decision} version={self.version}>"
