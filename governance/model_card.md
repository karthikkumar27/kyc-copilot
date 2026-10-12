# Model card: KYC Support Copilot (draft v0.1)

**Purpose.** Help human support agents of LimauPay (fictional e-wallet) answer customer questions
about e-KYC verification, grounded in internal SOPs and the live verification status.

**Users.** Trained support agents and supervisors. Not customer-facing: a human reviews and sends
every reply.

**Out of scope.** Making or changing verification decisions, legal or compliance advice, any action
with side effects (planned only behind human approval).

**Models.** Accessed through the LiteLLM gateway: `chat-default`, `chat-fallback`, `embed-default`.
Actual model IDs per environment live in `config/litellm/`.

**Known limitations (to measure and update).**
- PII detection of Malay names with the small spaCy model is weak; regex fallback covers IDs only.
- Answers are only as current as the indexed SOPs.
- Bahasa Melayu quality not yet measured.

**Evaluation.** See `eval/`. Release thresholds (week 3): faithfulness ≥ 0.85, context precision
≥ 0.80, 100% pass on restricted-case and ACL tests, red-team pass rate ≥ 95%.
