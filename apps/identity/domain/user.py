from datetime import datetime
import enum
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, String, Enum, DateTime, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class UserStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    DISABLED = "DISABLED"

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("identity.users.id"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("identity.roles.id"), primary_key=True)
)

class User(Base):
    __tablename__ : "users"
    __tableargs__ : {"schema" : "identity"}

    id = Column(UUID(as_uuid = True), primary_key = True, default = uuid4)
    organization_id = Column(UUID(as_uuid = True), ForeignKey("identity.organizations.id"), nullable = False)
    keycloak_user_id = Column(UUID(as_uuid = True), unique = True, index = True, nullable = False)
    email = Column(String(320), nullable = False)
    display_name = Column(String(255), nullable = False)
    status = Column(Enum(UserStatus), default = UserStatus.INVITED, index = True, nullable = False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    roles = relationship("Role", secondary=user_roles)


