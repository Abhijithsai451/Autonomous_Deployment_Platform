from datetime import datetime
import enum
from uuid import uuid4
from sqlalchemy import Column, ForeignKey, String, Enum, DateTime, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from apps.identity.infrastructure.base import Base

class UserStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    DISABLED = "DISABLED"

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("identity.users.id"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("identity.roles.id"), primary_key=True),
    schema="identity"
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        {"schema": "identity"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    keycloak_user_id = Column(UUID(as_uuid=True), unique=True, index=True, nullable=False)
    email = Column(String(320), nullable=False)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)

    status = Column(Enum(UserStatus, name="user_status", schema="identity"), default=UserStatus.INVITED, index=True,
                    nullable=False)

    timezone = Column(String(64), default="UTC", nullable=True)
    locale = Column(String(16), default="en", nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)  # Added layout property

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    roles = relationship("Role", secondary=user_roles)