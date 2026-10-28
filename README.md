# TwoSourceCheck — Dual-Source Corroboration Primitive

A standalone Intelligent Contract that attests a claim only when two
independent sources agree on it.

## Why this exists

One source can be wrong, stale, or cherry-picked. Prediction markets,
news verification and DAO proposal checks all face the same question:
"is this confirmed, or did one page just say so?" TwoSourceCheck turns
that into a reusable primitive with a visible audit trail.

1. `submit_claim(statement, url_a, url_b, criteria)` — the claim, both
   sources and the criteria are fixed at submission time.
2. `resolve_claim(claim_id)` — each source is judged in its own
   strict-equality block, and both verdicts are stored separately.
3. The final state is computed by deterministic code, never by asking
   an LLM to reconcile the two verdicts.

## The independence rule

Two pages on the same site are not corroboration. The contract extracts
each URL's domain in deterministic code and rejects a submission whose
two sources share a domain. That check runs before any web or LLM call,
so a bad submission fails cheaply.

## State design

One-way state machine per claim:
`PENDING -> AGREED_SUPPORTED | AGREED_CONTRADICTED | DISAGREEMENT | INSUFFICIENT`

- `AGREED_SUPPORTED`: both sources support the claim.
- `AGREED_CONTRADICTED`: both sources contradict it.
- `DISAGREEMENT`: one supports, the other contradicts. This is a
  terminal state, not an error — downstream builders must treat it as
  "do not act on this claim".
- `INSUFFICIENT`: at least one source says nothing useful about it.

Because `verdict_a` and `verdict_b` are stored, anyone can see *which*
source disagreed, instead of getting a single opaque verdict.

## Try it in GenLayer Studio

1. Paste `contracts/two_source_check.py` into Studio and deploy (no args).
2. `submit_claim` with, for example:
   - statement: `Python is a programming language.`
   - url_a: `https://en.wikipedia.org/wiki/Python_(programming_language)`
   - url_b: `https://www.python.org/`
   - criteria: `Supported only if the page describes Python as a programming language.`
3. `resolve_claim(0)`, then `get_claim(0)` — expect `AGREED_SUPPORTED`
   with both verdicts `SUPPORTED`.

## Tests

See `tests/test_cases.md` (9 cases): domain independence, input
validation, unknown / double resolution, and all four terminal states.
