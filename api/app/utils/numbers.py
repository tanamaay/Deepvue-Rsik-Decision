import re
from typing import Optional

CRORE = 10_000_000
LAKH = 100_000

WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "crore": CRORE, "crores": CRORE, "lakh": LAKH, "lakhs": LAKH,
}


def _parse_indian_number(num_str: str) -> float:
    """Parse Indian comma-separated numbers like 1,45,00,000."""
    cleaned = num_str.replace(",", "").strip()
    return float(cleaned)


def _words_to_number(text: str) -> Optional[float]:
    """Parse 'one crore forty-five lakh' style text."""
    words = re.sub(r"[^a-z\s]", " ", text.lower()).split()
    total = 0.0
    current = 0.0
    for word in words:
        if word in ("and", "rupees", "rupee", "inr", "only", "rs"):
            continue
        if word in WORD_TO_NUM:
            val = WORD_TO_NUM[word]
            if val >= 100:
                if current == 0:
                    current = 1
                current *= val
                if val >= LAKH:
                    total += current
                    current = 0
            else:
                current += val
        elif word.isdigit():
            current += float(word)
    total += current
    return total if total > 0 else None


def normalize_inr_amount(text: str) -> Optional[int]:
    """
    Normalize Indian currency expressions to integer INR.
    Handles: Rs. 1.45 crore, ₹1,45,00,000, 14.5 lakh, 45 lakh a month
    """
    if not text or not text.strip():
        return None

    original = text.strip()
    lower = original.lower()

    # Monthly to annual: "45 lakh a month" -> annual
    monthly_match = re.search(
        r"(?:rs\.?|₹|inr)?\s*([\d,]+(?:\.\d+)?)\s*(crore|crores|lakh|lakhs)?\s*(?:a|per)\s*month",
        lower,
    )
    if monthly_match:
        num = float(monthly_match.group(1).replace(",", ""))
        unit = monthly_match.group(2) or ""
        if "crore" in unit:
            monthly_inr = num * CRORE
        else:
            monthly_inr = num * LAKH
        return int(monthly_inr * 12)

    # Rs. 1.45 crore or 1.45 crore
    crore_match = re.search(r"(?:rs\.?|₹|inr)?\s*([\d,]+(?:\.\d+)?)\s*crore", lower)
    if crore_match:
        return int(float(crore_match.group(1).replace(",", "")) * CRORE)

    # 14.5 lakh or Rs. 45 lakh
    lakh_match = re.search(r"(?:rs\.?|₹|inr)?\s*([\d,]+(?:\.\d+)?)\s*lakh", lower)
    if lakh_match:
        return int(float(lakh_match.group(1).replace(",", "")) * LAKH)

    # ₹1,45,00,000 or INR 10,00,000
    symbol_match = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)", lower)
    if symbol_match:
        return int(_parse_indian_number(symbol_match.group(1)))

    # Plain Indian comma number
    comma_match = re.search(r"\b(\d{1,2}(?:,\d{2}){1,3}(?:\.\d+)?)\b", original)
    if comma_match:
        return int(_parse_indian_number(comma_match.group(1)))

    # Word-based: "one crore forty-five lakh"
    if any(w in lower for w in ("crore", "lakh", "hundred")):
        result = _words_to_number(lower)
        if result:
            return int(result)

    # Plain number
    plain = re.search(r"\b(\d+(?:\.\d+)?)\b", original)
    if plain:
        val = float(plain.group(1))
        if val >= 1000:
            return int(val)

    return None
