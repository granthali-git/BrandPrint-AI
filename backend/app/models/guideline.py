"""GuidelineRule database model representing vectorized brand rules."""
import uuid
import enum
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RuleCategory(str, enum.Enum):
    tone = "tone"
    fact = "fact"
    prohibited_claim = "prohibited_claim"
    visual = "visual"
    accessibility = "accessibility"
    legal_compliance = "legal_compliance"
    brand_voice = "brand_voice"


class GuidelineRule(Base):
    __tablename__ = "guideline_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(
        Enum(RuleCategory, name="rule_category", native_enum=False),
        nullable=False,
        index=True
    )
    title = Column(String(255), nullable=False)
    rule_text = Column(Text, nullable=False)
    rule_code = Column(String(100), nullable=True, index=True)
    source_file = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    brand = relationship("Brand", back_populates="guideline_rules")
    findings = relationship("Finding", back_populates="rule")

    def __repr__(self) -> str:
        return f"<GuidelineRule id={self.id} title={self.title} category={self.category}>"
