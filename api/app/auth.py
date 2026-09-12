from fastapi import Header, HTTPException

from app.config import CUSTOMERS


def get_customer(x_api_key: str = Header(..., alias="X-API-Key")) -> dict:
    customer = CUSTOMERS.get(x_api_key)
    if not customer:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {**customer, "api_key": x_api_key}
