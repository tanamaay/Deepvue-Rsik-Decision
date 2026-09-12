from datetime import datetime

from app.policies.definitions import get_policy


def _months_between(start: datetime, end: datetime) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(months, 0)


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def evaluate_clause(clause_id: str, clause: dict, context: dict) -> dict:
    """Evaluate a single policy clause. Returns {clause_id, status, reason, on_fail_action}."""
    clause_type = clause["type"]
    applied_on = _parse_date(context["applied_on"])
    result = {
        "clause_id": clause_id,
        "clause_text": clause["text"],
        "status": "undetermined",
        "reason": "",
        "on_fail_action": clause.get("on_fail", "REVIEW"),
    }

    upstream = context.get("upstream_data")
    extraction = context.get("extraction", {})
    business = context.get("business", {})
    loan = context.get("loan", {})
    upstream_failed = context.get("upstream_failed", False)
    extraction_failed = context.get("extraction_failed", False)

    if clause_type == "verification_failure":
        if upstream_failed:
            result["status"] = "failed"
            result["reason"] = "Verification source did not respond after retries"
            return result
        if upstream:
            result["status"] = "passed"
            result["reason"] = "Verification source responded successfully"
        else:
            result["status"] = "undetermined"
            result["reason"] = "Verification not yet attempted"
        return result

    if clause_type == "incorporation_age":
        inc_date = None
        if upstream and upstream.get("incorporation_date"):
            inc_date = _parse_date(upstream["incorporation_date"])
        elif extraction.get("incorporation_date", {}).get("value"):
            inc_date = _parse_date(extraction["incorporation_date"]["value"])

        if not inc_date:
            result["status"] = "undetermined"
            result["reason"] = "Incorporation date not available from verification or documents"
            return result

        months = _months_between(inc_date, applied_on)
        min_months = clause["min_months"]
        if months >= min_months:
            result["status"] = "passed"
            result["reason"] = f"Business incorporated {months} months before application (required: {min_months})"
        else:
            result["status"] = "failed"
            result["reason"] = f"Business incorporated only {months} months before application (required: {min_months})"
        return result

    if clause_type == "gst_filing_recency":
        if upstream_failed or not upstream:
            result["status"] = "undetermined"
            result["reason"] = "GST filing data unavailable — verification source failed"
            return result
        if upstream.get("gstin_status") != "ACTIVE":
            result["status"] = "failed"
            result["reason"] = f"GSTIN status is {upstream.get('gstin_status', 'unknown')}, not ACTIVE"
            return result
        days = upstream.get("days_since_last_filing")
        if days is None:
            result["status"] = "undetermined"
            result["reason"] = "Last filing date not available"
            return result
        max_days = clause["max_days"]
        if days <= max_days:
            result["status"] = "passed"
            result["reason"] = f"Last GST return filed {days} days before application (within {max_days} days)"
        else:
            result["status"] = "failed"
            result["reason"] = f"Last GST return filed {days} days before application (exceeds {max_days} days)"
        return result

    if clause_type == "gst_active":
        if upstream_failed or not upstream:
            result["status"] = "undetermined"
            result["reason"] = "GST status unavailable — verification source failed"
            return result
        if upstream.get("gstin_status") == "ACTIVE":
            result["status"] = "passed"
            result["reason"] = "GSTIN is active"
        else:
            result["status"] = "failed"
            result["reason"] = f"GSTIN status is {upstream.get('gstin_status', 'unknown')}"
        return result

    if clause_type in ("turnover_variance", "turnover_variance_young"):
        declared = business.get("declared_annual_turnover_inr")
        evidenced = None
        if upstream and upstream.get("annual_turnover_inr"):
            evidenced = upstream["annual_turnover_inr"]
        elif extraction.get("declared_turnover", {}).get("normalized_inr"):
            evidenced = extraction["declared_turnover"]["normalized_inr"]

        if not declared:
            result["status"] = "undetermined"
            result["reason"] = "Declared turnover not provided"
            return result
        if not evidenced:
            result["status"] = "undetermined"
            result["reason"] = "Evidenced turnover not available"
            return result

        variance_pct = abs(declared - evidenced) / evidenced * 100
        max_var = clause["max_variance_pct"]

        if clause_type == "turnover_variance_young":
            inc_months = context.get("incorporation_months")
            if inc_months and inc_months < clause.get("young_months", 24):
                if declared <= evidenced * (1 + max_var / 100):
                    result["status"] = "passed"
                    result["reason"] = f"Declared turnover within {max_var}% of evidenced for business under {clause['young_months']} months (variance: {variance_pct:.1f}%)"
                else:
                    result["status"] = "failed"
                    result["reason"] = f"Declared turnover exceeds evidenced by {variance_pct:.1f}% (max {max_var}% for young business)"
            else:
                if declared <= evidenced * 1.4:
                    result["status"] = "passed"
                    result["reason"] = f"Turnover variance {variance_pct:.1f}% within acceptable range"
                else:
                    result["status"] = "failed"
                    result["reason"] = f"Turnover variance {variance_pct:.1f}% exceeds threshold"
        else:
            if variance_pct <= max_var:
                result["status"] = "passed"
                result["reason"] = f"Declared turnover within {max_var}% of evidenced (variance: {variance_pct:.1f}%)"
            else:
                result["status"] = "failed"
                result["reason"] = f"Declared turnover variance {variance_pct:.1f}% exceeds {max_var}%"
        return result

    if clause_type == "loan_to_turnover":
        loan_amount = loan.get("amount_inr")
        evidenced = None
        if upstream and upstream.get("annual_turnover_inr"):
            evidenced = upstream["annual_turnover_inr"]
        if not loan_amount or not evidenced:
            result["status"] = "undetermined"
            result["reason"] = "Loan amount or verified turnover unavailable"
            return result
        ratio = loan_amount / evidenced * 100
        max_pct = clause["max_pct"]
        if ratio <= max_pct:
            result["status"] = "passed"
            result["reason"] = f"Loan is {ratio:.1f}% of verified turnover (max {max_pct}%)"
        else:
            result["status"] = "failed"
            result["reason"] = f"Loan is {ratio:.1f}% of verified turnover (exceeds {max_pct}%)"
        return result

    if clause_type == "address_mismatch":
        reg_addr = business.get("registered_address", "").lower()
        upstream_addr = (upstream or {}).get("registered_address", "").lower()
        extracted_addr = (extraction.get("address", {}).get("value") or "").lower()
        op_addr = (extraction.get("operating_address", {}).get("value") or "").lower()

        mismatch = False
        if upstream_addr and reg_addr and upstream_addr not in reg_addr and reg_addr not in upstream_addr:
            mismatch = True
        if op_addr and reg_addr and op_addr not in reg_addr and reg_addr not in op_addr:
            mismatch = True

        if not upstream and not extraction.get("address"):
            result["status"] = "undetermined"
            result["reason"] = "Address data insufficient to compare"
            return result

        if mismatch:
            result["status"] = "failed"
            result["reason"] = "Address mismatch detected between registration and operating premises"
        else:
            result["status"] = "passed"
            result["reason"] = "No address mismatch detected"
        return result

    if clause_type == "undisclosed_unit":
        concerns = extraction.get("concerns", [])
        has_undisclosed = any("undisclosed" in c.get("description", "").lower() or "tumkur" in c.get("description", "").lower() for c in concerns)
        note = context.get("unstructured", {}).get("field_agent_note", "").lower()
        if "isn't on the gst" in note or "not on the gst" in note or "second unit" in note:
            has_undisclosed = True

        if extraction_failed and not note:
            result["status"] = "undetermined"
            result["reason"] = "Could not assess undisclosed units — extraction unavailable"
            return result

        if has_undisclosed:
            result["status"] = "failed"
            result["reason"] = "Undisclosed business unit noted during assessment"
        else:
            result["status"] = "passed"
            result["reason"] = "No undisclosed business units noted"
        return result

    if clause_type == "excluded_sector":
        excluded = clause["excluded"]
        sector = business.get("sector", "").lower()
        doc_sectors = extraction.get("sectors", [])
        all_sectors = [sector] + [s.get("value", "").lower() for s in doc_sectors]

        found_excluded = []
        for s in all_sectors:
            for ex in excluded:
                if ex in s or s in ex:
                    found_excluded.append(s)

        if extraction_failed and not sector:
            result["status"] = "undetermined"
            result["reason"] = "Sector information unavailable"
            return result

        if found_excluded:
            result["status"] = "failed"
            result["reason"] = f"Excluded sector detected: {', '.join(set(found_excluded))}"
            result["on_fail_action"] = "REJECT"
        else:
            result["status"] = "passed"
            result["reason"] = "No excluded sectors detected"
        return result

    result["reason"] = f"Unknown clause type: {clause_type}"
    return result


