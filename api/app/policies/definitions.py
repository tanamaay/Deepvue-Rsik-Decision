KAVERI_POLICY_3_1 = {
    "policy_id": "kaveri",
    "version": "3.1",
    "name": "Kaveri Capital",
    "clauses": {
        "A1": {
            "text": "Business must be incorporated at least 36 months before application date.",
            "type": "incorporation_age",
            "min_months": 36,
        },
        "A2": {
            "text": "GSTIN must be active and returns filed within the last 90 days.",
            "type": "gst_filing_recency",
            "max_days": 90,
        },
        "A3": {
            "text": "Declared turnover must be within 40% of turnover evidenced by verification sources.",
            "type": "turnover_variance",
            "max_variance_pct": 40,
            "direction": "declared_within_evidence",
        },
        "A4": {
            "text": "Loan amount must not exceed 25% of verified annual turnover.",
            "type": "loan_to_turnover",
            "max_pct": 25,
        },
        "A5": {
            "text": "Any address mismatch between registration and operating premises requires REVIEW.",
            "type": "address_mismatch",
            "on_fail": "REVIEW",
        },
        "A6": {
            "text": "Any undisclosed business unit or entity noted during assessment requires REVIEW.",
            "type": "undisclosed_unit",
            "on_fail": "REVIEW",
        },
        "A7": {
            "text": "Failure to verify against the verification source requires REVIEW, never automatic REJECT.",
            "type": "verification_failure",
            "on_fail": "REVIEW",
        },
        "A8": {
            "text": "Sectors excluded entirely: crypto trading, gambling, unregistered lending.",
            "type": "excluded_sector",
            "excluded": ["crypto_trading", "crypto", "gambling", "unregistered_lending", "virtual_digital_assets"],
            "on_fail": "REJECT",
        },
    },
    "silence_rules": {
        "default_undetermined": "REVIEW",
        "turnover_undetermined": "REVIEW",
        "extraction_failure": "REVIEW",
    },
}

KAVERI_POLICY_3_2 = {
    **KAVERI_POLICY_3_1,
    "version": "3.2",
    "clauses": {
        **KAVERI_POLICY_3_1["clauses"],
        "A1": {
            "text": "Business must be incorporated at least 24 months before application date.",
            "type": "incorporation_age",
            "min_months": 24,
        },
    },
}

NEXA_POLICY_1_4 = {
    "policy_id": "nexa",
    "version": "1.4",
    "name": "Nexa Finserv",
    "clauses": {
        "B1": {
            "text": "Business must be incorporated at least 12 months before application date.",
            "type": "incorporation_age",
            "min_months": 12,
        },
        "B2": {
            "text": "GSTIN must be active. Filing recency is not a blocker if turnover is otherwise evidenced.",
            "type": "gst_active",
        },
        "B3": {
            "text": "Declared turnover may exceed evidenced turnover by up to 100% for businesses under 24 months old.",
            "type": "turnover_variance_young",
            "max_variance_pct": 100,
            "young_months": 24,
        },
        "B4": {
            "text": "Loan amount must not exceed 40% of verified annual turnover.",
            "type": "loan_to_turnover",
            "max_pct": 40,
        },
        "B5": {
            "text": "Address mismatch alone is not a blocker.",
            "type": "address_mismatch",
            "on_fail": "PASS",
        },
        "B6": {
            "text": "Undisclosed units are noted but do not require REVIEW unless combined with a turnover discrepancy above B3.",
            "type": "undisclosed_unit",
            "on_fail": "PASS",
        },
        "B7": {
            "text": "If the verification source does not respond, decide on what is available and mark the decision as degraded.",
            "type": "verification_failure",
            "on_fail": "DEGRADED",
        },
        "B8": {
            "text": "Sectors excluded entirely: gambling, unregistered lending.",
            "type": "excluded_sector",
            "excluded": ["gambling", "unregistered_lending"],
            "on_fail": "REJECT",
        },
    },
    "silence_rules": {
        "default_undetermined": "REVIEW",
        "turnover_undetermined": "PASS",
        "extraction_failure": "DEGRADED",
    },
}


def get_policy(policy_id: str, version: str | None = None) -> dict:
    if policy_id == "kaveri":
        if version == "3.2":
            return KAVERI_POLICY_3_2
        return KAVERI_POLICY_3_1
    if policy_id == "nexa":
        return NEXA_POLICY_1_4
    raise ValueError(f"Unknown policy: {policy_id}")
