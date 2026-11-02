from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Boolean, Integer, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base

class UserRole(str, Enum):
    DONOR = "donor"
    PROJECT_OWNER = "project_owner"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int]