# Test cases (run in GenLayer Studio / direct tests)

## Deterministic — no web or LLM needed
1. Valid claim with two different domains -> id 0, count 1, PENDING.
2. Two URLs on the same domain (e.g. two wikipedia.org pages) -> rejected.
3. Non-https source -> rejected.
4. Statement or criteria shorter than 10 chars -> rejected.
5. `get_claim(99)` on an unknown id -> rejected.
6. Resolving the same claim twice -> second call rejected.

## Non-deterministic — terminal states
7. Both sources support the claim -> AGREED_SUPPORTED, verdict_a and
   verdict_b both SUPPORTED.
8. Both sources contradict the claim -> AGREED_CONTRADICTED.
9. One source supports, the other contradicts -> DISAGREEMENT, with the
   two verdicts stored separately so the disagreement is auditable.
   (A source that says nothing useful leads to INSUFFICIENT, not to a
   forced agree/disagree outcome.)
