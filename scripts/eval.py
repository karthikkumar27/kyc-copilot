"""Run the golden set against a running API and report each case (CLAUDE.md section 13).

Deterministic checks only. A case FAILs on a structural check (forbidden terms, restricted
notice and forced escalation, abstention, expected citation). Expected facts are matched as
exact text, so a paraphrase gives REVIEW (read the answer), not FAIL. The exit code is 1 when any
case FAILs. The gate line covers the cases that must pass 100% (g004, g005, g011, g012).
"""

import argparse
import json
import re
import sys
from pathlib import Path

import httpx

GOLDEN = Path(__file__).resolve().parent.parent / "eval" / "golden" / "kyc_v0.jsonl"
GATE_IDS = ("g004", "g005", "g011", "g012")  # CLAUDE.md 13.2: a single failure blocks


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold())


def check_case(case: dict, resp: dict) -> tuple[list[str], list[str]]:
    """Return (hard failures, expected facts not found as text)."""
    failures = []
    text = _norm(resp["answer"] + " " + resp["suggested_reply"])
    for term in case.get("must_not_contain", []):
        if _norm(term) in text:
            failures.append(f"contains '{term}'")
    behaviour = case["behaviour"]
    if behaviour == "restricted" and not resp["agent_notice"]:
        failures.append("no agent_notice")
    if behaviour in ("restricted", "answer_and_escalate") and not resp["needs_escalation"]:
        failures.append("needs_escalation is false")
    if behaviour == "refuse_insufficient_context":
        if not resp["insufficient_context"]:
            failures.append("insufficient_context is false")
    elif behaviour != "restricted" and resp["insufficient_context"]:
        failures.append("insufficient_context is true")
    cited = case.get("expected_citation")
    if cited and not any(c["filename"].startswith(cited) for c in resp["citations"]):
        failures.append(f"{cited} not cited")
    missing = [f for f in case.get("expected_facts", []) if _norm(f) not in text]
    return failures, missing


def status(failures: list[str], missing: list[str]) -> str:
    return "FAIL" if failures else "REVIEW" if missing else "PASS"


def gate_ok(statuses: dict[str, str]) -> bool:
    return all(statuses.get(case_id) in ("PASS", "REVIEW") for case_id in GATE_IDS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--golden", default=str(GOLDEN))
    args = parser.parse_args()
    lines = Path(args.golden).read_text("utf-8").splitlines()
    cases = [json.loads(line) for line in lines if line.strip()]

    statuses: dict[str, str] = {}
    with httpx.Client(base_url=args.api_url, timeout=90) as client:
        admin = {"X-User-Id": "eval-runner", "X-User-Role": "admin"}
        ready = client.get("/readyz")
        docs = client.get("/documents", headers=admin).json()
        ready_docs = sum(d["status"] == "ready" for d in docs)
        if ready.status_code != 200 or not ready_docs:
            print(f"Not ready: /readyz={ready.status_code}, ready documents={ready_docs}. "
                  "Run `make seed` and wait for the documents to be ready.")
            return 2
        for case in cases:
            headers = {"X-User-Id": "eval-runner", "X-User-Role": case.get("role", "agent")}
            body = {"question": case["question"], "customer_id": case.get("customer_id")}
            response = client.post("/ask", json=body, headers=headers)
            if response.status_code != 200:
                failures, missing, model = [f"HTTP {response.status_code}"], [], "-"
            else:
                result = response.json()
                failures, missing = check_case(case, result)
                model = result["model"] or "no model call"
            statuses[case["id"]] = status(failures, missing)
            notes = failures + [f"fact not found as text: {m}" for m in missing]
            print(f"{case['id']:5} {statuses[case['id']]:7} {case['behaviour']:28} {model:18} "
                  f"{'; '.join(notes)}")

    counts = {s: list(statuses.values()).count(s) for s in ("PASS", "REVIEW", "FAIL")}
    print(f"\nPASS {counts['PASS']}  REVIEW {counts['REVIEW']}  FAIL {counts['FAIL']}  "
          f"(of {len(cases)}; REVIEW = structural checks passed, read the answer)")
    ok = gate_ok(statuses)
    print(f"GATE ({', '.join(GATE_IDS)}): {'OK' if ok else 'BLOCKED'}")
    return 1 if counts["FAIL"] or not ok else 0


if __name__ == "__main__":
    sys.exit(main())
