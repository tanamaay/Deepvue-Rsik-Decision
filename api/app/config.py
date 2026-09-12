from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", protected_namespaces=())

    database_url: str = "sqlite:///./data/deepvue.db"
    mock_upstream_url: str = "http://localhost:8001"
    model_outage: bool = False
    kaveri_policy_version: str = "3.1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    upstream_max_retries: int = 3
    upstream_timeout_seconds: int = 10
    processing_timeout_seconds: int = 120


settings = Settings()

# Static API keys per customer — customer_id determines policy
CUSTOMERS = {
    "kaveri_key_deepvue_2026": {
        "customer_id": "kaveri_capital",
        "name": "Kaveri Capital",
        "policy_id": "kaveri",
    },
    "nexa_key_deepvue_2026": {
        "customer_id": "nexa_finserv",
        "name": "Nexa Finserv",
        "policy_id": "nexa",
    },
}
