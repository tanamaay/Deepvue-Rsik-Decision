from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class Business(BaseModel):
    legal_name: str
    pan: str
    gstin: str
    registered_address: str
    declared_annual_turnover_inr: int
    sector: str


class Loan(BaseModel):
    amount_inr: int
    tenure_months: int
    purpose: str


class Unstructured(BaseModel):
    field_agent_note: str = ""
    document_text: str = ""


class ApplicationCreate(BaseModel):
    application_id_external: Optional[str] = None
    applied_on: str
    business: Business
    loan: Loan
    unstructured: Unstructured


class ApplicationResponse(BaseModel):
    application_id: str
    status: str


class ApplicationDetail(BaseModel):
    application_id: str
    status: str
    customer_id: str
    policy_id: str
    policy_version: str
    payload: dict
    decision: Optional[dict] = None
    extraction: Optional[dict] = None
    upstream_calls: Optional[list] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ApplicationListItem(BaseModel):
    application_id: str
    status: str
    business_name: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str
    upstream: dict
    model_provider: dict
    dependencies: dict
