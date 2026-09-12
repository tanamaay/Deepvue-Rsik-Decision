import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, Index

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=new_id)
    customer_id = Column(String, nullable=False, index=True)
    policy_id = Column(String, nullable=False)
    policy_version = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PROCESSING")
    idempotency_key = Column(String, nullable=True)
    payload = Column(JSON, nullable=False)
    decision = Column(JSON, nullable=True)
    extraction = Column(JSON, nullable=True)
    upstream_calls = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=utcnow, index=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_customer_idempotency", "customer_id", "idempotency_key", unique=True),
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(String, primary_key=True, default=new_id)
    customer_id = Column(String, nullable=False)
    key = Column(String, nullable=False)
    application_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        Index("ix_idem_customer_key", "customer_id", "key", unique=True),
    )


class UpstreamHealth(Base):
    __tablename__ = "upstream_health"

    id = Column(String, primary_key=True, default="mock_upstream")
    is_healthy = Column(Boolean, default=True)
    last_failure_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(String, default="0")
    last_error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
