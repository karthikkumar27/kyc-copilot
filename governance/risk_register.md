# Risk register: OWASP Top 10 for LLM Applications (2025)

| # | Risk | How it shows up here | Control | Status |
|---|---|---|---|---|
| LLM01 | Prompt injection | Agent or uploaded SOP tries to override rules | Spotlighting + escaping (`rag/prompting.py`), instruction hierarchy, golden cases g005 | Partial |
| LLM02 | Sensitive info disclosure | IC numbers, names, internal review reasons | PII redaction on ingest and query; deterministic disclosure policy (`kyc/policy.py`) | Partial |
| LLM03 | Supply chain | Unpinned images/deps, unknown models | Model allow-list in gateway; pin images and lock deps (todo) | Todo |
| LLM04 | Data and model poisoning | Malicious SOP upload | Only supervisor/admin can upload; audit log; ingestion scanning (week 4) | Partial |
| LLM05 | Improper output handling | Model output rendered or executed | JSON parsing + validation, citations range-checked, nothing executed | Done |
| LLM06 | Excessive agency | Copilot takes actions | Read-only today; actions only via human approval (week 5) | Done |
| LLM07 | System prompt leakage | Prompt reveals secrets | No secrets in prompts; leak tests in red-team suite (week 4) | Partial |
| LLM08 | Vector and embedding weaknesses | Agent retrieves supervisor-only SOP | Role filter inside SQL before ranking; tenant ID on every chunk; g011/g012 | Done |
| LLM09 | Misinformation | Invented policy | Grounding rules, citations, refusal without context, faithfulness gate | Partial |
| LLM10 | Unbounded consumption | Cost runaway | Upload size limit, gateway retries/timeouts; budgets and rate limits (week 5) | Partial |
