import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_customer
from app.database import get_db
from app.logging_utils import log_info
from app.models import Application, IdempotencyKey
from app.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationDetail,
    ApplicationListItem,
)
from app.services.worker import process_with_timeout, _resolve_policy_version

router = APIRouter(prefix="/v1/applications", tags=["applications"])


@router.post("", response_model=ApplicationResponse, status_code=202)
async def create_application(
    body: ApplicationCreate,
    customer: dict = Depends(get_customer),
    db: Session = Depends(get_db),
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
):
    customer_id = customer["customer_id"]
    policy_id = customer["policy_id"]
    policy_version = _resolve_policy_version(policy_id)

    if idempotency_key:
        existing = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.customer_id == customer_id,
                IdempotencyKey.key == idempotency_key,
            )
            .first()
        )
        if existing:
            app = db.query(Application).filter(Application.id == existing.application_id).first()
            if app:
                log_info(app.id, "Idempotency key replay — returning existing application")
                return ApplicationResponse(application_id=app.id, status=app.status)

    app = Application(
        customer_id=customer_id,
        policy_id=policy_id,
        policy_version=policy_version,
        status="PROCESSING",
        idempotency_key=idempotency_key,
        payload=body.model_dump(),
    )
    db.add(app)
    db.flush()

    if idempotency_key:
        idem = IdempotencyKey(
            customer_id=customer_id,
            key=idempotency_key,
            application_id=app.id,
        )
        db.add(idem)

    db.commit()
    db.refresh(app)

    log_info(app.id, "Application created", customer_id=customer_id, policy_version=policy_version)

    asyncio.create_task(process_with_timeout(app.id))

    return ApplicationResponse(application_id=app.id, status=app.status)


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(
    application_id: str,
    customer: dict = Depends(get_customer),
    db: Session = Depends(get_db),
):
    app = (
        db.query(Application)
        .filter(
            Application.id == application_id,
            Application.customer_id == customer["customer_id"],
        )
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    return ApplicationDetail(
        application_id=app.id,
        status=app.status,
        customer_id=app.customer_id,
        policy_id=app.policy_id,
        policy_version=app.policy_version,
        payload=app.payload,
        decision=app.decision,
        extraction=app.extraction,
        upstream_calls=app.upstream_calls,
        created_at=app.created_at,
        completed_at=app.completed_at,
    )


@router.get("", response_model=list[ApplicationListItem])
def list_applications(
    customer: dict = Depends(get_customer),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    apps = (
        db.query(Application)
        .filter(Application.customer_id == customer["customer_id"])
        .order_by(Application.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        ApplicationListItem(
            application_id=a.id,
            status=a.status,
            business_name=a.payload.get("business", {}).get("legal_name", "Unknown"),
            created_at=a.created_at,
            completed_at=a.completed_at,
        )
        for a in apps
    ]
