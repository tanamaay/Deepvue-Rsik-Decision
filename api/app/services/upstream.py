import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.logging_utils import log_info, log_warning, log_error
from app.models import UpstreamHealth


class UpstreamClient:
    def __init__(self):
        self.base_url = settings.mock_upstream_url
        self.max_retries = settings.upstream_max_retries
        self.timeout = settings.upstream_timeout_seconds
        self._circuit_open = False
        self._consecutive_failures = 0

    async def verify_gstin(
        self,
        gstin: str,
        applied_on: str,
        application_id: str,
        db: Optional[Session] = None,
    ) -> dict[str, Any]:
        call_log = {
            "endpoint": f"{self.base_url}/verify",
            "gstin_masked": gstin[:4] + "****" + gstin[-4:],
            "attempts": [],
            "success": False,
            "data": None,
            "error": None,
        }

        if self._circuit_open:
            call_log["error"] = "Circuit breaker open — upstream marked unhealthy"
            return call_log

        for attempt in range(1, self.max_retries + 1):
            attempt_log = {"attempt": attempt, "started_at": datetime.now(timezone.utc).isoformat()}
            try:
                log_info(application_id, f"Upstream verify attempt {attempt}", gstin_masked=call_log["gstin_masked"])
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}/verify",
                        params={"gstin": gstin, "applied_on": applied_on},
                        timeout=self.timeout,
                    )

                attempt_log["status_code"] = response.status_code
                attempt_log["ended_at"] = datetime.now(timezone.utc).isoformat()

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    attempt_log["retry_after"] = retry_after
                    log_warning(application_id, f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    call_log["attempts"].append(attempt_log)
                    continue

                if response.status_code >= 500:
                    attempt_log["error"] = f"Server error: {response.status_code}"
                    call_log["attempts"].append(attempt_log)
                    backoff = min(2 ** attempt, 10)
                    await asyncio.sleep(backoff)
                    continue

                if response.status_code == 200:
                    call_log["success"] = True
                    call_log["data"] = response.json()
                    call_log["attempts"].append(attempt_log)
                    self._consecutive_failures = 0
                    self._update_health(db, healthy=True)
                    log_info(application_id, "Upstream verify succeeded")
                    return call_log

                attempt_log["error"] = f"Unexpected status: {response.status_code}"
                call_log["attempts"].append(attempt_log)

            except httpx.TimeoutException:
                attempt_log["error"] = "Timeout"
                attempt_log["ended_at"] = datetime.now(timezone.utc).isoformat()
                call_log["attempts"].append(attempt_log)
                log_warning(application_id, f"Upstream timeout on attempt {attempt}")
                backoff = min(2 ** attempt, 10)
                await asyncio.sleep(backoff)

            except (httpx.ConnectError, httpx.RemoteProtocolError) as e:
                attempt_log["error"] = f"Connection error: {type(e).__name__}"
                attempt_log["ended_at"] = datetime.now(timezone.utc).isoformat()
                call_log["attempts"].append(attempt_log)
                log_warning(application_id, f"Upstream connection error on attempt {attempt}")
                backoff = min(2 ** attempt, 10)
                await asyncio.sleep(backoff)

        call_log["error"] = f"All {self.max_retries} attempts failed"
        self._consecutive_failures += 1
        if self._consecutive_failures >= 3:
            self._circuit_open = True
            log_error(application_id, "Circuit breaker opened — upstream unhealthy")
        self._update_health(db, healthy=False, error=call_log["error"])
        return call_log

    def _update_health(self, db: Optional[Session], healthy: bool, error: str = None):
        if not db:
            return
        record = db.query(UpstreamHealth).filter(UpstreamHealth.id == "mock_upstream").first()
        if not record:
            record = UpstreamHealth(id="mock_upstream")
            db.add(record)
        record.is_healthy = healthy
        record.updated_at = datetime.now(timezone.utc)
        if not healthy:
            record.last_failure_at = datetime.now(timezone.utc)
            record.last_error = error
            record.consecutive_failures = str(self._consecutive_failures)
        else:
            record.consecutive_failures = "0"
        db.commit()

    def is_healthy(self) -> bool:
        return not self._circuit_open

    async def check_reachability(self) -> dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=5)
                return {"reachable": response.status_code == 200, "status_code": response.status_code}
        except Exception as e:
            return {"reachable": False, "error": str(e)}


upstream_client = UpstreamClient()
