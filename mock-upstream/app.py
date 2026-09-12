import asyncio
import os
import random
from datetime import datetime, timedelta

from fastapi import FastAPI, Query
from pydantic_settings import BaseSettings

app = FastAPI(title="Mock Upstream Verification API")


class Settings(BaseSettings):
    hard_failure_rate: float = 0.30
    hang_rate: float = 0.10
    rate_limit_rate: float = 0.05
    hang_seconds: int = 20
    retry_after_seconds: int = 5


settings = Settings()

FIXTURE_DATA = {
    "29AAFCS4321K1ZP": {
        "gstin": "29AAFCS4321K1ZP",
        "gstin_status": "ACTIVE",
        "legal_name": "Saraswati Traders Private Limited",
        "incorporation_date": "2023-08-11",
        "registered_address": "No. 42, 3rd Cross, Peenya Industrial Area, Bengaluru 560058",
        "annual_turnover_inr": 10200000,
    },
    # Mature business fixture — passes Kaveri A1 (36+ months incorporated)
    "29AAFCS4321K2Z1": {
        "gstin": "29AAFCS4321K2Z1",
        "gstin_status": "ACTIVE",
        "legal_name": "Saraswati Traders Private Limited",
        "incorporation_date": "2020-08-11",
        "registered_address": "No. 42, 3rd Cross, Peenya Industrial Area, Bengaluru 560058",
        "annual_turnover_inr": 10200000,
    },
}


def _compute_days_since_filing(applied_on: str) -> int:
    applied = datetime.strptime(applied_on, "%Y-%m-%d")
    filing_date = applied - timedelta(days=41)
    return (applied - filing_date).days


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/verify")
async def verify(
    gstin: str = Query(...),
    applied_on: str = Query("2026-02-20"),
):
    roll = random.random()

    if roll < settings.hard_failure_rate:
        from fastapi.responses import JSONResponse
        codes = [500, 502, 503]
        return JSONResponse(status_code=random.choice(codes), content={"error": "Service unavailable"})

    if roll < settings.hard_failure_rate + settings.hang_rate:
        await asyncio.sleep(settings.hang_seconds)
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=504, content={"error": "Gateway timeout"})

    if roll < settings.hard_failure_rate + settings.hang_rate + settings.rate_limit_rate:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limited"},
            headers={"Retry-After": str(settings.retry_after_seconds)},
        )

    fixture = FIXTURE_DATA.get(gstin)
    if not fixture:
        return {
            "gstin": gstin,
            "gstin_status": "ACTIVE",
            "legal_name": "Unknown Entity",
            "incorporation_date": "2020-01-01",
            "registered_address": "Unknown",
            "annual_turnover_inr": 5000000,
            "days_since_last_filing": 30,
        }

    data = {**fixture}
    data["days_since_last_filing"] = _compute_days_since_filing(applied_on)
    return data
