import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes import applications, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Deepvue Risk Decisioning API",
    description="Merchant onboarding and risk decisioning service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications.router)
app.include_router(health.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"service": "deepvue-risk-api", "docs": "/docs"}
