import asyncio
from datetime import datetime, timezone

from app.config import settings
from app.database import SessionLocal
from app.logging_utils import log_info, log_error
from app.models import Application
from app.policies.engine import evaluate_policy
from app.services.extraction import extract_structured_data
from app.services.upstream import upstream_client


def _resolve_policy_version(policy_id: str) -> str:
    if policy_id == "kaveri":
        return settings.kaveri_policy_version
    if policy_id == "nexa":
        return "1.4"
    return "1.0"


async def process_application(application_id: str):
    """Background worker: verify, extract, decide."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            log_error(application_id, "Application not found in worker")
            return

        payload = app.payload
        log_info(application_id, "Starting background processing")

        upstream_calls = []
        upstream_data = None
        upstream_failed = False

        # Step 1: Upstream verification
        gstin = payload.get("business", {}).get("gstin", "")
        applied_on = payload.get("applied_on", "")

        call_result = await upstream_client.verify_gstin(
            gstin=gstin,
            applied_on=applied_on,
            application_id=application_id,
            db=db,
        )
        upstream_calls.append(call_result)

        if call_result["success"]:
            upstream_data = call_result["data"]
        else:
            upstream_failed = True
            log_info(application_id, "Upstream verification failed — proceeding with degraded data")

        # Step 2: AI extraction
        unstructured = payload.get("unstructured", {})
        extraction_result = extract_structured_data(
            field_agent_note=unstructured.get("field_agent_note", ""),
            document_text=unstructured.get("document_text", ""),
            application_id=application_id,
        )

        extraction_failed = not extraction_result.get("success", False) or extraction_result.get("extraction_degraded", False)
        extraction_fields = extraction_result.get("fields", {})
        extraction_concerns = extraction_result.get("concerns", [])

        # Merge concerns into extraction for policy engine
        extraction_for_policy = {**extraction_fields, "concerns": extraction_concerns}

        # Step 3: Policy evaluation
        context = {
            "applied_on": applied_on,
            "business": payload.get("business", {}),
            "loan": payload.get("loan", {}),
            "unstructured": unstructured,
            "upstream_data": upstream_data,
            "upstream_failed": upstream_failed,
            "extraction": extraction_for_policy,
            "extraction_failed": extraction_failed,
        }

        decision = evaluate_policy(app.policy_id, app.policy_version, context)

        # Map outcome to status
        status_map = {
            "APPROVED": "APPROVED",
            "REJECTED": "REJECTED",
            "REVIEW": "REVIEW",
        }
        status = status_map.get(decision["outcome"], "REVIEW")

        if upstream_failed and status == "APPROVED" and app.policy_id == "kaveri":
            status = "REVIEW"
            decision["degraded"] = True
            decision["reasons"].append({
                "clause_id": "A7",
                "clause_text": "Failure to verify requires REVIEW",
                "status": "failed",
                "reason": "Upstream verification failed — decision degraded per policy A7",
            })

        app.status = status
        app.decision = decision
        app.extraction = extraction_result
        app.upstream_calls = upstream_calls
        app.completed_at = datetime.now(timezone.utc)
        app.updated_at = datetime.now(timezone.utc)
        db.commit()

        log_info(application_id, f"Processing complete: {status}", degraded=decision.get("degraded", False))

    except Exception as e:
        log_error(application_id, f"Worker failed: {type(e).__name__}: {e}")
        try:
            app = db.query(Application).filter(Application.id == application_id).first()
            if app:
                app.status = "FAILED"
                app.decision = {
                    "outcome": "FAILED",
                    "error": str(e),
                    "policy_id": app.policy_id,
                    "policy_version": app.policy_version,
                }
                app.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


async def process_with_timeout(application_id: str):
    """Ensure application reaches terminal state within bounded time."""
    try:
        await asyncio.wait_for(
            process_application(application_id),
            timeout=settings.processing_timeout_seconds,
        )
    except asyncio.TimeoutError:
        log_error(application_id, "Processing timed out")
        db = SessionLocal()
        try:
            app = db.query(Application).filter(Application.id == application_id).first()
            if app and app.status == "PROCESSING":
                app.status = "FAILED"
                app.decision = {
                    "outcome": "FAILED",
                    "error": "Processing timed out",
                    "policy_id": app.policy_id,
                    "policy_version": app.policy_version,
                }
                app.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
