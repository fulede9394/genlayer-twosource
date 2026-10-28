# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import typing


class TwoSourceCheck(gl.Contract):
    """
    TwoSourceCheck - a dual-source corroboration primitive.

    A single source can be wrong, stale, or cherry-picked. This
    contract only attests a claim when two *independent* sources
    agree on it, and it records each source's verdict separately
    so a disagreement is visible instead of being averaged away.

    Independence is enforced in deterministic code, not by
    trusting the submitter: the two source URLs must have
    different domains. Each source is judged in its own
    strict-equality block, so one source's failure cannot
    contaminate the other, and the final state is computed
    from the two verdicts by plain code:

      SUPPORTED + SUPPORTED     -> AGREED_SUPPORTED
      CONTRADICTED + CONTRADICTED -> AGREED_CONTRADICTED
      SUPPORTED + CONTRADICTED  -> DISAGREEMENT
      anything else             -> INSUFFICIENT

    DISAGREEMENT is a terminal state on purpose. It is not a
    failed transaction and it is not a weak "maybe": downstream
    builders must treat it as "do not act on this claim".
    """

    claim_count: u256
    statements: TreeMap[u256, str]
    source_a: TreeMap[u256, str]
    source_b: TreeMap[u256, str]
    criteria_map: TreeMap[u256, str]
    statuses: TreeMap[u256, str]
    verdict_a: TreeMap[u256, str]
    verdict_b: TreeMap[u256, str]

    PENDING = "PENDING"
    AGREED_SUPPORTED = "AGREED_SUPPORTED"
    AGREED_CONTRADICTED = "AGREED_CONTRADICTED"
    DISAGREEMENT = "DISAGREEMENT"
    INSUFFICIENT = "INSUFFICIENT"

    def __init__(self):
        self.claim_count = u256(0)

    def _domain(self, url: str) -> str:
        # https://example.com/path -> example.com
        rest = url[8:]
        slash = rest.find("/")
        if slash == -1:
            return rest
        return rest[:slash]

    @gl.public.write
    def submit_claim(
        self, statement: str, url_a: str, url_b: str, criteria: str
    ) -> int:
        statement = statement.strip()
        url_a = url_a.strip()
        url_b = url_b.strip()
        criteria = criteria.strip()

        assert len(statement) >= 10, "statement too short"
        assert len(statement) <= 500, "statement too long"
        assert url_a.startswith("https://"), "source A must be https"
        assert url_b.startswith("https://"), "source B must be https"
        assert len(url_a) <= 300 and len(url_b) <= 300, "source URL too long"
        assert self._domain(url_a) != self._domain(url_b), (
            "sources must be from different domains: "
            "two pages on the same site are not independent corroboration"
        )
        assert len(criteria) >= 10, "criteria too short"
        assert len(criteria) <= 500, "criteria too long"

        cid = self.claim_count
        self.statements[cid] = statement
        self.source_a[cid] = url_a
        self.source_b[cid] = url_b
        self.criteria_map[cid] = criteria
        self.statuses[cid] = self.PENDING
        self.verdict_a[cid] = ""
        self.verdict_b[cid] = ""
        self.claim_count = cid + u256(1)
        return int(cid)

    @gl.public.write
    def resolve_claim(self, claim_id: int) -> str:
        cid = u256(claim_id)
        assert cid in self.statuses, "unknown claim"
        assert self.statuses[cid] == self.PENDING, "claim already resolved"

        # Copy storage into locals: non-deterministic blocks may not
        # touch contract storage, they may only capture local values.
        statement = self.statements[cid]
        url_a = self.source_a[cid]
        url_b = self.source_b[cid]
        criteria = self.criteria_map[cid]

        # Two separate blocks, not a shared helper: each block
        # captures its own source URL directly from method locals,
        # so the two judgements stay independent.
        def get_verdict_a() -> str:
            page = gl.nondet.web.render(url_a, mode="text")
            prompt = f"""Judge one claim using only the page below.

Claim: {statement}
Criteria for support: {criteria}

Page content:
{page[:4000]}

Reply with exactly one word, nothing else:
SUPPORTED - the page clearly meets the criteria
CONTRADICTED - the page clearly shows the claim is false
INSUFFICIENT - the page does not contain enough information"""
            raw = gl.nondet.exec_prompt(prompt).strip().upper()
            if "CONTRADICTED" in raw:
                return "CONTRADICTED"
            if "SUPPORTED" in raw:
                return "SUPPORTED"
            return "INSUFFICIENT"

        def get_verdict_b() -> str:
            page = gl.nondet.web.render(url_b, mode="text")
            prompt = f"""Judge one claim using only the page below.

Claim: {statement}
Criteria for support: {criteria}

Page content:
{page[:4000]}

Reply with exactly one word, nothing else:
SUPPORTED - the page clearly meets the criteria
CONTRADICTED - the page clearly shows the claim is false
INSUFFICIENT - the page does not contain enough information"""
            raw = gl.nondet.exec_prompt(prompt).strip().upper()
            if "CONTRADICTED" in raw:
                return "CONTRADICTED"
            if "SUPPORTED" in raw:
                return "SUPPORTED"
            return "INSUFFICIENT"

        va = gl.eq_principle.strict_eq(get_verdict_a)
        vb = gl.eq_principle.strict_eq(get_verdict_b)
        self.verdict_a[cid] = va
        self.verdict_b[cid] = vb

        # Deterministic agreement logic. No LLM is asked to
        # reconcile the two verdicts; reconciliation is code.
        if va == "SUPPORTED" and vb == "SUPPORTED":
            final = self.AGREED_SUPPORTED
        elif va == "CONTRADICTED" and vb == "CONTRADICTED":
            final = self.AGREED_CONTRADICTED
        elif {va, vb} == {"SUPPORTED", "CONTRADICTED"}:
            final = self.DISAGREEMENT
        else:
            final = self.INSUFFICIENT

        self.statuses[cid] = final
        return final

    @gl.public.view
    def get_claim(self, claim_id: int) -> typing.Any:
        cid = u256(claim_id)
        assert cid in self.statuses, "unknown claim"
        return {
            "id": claim_id,
            "statement": self.statements[cid],
            "source_a": self.source_a[cid],
            "source_b": self.source_b[cid],
            "criteria": self.criteria_map[cid],
            "status": self.statuses[cid],
            "verdict_a": self.verdict_a[cid],
            "verdict_b": self.verdict_b[cid],
        }

    @gl.public.view
    def get_status(self, claim_id: int) -> str:
        cid = u256(claim_id)
        assert cid in self.statuses, "unknown claim"
        return self.statuses[cid]

    @gl.public.view
    def get_claim_count(self) -> int:
        return int(self.claim_count)
