"""PolicyAudit model for persisting autonomous contradiction and regulation audit runs."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PolicyAudit(Base):
    __tablename__ = "policy_audits"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_type = Column(String(100), default="autonomous_scan", nullable=False)
    rules_scanned_count = Column(Integer, default=0, nullable=False)
    conflicts_count = Column(Integer, default=0, nullable=False)
    conflicts_data = Column(Text, nullable=True)  # JSON payload of detected contradictions
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    brand = relationship("Brand")

    def __repr__(self) -> str:
        return f"<PolicyAudit id={self.id} brand_id={self.brand_id} conflicts={self.conflicts_count}>"