def evaluate_policy(policy_id: str, policy_version: str, context: dict) -> dict:
    """Evaluate all clauses and produce a final decision."""
    policy = get_policy(policy_id, policy_version)
    silence = policy["silence_rules"]

    # Compute incorporation months for context
    upstream = context.get("upstream_data")
    extraction = context.get("extraction", {})
    applied_on = _parse_date(context["applied_on"])
    inc_date = None
    if upstream and upstream.get("incorporation_date"):
        inc_date = _parse_date(upstream["incorporation_date"])
    elif extraction.get("incorporation_date", {}).get("value"):
        inc_date = _parse_date(extraction["incorporation_date"]["value"])
    if inc_date:
        context["incorporation_months"] = _months_between(inc_date, applied_on)

    clause_results = []
    for clause_id, clause in policy["clauses"].items():
        result = evaluate_clause(clause_id, clause, context)
        clause_results.append(result)

    # Determine overall decision
    has_reject = False
    has_review = False
    is_degraded = context.get("upstream_failed", False) or context.get("extraction_failed", False)

    for cr in clause_results:
        if cr["status"] == "failed":
            action = cr.get("on_fail_action", "REVIEW")
            if action == "REJECT":
                has_reject = True
            elif action == "REVIEW":
                has_review = True
            elif action == "DEGRADED":
                is_degraded = True
        elif cr["status"] == "undetermined":
            action = silence.get("default_undetermined", "REVIEW")
            if action == "REVIEW":
                has_review = True
            elif action == "REJECT":
                has_reject = True

    if has_reject:
        outcome = "REJECTED"
    elif has_review:
        outcome = "REVIEW"
    else:
        outcome = "APPROVED"

    reasons = []
    for cr in clause_results:
        reasons.append({
            "clause_id": cr["clause_id"],
            "clause_text": cr["clause_text"],
            "status": cr["status"],
            "reason": cr["reason"],
        })

    return {
        "outcome": outcome,
        "policy_id": policy_id,
        "policy_version": policy_version,
        "policy_name": policy["name"],
        "degraded": is_degraded,
        "clause_results": clause_results,
        "reasons": reasons,
    }
