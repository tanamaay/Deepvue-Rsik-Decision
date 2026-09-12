import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import UpstreamHealth
from app.schemas import HealthResponse
from app.services.upstream import upstream_client
from app.services.llm_extraction import check_llm_reachability

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    upstream_reachability = await upstream_client.check_reachability()
    upstream_record = db.query(UpstreamHealth).filter(UpstreamHealth.id == "mock_upstream").first()

    upstream_healthy = upstream_client.is_healthy() and upstream_reachability.get("reachable", False)
    if upstream_record and not upstream_record.is_healthy:
        upstream_healthy = False

    llm_status = check_llm_reachability()
    model_available = not settings.model_outage
    model_reachable = llm_status.get("reachable", False) if settings.openai_api_key else True

    overall = "healthy" if upstream_healthy and model_available else "degraded"
    if not upstream_healthy and not model_available:
        overall = "unhealthy"

    return HealthResponse(
        status=overall,
        upstream={
            "name": "mock_upstream",
            "url": settings.mock_upstream_url,
            "healthy": upstream_healthy,
            "reachable": upstream_reachability.get("reachable", False),
            "circuit_breaker_open": not upstream_client.is_healthy(),
            "last_error": upstream_record.last_error if upstream_record else None,
        },
        model_provider={
            "available": model_available,
            "outage_simulated": settings.model_outage,
            "reachable": model_reachable,
            "model": llm_status.get("model", settings.openai_model if settings.openai_api_key else "regex_fallback"),
            "reason": llm_status.get("reason"),
        },
        dependencies={
            "database": "sqlite",
            "kaveri_policy_version": settings.kaveri_policy_version,
        },
    )
