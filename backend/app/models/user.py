"""User database model and role enumerations."""
import uuid
import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    Admin = "Admin"
    BrandManager = "BrandManager"
    Creator = "Creator"
    Reviewer = "Reviewer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    role = Column(
        Enum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.Creator
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def name(self) -> str:
        if self.full_name:
            return self.full_name
        return self.email.split("@")[0] if self.email else "User"

    # Relationships
    brands_created = relationship("Brand", back_populates="creator", cascade="all, delete-orphan")
    submissions = relationship("ContentSubmission", back_populates="creator", cascade="all, delete-orphan")
    reviews = relationship("ReviewDecision", back_populates="reviewer", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
