# DECISIONS.md

## What I'd build differently with three weeks

- **Postgres over SQLite** — SQLite is fine for a demo and single-instance deploy, but stops being fine at concurrent writes from multiple API workers. Postgres with row-level locking would be the first production swap.
- **Dedicated worker process** — Currently background tasks run in the API process via `asyncio.create_task`. A separate worker (even a simple polling loop) would survive API restarts and make retry semantics cleaner.
- **Real LLM extraction with structured output** — I used regex/heuristic extraction for reliability and zero API cost. With three weeks I'd add OpenAI structured outputs as primary, with regex as fallback, and compare grounding quality.
- **Policy DSL** — Policies are Python dicts evaluated by typed clause handlers. At scale I'd move to a YAML/JSON DSL with a rules engine (like json-rules-engine or custom) so customers can self-serve policy edits.
- **Observability** — Add OpenTelemetry tracing, structured JSON logs shipped to a collector, and a dashboard for upstream failure rates.
- **Deployment** — AWS ECS/Fargate with ALB, RDS Postgres, and Secrets Manager for API keys instead of env vars.

## What I deliberately left out

- CI/CD pipeline
- User signup / admin UI for key management
- Queue cluster (Redis/RabbitMQ) — simple in-process async is sufficient
- Real corporate registry integration
- Agent framework — extraction is deterministic regex, not an agent loop
- Rate limiting on our API (only upstream rate limiting is handled)

## How I handled untrusted model output

Since I used regex-based extraction (not a live LLM in the default path), the trust model is:

- **Ungrounded fields** — Every extracted field must have a `provenance` object with a quoted span from the input. Fields without provenance are flagged in `ungrounded_fields` and excluded from policy evidence.
- **Hostile input** — Regex patterns detect prompt injection attempts (`disregard`, `return approve`, `note to automated reviewer`). These are surfaced as `concerns` with type `hostile_input` and never influence the decision outcome directly — they don't auto-approve.
- **Unparseable** — If extraction returns no fields (empty document), clauses depending on extracted material resolve to `undetermined`, which maps to REVIEW per Kaveri's silence rules or DEGRADED per Nexa's.
- **Model outage** — `MODEL_OUTAGE=true` env var simulates provider unavailability. Extraction returns `extraction_degraded: true`, and policy clauses that need unstructured data resolve to undetermined.

## How policies are represented

Policies are Python dictionaries in `policies/definitions.py` with typed clause handlers in `policies/engine.py`. Each clause has a `type` (e.g., `incorporation_age`, `turnover_variance`) that maps to a deterministic evaluation function.

**Why:** Policies are short (8 clauses each). Python dicts are readable, version-controllable, and produce identical results on every run. No LLM in the decision path.

**At 50 customers with 40-page policies:** This approach breaks down. I'd migrate to:
1. A policy DSL (YAML) stored per customer in the database
2. A generic rules engine that evaluates clauses by type
3. Policy versioning with effective-date pinning (already implemented at intake)
4. A policy editor UI for compliance teams, with clause templates

## How I resolved policy silences

| Silence | Resolution | Rationale |
|---------|-----------|-----------|
| Which failed clauses → REJECT vs REVIEW | Each clause has an explicit `on_fail` action. A8 (excluded sector) → REJECT. A5, A6, A7 → REVIEW. Turnover/incorporation failures → REVIEW (conservative default). | Kaveri is conservative; undetermined inputs shouldn't auto-approve. |
| Undetermined clause inputs | Default to REVIEW for Kaveri, PASS for Nexa turnover undetermined | Recorded in `silence_rules` per policy. Visible in decision reasons. |
| Nexa B5/B6 "not a blocker" | `on_fail: PASS` — clause fails but doesn't affect outcome | Explicit in clause definition. |
| Nexa B7 degraded verification | `on_fail: DEGRADED` — decision proceeds but flagged | Customer can see `degraded: true` in the decision. |

A customer would discover these resolutions by reading the `silence_rules` in the policy definition file, seeing `on_fail` on each clause, and observing the `reasons` array in any decision where a clause was undetermined.

## Tests I'd refuse to ship without

1. **Number normalization** (`test_numbers.py`) — A bug here means wrong turnover comparisons and wrong loan-to-turnover ratios. 9 test cases covering crore, lakh, monthly, Indian commas, and word forms.
2. **Policy engine determinism** (`test_policy.py`) — Same input must produce same output. Kaveri 3.1 vs 3.2 incorporation threshold difference. Crypto exclusion only under Kaveri.
3. **Idempotency and isolation** (`test_idempotency.py`) — Duplicate keys must not create duplicate applications. Customer A cannot read Customer B's data.

## AI tools used 

- **Claude AI (this session)** 
