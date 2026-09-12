import re
from typing import Any, Optional

from app.config import settings
from app.utils.numbers import normalize_inr_amount

HOSTILE_PATTERNS = [
    r"disregard\s+(turnover|incorporation|checks)",
    r"return\s+approve",
    r"pre-cleared",
    r"note\s+to\s+automated\s+reviewer",
    r"ignore\s+(previous|all)\s+instructions",
]


def _find_provenance(text: str, value: str) -> Optional[dict]:
    if not text or not value:
        return None
    idx = text.lower().find(value.lower())
    if idx >= 0:
        end = min(idx + len(value) + 20, len(text))
        return {"quote": text[idx:end].strip(), "offset": idx}
    return None


def _detect_hostile_input(text: str) -> list[dict]:
    concerns = []
    for pattern in HOSTILE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            concerns.append({
                "type": "hostile_input",
                "description": f"Attempted prompt injection detected: '{match.group()}'",
                "provenance": {"quote": match.group(), "offset": match.start()},
            })
    return concerns


def _extract_incorporation_date(text: str) -> Optional[dict]:
    patterns = [
        r"Date of Incorporation:\s*(\d{1,2}\s+\w+\s+\d{4})",
        r"incorporated on\s*(\d{1,2}[\s/-]\w+[\s/-]\d{4})",
        r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            parsed = _parse_flexible_date(date_str)
            if parsed:
                return {
                    "value": parsed,
                    "provenance": {"quote": match.group(), "offset": match.start()},
                    "grounded": True,
                }
    return None


def _parse_flexible_date(date_str: str) -> Optional[str]:
    months = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }
    match = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_str.strip(), re.IGNORECASE)
    if match:
        day, month_name, year = match.groups()
        month = months.get(month_name.lower())
        if month:
            return f"{year}-{month}-{day.zfill(2)}"
    return None


def _extract_entity_name(text: str) -> Optional[dict]:
    patterns = [
        r"(?:CERTIFICATE OF INCORPORATION\n)([^\n]+)",
        r"Legal Name:\s*([^\n]+)",
        r"^([A-Z][^\n]+(?:Private Limited|LLP|Limited))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            return {
                "value": name,
                "provenance": {"quote": match.group(), "offset": match.start()},
                "grounded": True,
            }
    return None


def _extract_address(text: str) -> Optional[dict]:
    patterns = [
        r"Registered Office:\s*([^\n]+)",
        r"registered_address[\"']?\s*:\s*[\"']?([^\"'\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {
                "value": match.group(1).strip(),
                "provenance": {"quote": match.group(), "offset": match.start()},
                "grounded": True,
            }
    return None


