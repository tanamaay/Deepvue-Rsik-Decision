import logging
import re

logger = logging.getLogger("deepvue")

PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
GSTIN_PATTERN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b")


def mask_pii(text: str) -> str:
    if not text:
        return text
    text = PAN_PATTERN.sub(lambda m: m.group()[:2] + "****" + m.group()[-1], text)
    text = GSTIN_PATTERN.sub(lambda m: m.group()[:4] + "****" + m.group()[-4:], text)
    return text


def log_info(application_id: str, message: str, **kwargs):
    safe_msg = mask_pii(message)
    extra = " ".join(f"{k}={mask_pii(str(v))}" for k, v in kwargs.items())
    logger.info(f"[application_id={application_id}] {safe_msg} {extra}".strip())


def log_warning(application_id: str, message: str, **kwargs):
    safe_msg = mask_pii(message)
    extra = " ".join(f"{k}={mask_pii(str(v))}" for k, v in kwargs.items())
    logger.warning(f"[application_id={application_id}] {safe_msg} {extra}".strip())


def log_error(application_id: str, message: str, **kwargs):
    safe_msg = mask_pii(message)
    extra = " ".join(f"{k}={mask_pii(str(v))}" for k, v in kwargs.items())
    logger.error(f"[application_id={application_id}] {safe_msg} {extra}".strip())
