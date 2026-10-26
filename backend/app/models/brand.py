"""Brand database model representing a brand workspace."""
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    creator = relationship("User", back_populates="brands_created")
    guideline_rules = relationship("GuidelineRule", back_populates="brand", cascade="all, delete-orphan")
    submissions = relationship("ContentSubmission", back_populates="brand", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Brand id={self.id} name={self.name}>"