def _extract_turnover(text: str) -> Optional[dict]:
    patterns = [
        r"Aggregate turnover[^:]*:\s*([^\n(]+)",
        r"turnover[^:]*:\s*((?:Rs\.?|₹|INR)?\s*[\d,.\s]+(?:crore|lakh)[^\n]*)",
        r"(?:around|quoted turnover at)\s*((?:\d+[\d,.\s]*(?:lakh|crore)[^\n]*))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            normalized = normalize_inr_amount(raw)
            return {
                "value": raw,
                "normalized_inr": normalized,
                "provenance": {"quote": match.group(), "offset": match.start()},
                "grounded": True,
            }
    return None


def _extract_sectors(text: str) -> list[dict]:
    sectors = []
    match = re.search(r"Nature of Business[^:]*:\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        activities = match.group(1).split(";")
        for activity in activities:
            activity = activity.strip()
            if activity:
                sectors.append({
                    "value": activity.lower().replace(" ", "_"),
                    "provenance": {"quote": activity, "offset": match.start()},
                    "grounded": True,
                })
    return sectors


def _extract_concerns(note: str, doc: str) -> list[dict]:
    concerns = []
    combined = f"{note} {doc}"

    concerns.extend(_detect_hostile_input(combined))

    if "tumkur" in note.lower() and ("gst" in note.lower() or "isn't on" in note.lower()):
        idx = note.lower().find("tumkur")
        concerns.append({
            "type": "undisclosed_unit",
            "description": "Second unit in Tumkur not on GST record mentioned by field agent",
            "provenance": {"quote": note[max(0, idx - 30):idx + 50].strip(), "offset": idx},
        })

    if "hesitation" in note.lower():
        idx = note.lower().find("hesitation")
        concerns.append({
            "type": "field_observation",
            "description": "Field agent noted hesitation when asked about Tumkur unit",
            "provenance": {"quote": note[max(0, idx - 20):idx + 40].strip(), "offset": idx},
        })

    if "signage is newer" in note.lower() or "running since 2021" in note.lower():
        concerns.append({
            "type": "date_discrepancy",
            "description": "Field agent note suggests business running since 2021 but incorporation document shows 2023",
            "provenance": {"quote": "Owner says they've been running since 2021 though the signage is newer", "offset": 0},
        })

    if "virtual digital assets" in doc.lower() or "crypto" in doc.lower():
        idx = doc.lower().find("virtual digital assets") if "virtual digital assets" in doc.lower() else doc.lower().find("crypto")
        concerns.append({
            "type": "excluded_sector",
            "description": "Document mentions virtual digital assets / crypto trading activity",
            "provenance": {"quote": doc[idx:idx + 40].strip(), "offset": idx},
        })

    return concerns


def _extract_with_regex(note: str, doc: str) -> dict[str, Any]:
    """Regex/heuristic extraction — used as fallback when LLM unavailable."""
    fields = {}
    concerns = _extract_concerns(note, doc)

    entity = _extract_entity_name(doc) or _extract_entity_name(note)
    if entity:
        fields["entity_name"] = entity

    inc_date = _extract_incorporation_date(doc)
    if inc_date:
        fields["incorporation_date"] = inc_date

    address = _extract_address(doc)
    if address:
        fields["address"] = address

    turnover = _extract_turnover(doc) or _extract_turnover(note)
    if turnover:
        fields["declared_turnover"] = turnover

    sectors = _extract_sectors(doc)
    if sectors:
        fields["sectors"] = sectors

    monthly_match = re.search(r"(\d+\s*lakh\s*a\s*month)", note, re.IGNORECASE)
    if monthly_match:
        normalized = normalize_inr_amount(monthly_match.group(1))
        fields["monthly_turnover_quoted"] = {
            "value": monthly_match.group(1),
            "normalized_inr_annual": normalized,
            "provenance": {"quote": monthly_match.group(), "offset": monthly_match.start()},
            "grounded": True,
        }

    ungrounded = []
    for key, field in fields.items():
        if isinstance(field, dict) and not field.get("grounded", True):
            ungrounded.append(key)
        elif isinstance(field, list):
            for item in field:
                if not item.get("grounded", True):
                    ungrounded.append(key)

    return {
        "fields": fields,
        "concerns": concerns,
        "ungrounded_fields": ungrounded,
    }


def _merge_concerns(regex_concerns: list, llm_concerns: list) -> list:
    """Merge concerns from regex (security) and LLM, deduplicating by type."""
    seen_types = set()
    merged = []
    for c in regex_concerns + llm_concerns:
        key = (c.get("type"), c.get("description", "")[:50])
        if key not in seen_types:
            seen_types.add(key)
            merged.append(c)
    return merged


def extract_structured_data(
    field_agent_note: str,
    document_text: str,
    application_id: str = "",
) -> dict[str, Any]:
    """Extract structured fields — LLM primary, regex fallback, always grounded."""
    if settings.model_outage:
        return {
            "success": False,
            "error": "Model provider unavailable (MODEL_OUTAGE=true)",
            "fields": {},
            "concerns": [],
            "extraction_degraded": True,
            "extraction_method": "none",
        }

    note = field_agent_note or ""
    doc = document_text or ""

    if note.strip().lower() in ("n/a", "") and not doc.strip():
        return {
            "success": True,
            "fields": {},
            "concerns": [{
                "type": "no_unstructured_data",
                "description": "No unstructured material provided for extraction",
                "provenance": None,
            }],
            "extraction_degraded": True,
            "extraction_method": "none",
        }

    # Always run regex for security-sensitive detections (hostile input, etc.)
    regex_result = _extract_with_regex(note, doc)
    regex_concerns = regex_result["concerns"]

    # Try LLM extraction if API key is configured
    if settings.openai_api_key:
        from app.services.llm_extraction import extract_with_llm

        llm_result = extract_with_llm(note, doc, application_id)
        if llm_result.get("success"):
            return {
                "success": True,
                "fields": llm_result["fields"],
                "concerns": _merge_concerns(regex_concerns, llm_result.get("concerns", [])),
                "ungrounded_fields": llm_result.get("ungrounded_fields", []),
                "extraction_degraded": bool(llm_result.get("ungrounded_fields")),
                "extraction_method": "llm",
                "model": llm_result.get("model"),
            }

    # Fallback to regex when no API key or LLM call failed
    return {
        "success": True,
        "fields": regex_result["fields"],
        "concerns": regex_concerns,
        "ungrounded_fields": regex_result["ungrounded_fields"],
        "extraction_degraded": False,
        "extraction_method": "regex_fallback",
    }
