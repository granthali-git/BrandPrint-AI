"""AuditHistory model for persisting compliance audits, document extractions, and comparisons."""
import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditHistory(Base):
    __tablename__ = "audit_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    session_type = Column(String(50), nullable=False, index=True)  # "SINGLE_AUDIT" | "DUAL_COMPARISON" | "THREE_WAY_COMPARISON" | "CONTRADICTION_CHECK"
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    inputs_payload = Column(JSON, nullable=False, default=dict)
    results_payload = Column(JSON, nullable=False, default=dict)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True)

    user = relationship("User")
    brand = relationship("Brand")

    def __repr__(self) -> str:
        return f"<AuditHistory id={self.id} type={self.session_type} title={self.title[:30]}>"

