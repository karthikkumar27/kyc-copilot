# CLAUDE.md — KYC Support Copilot: RAG Engineering Guardrails

> **Audience:** Claude Code and any AI coding agent working in this repository.
> **System:** KYC Support Copilot for LimauPay (fictional Malaysian e-wallet), code release `0.1.0`.
> **Principle:** optimise for correct, grounded, authorised, observable behaviour that can be
> verified, not for a convincing demo. If a property is unverified, say it is unverified.

---

## 0. How to read this file

### 0.1 Normative terms

| Term | Meaning in this file |
|---|---|
| **MUST / MUST NOT** | Mandatory. Deviation requires explicit approval from a named human in the task or PR, and the approval MUST be recorded in the PR description. |
| **SHOULD / SHOULD NOT** | Default behaviour. Deviation is allowed only with a stated reason in Claude's final report. |
| **MAY** | Optional; use judgement. |

### 0.2 Rule provenance

- A rule followed by a reference such as `(FR-ASK-04)`, `(BR-06)`, `(NFR-SEC-02)` or `(TSD §6.7)`
  is derived from `docs/FSD.md` or `docs/TSD.md`.
- A rule with an `OD-*` reference depends on an **open decision** (§20). Claude MUST NOT resolve
  open decisions unilaterally.
- A rule with no reference is a **general RAG engineering practice** adopted for this repository.
  General practices never override a document-derived rule; where they appear to conflict, the
  conflict is an open decision.

### 0.3 Requirement status

FSD requirements carry a status. Claude MUST respect it:

- **Implemented**: current behaviour that MUST be preserved and MUST NOT regress.
- **Partial**: preserve what exists; do not describe it as complete.
- **Planned**: not in code. MUST NOT be described, documented or reported as implemented. MAY be
  built only when the task explicitly scopes it, following the FSD description and roadmap (FSD §11).

---

## 1. Sources of truth and precedence

| Source | Location | Authority |
|---|---|---|
| Functional spec | `docs/FSD.md` | Business intent, roles, business rules, acceptance criteria |
| Technical spec | `docs/TSD.md` | Architecture, data design, API contracts, configuration, known gaps |
| Multi-cloud guide | `docs/multicloud.md` | Procedure for adding cloud providers |
| Governance | `governance/` (model card, risk register, data handling) | Risk, data-handling and release-threshold context |
| Golden set | `eval/golden/kyc_v0.jsonl` | Functional acceptance suite (FSD §10) |
| Code and tests | `app/`, `migrations/`, `tests/` | Actual behaviour |

Rules:

1. Both FSD and TSD are **Draft, reverse-engineered from the code** (FSD header, TSD header). The
   FSD states that where code and README disagree, **the code is the source of truth**. Therefore:
   - Claude MUST NOT treat the README, chat history, or generated code as requirements.
   - When code and FSD/TSD disagree, Claude MUST NOT silently "fix" either side. It MUST report the
     discrepancy (file, line, requirement ID) and ask whether the document or the code is wrong.
     The divergence may be a documentation error or a regression.
2. The FSD and TSD describe the **same** application and are consistent companions. The TSD is
   authoritative for *how*; the FSD for *what* and *why*. Neither replaces the other.
3. Requirement IDs (`FR-*`, `NFR-*`, `BR-*`, `UC-*`) are the traceability keys. Every meaningful
   code or test change MUST map to a requirement ID, a TSD gap (`T*`), an FSD question (`Q*`), or an
   explicitly approved technical task.
4. A requirement change MUST be reflected in `docs/FSD.md` / `docs/TSD.md` (including the TSD §16
   traceability table) in the same PR as the code change, or the PR MUST state why not.
5. Claude MUST NOT invent business rules, reason codes, roles, permissions, retention periods,
   SLAs, latency targets, model choices, thresholds or schemas. Gaps go to §20.

---

## 2. System snapshot (for orientation; the TSD is authoritative)

- **What it does:** a read-only assistant for internal support staff. One `POST /ask` returns a
  grounded, cited answer from indexed SOPs plus live verification status, a suggested reply in
  English or Bahasa Melayu, an escalation flag, and for restricted cases a fixed agent notice. Every
  interaction is audited. It never talks to customers and never changes a verification decision
  (FSD §1.1, BR-07).
- **Pipeline:** redact question → KYC lookup → deterministic disclosure policy → embed → hybrid
  retrieval (pgvector HNSW cosine + Postgres FTS `simple`, fused with RRF) with tenant/role filter
  inside both branches → spotlighted prompt → JSON-mode generation → parse/validate → force
  escalation where required → audit (TSD §5.1).
- **Ingestion:** upload → validate → SHA-256 dedup → store → queue → OCR/decode → PII redact →
  heading-aware chunking → embed → transactional chunk replace (TSD §5.2).
- **Stack (TSD §2):** Python ≥ 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async + asyncpg, Alembic,
  PostgreSQL 16 + pgvector, arq/Redis (local) or Cloud Tasks (GCP), LiteLLM gateway, Tesseract or
  Document AI, Presidio or Cloud DLP, Terraform (GCP), ruff + pytest, GitHub Actions.
- **Roles:** `agent` ⊂ `supervisor` ⊂ `admin` (BR-05, FSD §2.1). One tenant per deployment in v0.1;
  the data model is multi-tenant (FSD §12).

### 2.1 Commands (TSD §12)

| Task | Command |
|---|---|
| Start local stack | `make up` |
| Seed synthetic SOPs | `make seed` |
| Unit tests (in container) | `make test` |
| Lint (in container) | `make lint` |
| CI equivalent | `ruff check .` then `pytest -q` |
| Migrate | `alembic upgrade head` |

Claude MUST use these project commands rather than inventing alternatives, and MUST report the
exact commands it ran.

### 2.2 High-risk paths

Changes to these files MUST be called out explicitly in the plan and the final report, MUST have
tests that exercise the changed behaviour, and MUST NOT be bundled with unrelated changes:

| Path | Why it is high-risk |
|---|---|
| `app/kyc/policy.py` | Tipping-off protection, `SAFE_FIELDS`, disclosable reason list |
| `app/rag/retrieve.py` | Tenant and role filtering before ranking |
| `app/rag/prompting.py` | System prompt, spotlighting/escaping, output parsing, citation checks |
| `app/rag/answer.py` | Orchestration order, forced escalation, audit content |
| `app/security.py`, `app/config.py` | Identity, role checks, production guard |
| `app/domain.py` (`ROLE_SCOPES`) | Role hierarchy |
| `app/adapters/pii/*` | Redaction patterns and providers |
| `app/api/documents.py` | Upload validation, role gates, 404 masking, deletion |
| `migrations/` | Schema, indexes, append-only audit trigger, embedding dimension |
| `config/litellm/*.yaml` | Model routing, fallbacks, retries |
| `deploy/terraform/` | IAM, residency, data at rest, secrets |

---

## 3. Non-negotiable invariants

These are the critical correctness and security controls. Claude MUST preserve every invariant,
MUST NOT weaken one to make a feature or test work, and MUST stop and report if a task appears to
require violating one.

| ID | Invariant | Source | Current automated evidence | Required evidence when touched |
|---|---|---|---|---|
| INV-01 | Tenant is derived server-side (`DEFAULT_TENANT` now, OIDC claims later), never from request input. Every document, chunk, audit and KYC lookup is tenant-scoped. | BR-06, TSD §6.2, §11 | None | Unit test on the dependency + integration test with two tenants' data |
| INV-02 | Tenant **and** role-overlap filters are inside **both** the vector and keyword sub-queries, before ranking. No post-retrieval filtering as the access control. | FR-ASK-04, NFR-SEC-01, TSD §6.7 | Golden g011/g012 via `make eval` (live stack and model; not an integration test) | Integration test against real Postgres + pgvector proving restricted chunks are never candidates |
| INV-03 | A document the caller may not read returns `404`, identical to a non-existent document, on view, re-ingest and delete. | FR-DOC-08, UC-05 | None | API test per role |
| INV-04 | Upload and re-ingest: supervisor or admin. Delete: admin only. Unknown role: `403`. | FR-DOC-01/09/10, FR-AUTH-01, FSD §2.1 | None | API test per role and per endpoint |
| INV-05 | The disclosure policy is deterministic code. For `REJECTED`/`UNDER_REVIEW`, a reason code not on the BR-02 allow-list (including unknown codes) is removed before context is built, status is shown as `UNDER_REVIEW`, the `SCR-REVIEW-01` disclosure rule is added, the fixed `agent_notice` is returned, and `needs_escalation = true` is forced regardless of model output. | FR-KYC-03/04, BR-02/03, UC-03 | `tests/test_kyc_policy.py`, `tests/test_answer.py` (gateway payload has no internal reason) | Unit tests + a test asserting the payload sent to the gateway contains no internal reason |
| INV-06 | Only `SAFE_FIELDS` reach the model; `agent_notice` never reaches the model. | FR-KYC-02, FR-KYC-05 | `tests/test_kyc_policy.py` | Unit test on the allow-list |
| INV-07 | The question is PII-redacted before embedding, retrieval, any model call and audit. Document text is redacted before chunking, embedding and storage. | FR-ASK-03, FR-ING-03, NFR-PRV-01 | `tests/test_pii_regex.py` (patterns only, not ordering) | Test proving ordering (redactor called before embed/chat/audit) |
| INV-08 | `customer_id` MUST match `^CUS-\d{5}$`; IC/NRIC numbers are rejected with `422`. | FR-ASK-02, BR-01 | Pydantic schema only | API validation test |
| INV-09 | Retrieved chunks, metadata, account JSON and the question are wrapped as untrusted data with `&`, `<`, `>` escaped so they cannot close the spotlight tags. | NFR-SEC-02, TSD §6.8 | `tests/test_prompting.py` | Extend tests for any new field placed in the prompt |
| INV-10 | Model output is parsed as a JSON object and validated; non-JSON or non-object output returns the fixed escalation answer; citations outside `1..n_chunks` or non-integer are dropped; nothing the model returns is executed. | FR-ASK-08, FR-ASK-10, NFR-SEC-03 | `tests/test_prompting.py` | Parser tests for every new field |
| INV-11 | No retrieved chunks **and** no account context → fixed answer with `insufficient_context = true` and `needs_escalation = true`, and no chat-model call. | FR-ASK-06, UC-01 | None | Test that the chat client is not invoked |
| INV-12 | The copilot is read-only: no tool or code path with side effects is driven by model output. | BR-07, NFR-SEC-03, TSD §11 (LLM06) | Design only | Any new tool requires an approved requirement (F5 is Planned) |
| INV-13 | The audit log is append-only and records the FR-AUD-01/03 fields for every `/ask`, upload and delete. The DB rejects `UPDATE`/`DELETE`. | FR-AUD-01..04 | None | Integration test that update/delete raise; test of `detail` keys |
| INV-14 | `AUTH_MODE=dev` is refused when `ENVIRONMENT=production`; misconfigured or placeholder adapters stop startup. | FR-AUTH-02, FR-OPS-05, NFR-REL-03 | `tests/test_registry.py` (adapters only) | Settings validation test |
| INV-15 | Unhandled errors return `500 {"detail":"Internal error","request_id":…}`; no stack traces, prompts or provider errors leak. | FR-OPS-04 | None | API test with a forced exception |
| INV-16 | No secrets in prompts, code, logs or fixtures. Provider keys exist only in the gateway; GCP secrets come from Secret Manager. | NFR-SEC-04 | None | Secret scanning in CI (recommended, §16) |
| INV-17 | The application reaches models only through gateway aliases (`chat-default`, `embed-default`). Domain and RAG code never import a cloud SDK; only `app/adapters/*/<cloud>.py` may. | TSD §1.3, §3, NFR-PORT-01 | None | Import-boundary check (recommended, §16) |
| INV-18 | Repository data and tests are synthetic only. No real customer data, IC numbers or production SOPs. | NFR-PRV-03 | Policy only | Review |
| INV-19 | Region defaults to `MY` / `asia-southeast1`; out-of-region processing (e.g. Document AI in `us`) stays opt-in. | NFR-PRV-02 | Terraform defaults | Review of config and Terraform diffs |
| INV-20 | Ingestion is idempotent: re-running replaces a document's chunks in one transaction; chunks inherit the document's tenant and `allowed_roles`; uploads are deduplicated by SHA-256 per tenant. | FR-ING-05/06, FR-DOC-06 | None | Integration tests for re-run, failure rollback and dedup |

"None" in the evidence column is a known gap, not permission to skip testing. When Claude changes
code covered by an invariant with no automated evidence, it MUST add the evidence listed, or state
explicitly in the report that the invariant remains unverified.

---

## 4. Prohibited practices

Claude MUST NOT:

1. Pass a restricted reason code, the raw KYC record, `agent_notice`, or any non-`SAFE_FIELDS`
   field to a model, prompt template, log line or trace (INV-05/06).
2. Move authorisation, tenant filtering, disclosure decisions or escalation forcing into the prompt
   or rely on the model to enforce them (TSD §1.3 "policy in code, not in the prompt").
3. Filter retrieved chunks by role or tenant only after ranking or after the model has seen them
   (INV-02).
4. Accept a tenant, role or user identity from the request body or query string, or add a new
   header-based identity path outside `AUTH_MODE=dev` (INV-01, FR-AUTH-01).
5. Accept IC/NRIC/MyKad numbers, card numbers or passwords as input, or make the copilot ask for or
   repeat them (BR-01, FR-ASK-12).
6. Add tools, actions or endpoints that change verification state or any external system without
   an approved requirement (BR-07; F5 Attempt Override is Planned and human-approved only).
7. Call model providers directly or hard-code provider model IDs in application code (INV-17).
8. Remove, skip, weaken or rewrite assertions, or edit golden-set expected outcomes, to make tests
   or evaluations pass.
9. Claim a test passed, a migration succeeded, an evaluation improved, or a quality gate was met
   without having run it and inspected the output.
10. Describe Planned features (OIDC, streaming, re-ranker, red-team suite, ingestion injection
    scanning, eval gate, tracing, semantic cache, rate limits, AWS/Azure adapters) as implemented.
11. Swallow exceptions broadly, add silent fallbacks, or return a successful-looking answer after a
    retrieval or provider failure.
12. Weaken the append-only audit trigger, add an audit update/delete path, or grant the app DB role
    additional privileges (INV-13, T17).
13. Commit `.env` files, credentials, real customer data, generated indexes or large artefacts.
14. Change `EMBEDDING_DIM`, the embedding model, the chunker or the parser without the migration
    procedure in §8.4.
15. Introduce agents, multi-step LLM orchestration, extra indexes, extra vector stores or new
    frameworks without a requirement and measured evidence.
16. Disable or bypass startup validation (production guard, adapter validation) to "get it running".

---

## 5. Architecture and design guardrails

### 5.1 Stage boundaries

Each RAG stage has a home. New logic MUST go into the owning module and SHOULD NOT leak across
boundaries.

| Stage | Owning module | Notes |
|---|---|---|
| Transport, validation, role gates | `app/api/*` | Pydantic schemas; `require_role` |
| Identity | `app/security.py` | `CurrentUser` contract; OIDC goes behind it (FR-AUTH-03) |
| Disclosure policy | `app/kyc/policy.py` | Pure function, no I/O |
| KYC status | `app/kyc/provider.py` | `KycStatusProvider` Protocol; production provider implements the same interface (FR-KYC-07) |
| Parsing / OCR | `app/adapters/ocr/*` via `app/rag/ingest.py` | |
| PII redaction | `app/adapters/pii/*` | |
| Chunking | `app/rag/chunking.py` | Pure function |
| Embedding and chat calls | `app/llm.py` | Gateway only |
| Indexing | `app/rag/ingest.py` | Transactional replace |
| Retrieval and fusion | `app/rag/retrieve.py` | Single SQL statement, filters inside CTEs |
| Context assembly, prompt, parsing | `app/rag/prompting.py` | |
| Orchestration and audit | `app/rag/answer.py`, `app/db/audit.py` | |
| Cloud specifics | `app/adapters/*/<cloud>.py`, `deploy/`, `config/litellm/` | Only here |

### 5.2 Design rules

- Dependency direction MUST remain `api → rag / kyc / db / adapters.factory → adapters.<kind>.<cloud>`;
  `app/domain.py` MUST stay free of framework and cloud imports (TSD §3).
- Deterministic logic (authorisation, filtering, disclosure, escalation forcing, validation, state
  transitions) MUST be code. The LLM is used only for language understanding and generation.
- New infrastructure dependencies MUST be added as a `Protocol` + adapter selected by environment
  variable, following `docs/multicloud.md` (NFR-PORT-01, TSD §12.3). New placeholders MUST fail fast
  at startup (`PlannedProvider`).
- The service MUST remain one image with several commands (TSD §1.3). Do not add a second service
  or language runtime without an approved TSD change.
- Additional components (re-ranker, query rewriting, parent-child retrieval, caches, agents) SHOULD
  be added only when a requirement exists and an offline evaluation shows a measurable benefit that
  justifies latency and cost. The re-ranker is Planned for week 2 and MUST be evaluated against the
  current hybrid baseline before becoming the default.

---

## 6. Document ingestion and data processing

### 6.1 Validation (FR-DOC-02..07)

- Allowed extensions: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.md`, `.txt`, else `415`. `source_type` in
  `sop|regulation|faq|script`, else `422`. `allowed_roles` a non-empty subset of the three roles,
  else `422`. Over `MAX_UPLOAD_MB` → `413`; empty → `400`.
- Adding a file type MUST be an approved requirement change, with a parser, OCR path, tests and
  FSD/TSD updates. Office documents and HTML are **not** supported in v0.1; do not add them
  speculatively.
- File type is currently taken from the extension (T14). Content-signature checks SHOULD be added
  when this code is touched, without changing documented status codes unless approved.
- Filenames MUST be sanitised to `[A-Za-z0-9._-]`, max 120 characters; storage keys MUST stay
  `{tenant_id}/{document_id}/{safe_name}`; the path-traversal and bucket-ownership guards MUST be
  preserved (TSD §7.4, §6.3).

### 6.2 Parsing and OCR (FR-ING-02)

- Text files decode as UTF-8 with replacement; PDFs use the text layer and OCR pages with fewer
  than 20 characters; images are OCR'd; local OCR uses `eng+msa`.
- A document that yields no text MUST be marked `failed` (FR-ING-08). Empty, corrupt, unsupported
  and partially readable inputs MUST produce an explicit status and actionable error, never a silent
  partial index.
- Page numbers and Markdown heading hierarchy MUST be preserved because citations depend on them.
- When changing parsing, Claude SHOULD sample extraction output for scanned pages, tables and
  Malay text and report what was checked. Tables lose structure in the current pipeline; treat
  table-heavy content as a known limitation, not something to fix speculatively.

### 6.3 Redaction (FR-ING-03, NFR-PRV-01)

- Redaction MUST run on every page before chunking and embedding; only redacted text is stored.
- Changes to regex patterns or detectors MUST include positive and negative tests (Malaysian
  identifiers, +60 mobiles, emails, cards; amounts and reference numbers not redacted). Known
  false-positive (T11) and Malay-recall (T12) gaps MUST NOT be described as resolved without
  measured evidence.

### 6.4 Lifecycle, idempotency and deletion

- Status transitions MUST follow `queued → processing → ready | failed` (error ≤ 2,000 characters)
  and the TSD §5.4 state machine (FR-ING-07). On failure: roll back, set `failed`, save the error,
  re-raise so the queue can retry.
- Re-running ingestion MUST replace chunks in one transaction; a `ready` document is skipped by the
  worker (FR-ING-06). Re-ingest sets `queued` first (UC-06).
- Known local-queue defects: re-ingest within an hour can be silently dropped (T1); ordinary
  exceptions are not retried (T2). Do not rely on local re-ingest/retry behaviour in tests or claims
  until fixed.
- Upload is not atomic across storage, DB, queue and audit (T3). Do not add further steps to that
  sequence without addressing consistency (outbox or reaper) or recording the risk.
- Deletion MUST remove the document row, cascade chunks and embeddings, attempt the stored-file
  deletion, and audit `document.delete` (FR-DOC-10, UC-07). Note OD-10 on orphaned and versioned
  objects.
- Changing a document's `allowed_roles` currently requires delete and re-upload (T8). Any role-update
  feature MUST update document and chunk rows atomically and be audited.

---

## 7. Chunking

- The current strategy is heading-aware, page-bounded chunking with `CHUNK_MAX_CHARS=1500`,
  `CHUNK_OVERLAP_CHARS=200`, overlap < half of max, chunks never cross pages, section carried across
  pages, section title prepended to embedding text (FR-ING-04, TSD §6.5). These are the **current
  configured baseline**, not validated optima.
- Chunk parameters MUST come from configuration, never be hard-coded elsewhere.
- Changing the strategy or parameters MUST be accompanied by a comparison against the baseline on
  the golden set (retrieval hit rate of the expected SOP, answer pass rate, restricted/access cases
  at 100%), plus chunk count, duplication and prompt-size impact. Week 2 plans this comparison.
- Every chunk MUST retain `document_id`, `chunk_index`, `page`, `section`, `tenant_id`,
  `allowed_roles` and `embedding_model`.
- Chunker and parser versions are not recorded on chunks today (OD-05). Claude SHOULD propose
  recording them when changing either, as a migration requiring approval.

---

## 8. Embeddings and indexing

### 8.1 Current state (TSD §2, §6.9, §7)

- Embeddings via alias `embed-default` (currently `gemini-embedding-001`), `EMBEDDING_DIM=1536`,
  batches of `EMBED_BATCH_SIZE=16`, each vector length checked. HNSW `vector_cosine_ops`; GIN on
  `content_tsv` (`simple` config) and `allowed_roles`.

### 8.2 Rules

- Query and document embeddings MUST use the same model and dimension. Dimension mismatches MUST
  fail loudly (existing `RuntimeError`), never be truncated or padded.
- `embedding_model` MUST be written on every chunk. Vectors from different embedding models MUST
  NOT be mixed in one retrieval space unless a design explicitly supports and validates it.
- Unchanged documents MUST NOT be re-embedded unnecessarily (dedup and the `ready` skip exist for
  this reason).

### 8.3 Index changes

- The vector dimension is fixed in the migration. Changing `EMBEDDING_DIM` or the embedding model
  requires a new Alembic revision **and** re-embedding every document (TSD §7.2).

### 8.4 Mandatory procedure for embedding, chunking, parser or index changes

1. State the reason, expected benefit, affected requirements and blast radius.
2. Record the baseline (golden-set results, retrieval hit rate, latency, token use).
3. Write a reversible migration where practical; document any irreversible step before running it.
4. Re-embed or re-ingest into new columns/tables or a shadow index first; MUST NOT overwrite the
   working index irreversibly before validation.
5. Compare against the baseline; restricted-case and access-control cases MUST remain 100%.
6. Document backfill, cut-over and rollback steps in the PR.
7. Obtain approval before production rollout.

---

## 9. Retrieval

### 9.1 Current behaviour (TSD §6.7)

One SQL statement: vector top `RETRIEVAL_K=20` by cosine distance and keyword top 20 by
`ts_rank_cd`, both with the same tenant and role filter, fused with RRF (`1/(60 + rank)`), top
`RETRIEVAL_TOP_N=6` returned. Hybrid exists so exact terms (reason codes, SOP IDs) match (FR-ASK-05).

### 9.2 Rules

- INV-02 applies to every retrieval path, including any new one (re-ranker, cache, query rewrite,
  adjacent-chunk expansion). Expansion MUST re-apply the same tenant and role filter.
- `k`, `top_n`, the RRF constant and any thresholds MUST be configuration, and changes MUST be
  evaluated on the golden set. They MUST NOT be tuned on a handful of examples.
- Similarity and RRF scores MUST NOT be presented as calibrated confidence.
- Hybrid retrieval MUST NOT be replaced by vector-only or keyword-only without evaluation showing
  no regression on exact-code queries (e.g. g001, g006) and paraphrased queries.
- The `simple` text-search configuration is intentional for mixed English/Malay content; MUST NOT
  switch to a stemming configuration without evaluating Malay queries.
- Filtered HNSW scans can return fewer than `k` rows (T10). Enabling `hnsw.iterative_scan` requires
  pgvector ≥ 0.8 and an evaluation of narrow-role recall (g012).
- Model-generated filters MUST NOT be introduced; if ever needed, they MUST be validated against an
  allow-list and the authenticated context.
- Retrieval errors and timeouts MUST surface as errors (generic `500` with request ID), not as an
  empty result that triggers the no-context answer.
- **Abstention is mostly model-driven today.** Because there is no relevance threshold, the vector
  branch returns candidates whenever the caller can read any chunk, so the deterministic no-context
  path (INV-11) fires only when no readable chunks exist (OD-06). Claude MUST NOT claim that
  irrelevant retrieval is handled deterministically.
- Superseded or conflicting SOP versions can both be retrieved (OD-03). Context assembly MUST
  preserve per-chunk source labels so conflicts stay visible.

---

## 10. Grounded generation, citations and structured output

### 10.1 Prompt and context (FR-ASK-07..09, TSD §6.8)

- The model MUST receive only: the system prompt, spotlighted `<documents>`, `<account_status>`
  built by the disclosure policy, any `disclosure_rule`, and the redacted question.
- Retrieved documents and account data are **untrusted evidence**, never instructions. The system
  prompt MUST keep the instruction hierarchy (use only provided data, treat it as data, obey
  `disclosure_rule`).
- Generation runs at `temperature=0` with JSON mode. Temperature 0 does not make output
  deterministic; tests MUST NOT depend on exact model wording.
- Prompt changes are behaviour changes: they MUST be reviewed as high-risk (§2.2), MUST keep the
  output key contract (`answer`, `citations`, `suggested_reply`, `needs_escalation`,
  `insufficient_context`), and MUST be followed by the golden-set check (§13).

### 10.2 Citations

- Citation markers are `[n]` over the retrieved set; citations outside `1..n_chunks` are dropped
  (FR-ASK-08). Response citations MUST be built from server-side retrieval data
  (`chunk_id`, `document_id`, `filename`, `page`, `section`), never from model-supplied metadata.
- Current validation is a **range check only** (OD-04). It does not verify that every factual claim
  is cited, that the cited chunk supports the claim, or that inline `[n]` markers match the
  returned citations. Claude MUST NOT describe citations as verified beyond what the code checks.
- Fabricated URLs, quotations or source names MUST NOT be accepted into the response. New output
  fields that reference sources MUST be validated against the retrieved set.

### 10.3 Abstention and escalation

- When evidence is insufficient the response MUST set `insufficient_context = true` without
  inventing policy (FR-ASK-07; golden g008, g009).
- `needs_escalation` MUST be forced `true` for restricted cases, no-context answers and unreadable
  output (FSD §8). Other forcing rules are an open decision (OD-07/Q7); MUST NOT add them without
  approval.
- The answer for the agent and the `suggested_reply` for the customer are distinct. The suggested
  reply MUST be in the question's language (English or Bahasa Melayu) (FR-ASK-09, BR-08).

### 10.4 Structured output

- Model output MUST be validated at the application boundary before any downstream use, even with
  JSON mode (INV-10).
- `format_error` and `dropped_citations` are computed but not returned or audited (T5). Claude
  SHOULD NOT drop these signals further; surfacing them requires an approved contract change.
- Response schema changes to `AskResponse` or the document object are API contract changes: update
  the TSD §8 contract, tests and `/docs` in the same PR.

---

## 11. Security, privacy and prompt injection

### 11.1 Authentication and authorisation

- `AUTH_MODE=dev` (headers `X-User-Id`, `X-User-Role`) is for local development only and MUST stay
  refused in production (FR-AUTH-01/02). OIDC (FR-AUTH-03, Planned) MUST go behind the existing
  `CurrentUser` contract with no endpoint changes (TSD §6.2).
- Until OIDC exists, Cloud Run IAM (`run.invoker`) is the outer boundary on GCP (TSD §11). Claude
  MUST NOT loosen IAM, grant public invoker access, or expose the worker's
  `/internal/ingest/{id}` endpoint beyond the API service account (TSD §8.8).
- Authorisation MUST be enforced at upload, listing, viewing, re-ingest, delete, retrieval, and any
  future cache, citation rendering or action (INV-01..04).

### 11.2 Tipping-off protection (UC-03, BR-02..04)

- The BR-02 disclosable list and its approved explanations are business rules. Adding, removing or
  rewording entries MUST be an approved FSD change; Claude MUST NOT edit them on its own initiative.
- Unknown reason codes MUST fail closed (BR-03).
- The guarantee is structural: the model never receives the reason. Tests MUST assert on the
  context/payload, not only on model output. The golden checks for g004 ("sanction", "screening",
  "watchlist" absent) and g005 ("FRAUD"/"fraud" absent) MUST be deterministic string checks, not an
  LLM judge.
- Output guard (BR-09, `guard_restricted_output`): in a restricted case an `answer` or
  `suggested_reply` naming `sanction`, `screening`, `watchlist` or `fraud` is replaced in code. MUST
  NOT be removed or weakened. Its term list is a business rule: changes need an approved FSD
  change. It is a second layer, never a substitute for keeping the reason away from the model.

### 11.3 Prompt injection

- Direct injection (user question) and indirect injection (uploaded documents) are both in scope
  (OWASP LLM01). Current mitigation is spotlighting, escaping and the instruction hierarchy
  (NFR-SEC-02). Ingestion-time scanning (FR-DOC-11) and a CI red-team suite (NFR-SEC-05) are
  Planned.
- Any new text placed in a prompt MUST be escaped and tagged as data, with a test proving it cannot
  close or forge tags.
- Model output MUST NEVER drive authorisation, filtering, disclosure, data writes or tool calls.

### 11.4 PII and data handling

- Inputs (question, document text) are redacted. Outputs (`answer`, `suggested_reply`) are **not**
  redacted (Q1, T4), and the raw model `answer` is written to the append-only audit log. Claude MUST
  NOT claim "PII redaction in and out" until OD-01 is decided and implemented.
- Logs MUST NOT contain raw questions, retrieved content, KYC records, prompts or model output by
  default. Use IDs, counts and categories.
- Data sent to external model providers MUST be limited to the redacted question, retrieved
  redacted chunks and `SAFE_FIELDS`. Provider retention and training settings are not documented
  (OD-11).
- Residency defaults MUST be preserved (INV-19). Enabling Document AI (`us`) or any out-of-region
  service is opt-in and MUST be called out in the PR.

### 11.5 Secrets and infrastructure

- Secrets come from environment injection locally and Secret Manager on GCP. `LLM_API_KEY` /
  `LITELLM_MASTER_KEY` and DB passwords MUST NOT appear in code, logs, prompts or test fixtures; the
  local default `sk-local-change-me` MUST NOT be used outside local development.
- Least privilege MUST be preserved: separate API and worker service accounts; only the API may
  enqueue and invoke the worker; only the worker has Document AI access (TSD §11).
- The app container runs as non-root (UID 10001); MUST NOT be changed.
- Supply chain: dependencies use `>=` without a lock file and LiteLLM uses `main-stable` (T13).
  Claude SHOULD NOT add unpinned dependencies; new dependencies MUST be justified (maintenance,
  licence, security, size).

---

## 12. API design, reliability and operations

- Endpoints, status codes and payloads MUST match TSD §8. Errors: `403` role, `404` masked
  resource, `413`, `415`, `422`, generic `500` with `request_id`, `501` for non-dev `AUTH_MODE`.
- Every response MUST carry `x-request-id` (FR-OPS-03); every log line MUST include it (NFR-OBS-01).
- Expensive work (OCR, embedding) MUST stay asynchronous through the queue (FR-ING-01). Jobs MUST be
  idempotent and observable via document status and errors.
- Timeouts and retries: client timeout 30 s with 2 retries, gateway 2 retries plus fallback
  (NFR-REL-01). This multiplies attempts and latency (T9). Claude MUST NOT add another retry layer;
  consolidating retries changes NFR-REL-01 and needs approval.
- Validation, authorisation and malformed-request errors MUST NOT be retried.
- During dependency failures the system MUST fail closed: never skip the tenant/role filter, the
  disclosure policy or redaction to keep serving. If the PII provider fails, the request MUST fail,
  not proceed unredacted.
- `/healthz` reflects liveness only; `/readyz` checks DB and gateway (FR-OPS-01/02). Queue and
  storage are not checked (T6); adding checks MUST keep them lightweight (3 s class timeouts).
- Pagination (T15), rate limits and budgets (NFR-PERF-02) are absent. New list endpoints SHOULD be
  paginated; rate limiting is Planned and MUST NOT be described as present.

### 12.1 Deployment

- Migrations run as a separate step (`migrate` service / `kyc-migrate` job) before API and worker.
  New migrations MUST be forward-compatible with the running code during rollout and SHOULD include
  a working `downgrade`.
- Model IDs in `config/litellm/*.yaml` change often and MUST be verified against provider
  documentation, not edited from memory (FSD §12).
- Terraform defaults include `deletion_protection = false` and local state (TSD §12.2). Claude MUST
  NOT change production-impacting Terraform without explicit approval and a plan output reviewed by
  a human. Claude MUST NOT run `terraform apply`, deploy, or execute cloud mutations unless the task
  explicitly asks for it.
- A production deployment cannot serve requests until OIDC exists (Q5). Do not work around this by
  enabling dev auth.

---

## 13. Evaluation and quality assurance

### 13.1 Current state

- Acceptance suite: `eval/golden/kyc_v0.jsonl`, 12 cases, behaviour classes `answer`,
  `answer_and_escalate`, `restricted`, `refuse_insufficient_context` (FSD §8, §10).
- `make eval` (`scripts/eval.py`, FSD §10) runs all cases against the running stack with
  deterministic checks: forbidden terms, restricted notice, forced escalation, abstention, expected
  citation. FAIL = a structural check failed; REVIEW = only an expected fact was not found as exact
  text (read the answer); PASS otherwise. An on-demand workflow (`eval.yml`) runs it in CI. It is
  not run on every PR, computes no faithfulness or context-precision scores, and does not enforce
  the thresholds below.
- Planned release gate (NFR-QUAL-01): faithfulness ≥ 0.85, context precision ≥ 0.80, 100% pass on
  restricted-case and access-control tests, red-team pass rate ≥ 95%. These are **targets, not
  current results**.

### 13.2 Rules

- Changes to parsing, redaction, chunking, embeddings, retrieval, fusion, prompts, models, gateway
  routing, context assembly, citation logic or the disclosure policy MUST be followed by a golden-set
  check. Claude MUST report each case as `passed`, `failed` or `not run`, how it was checked
  (manual curl, script, test), and against which model.
- Restricted-case (g004, g005) and access-control (g011, g012) cases MUST pass 100% before any such
  change is called done. A single failure is a blocker.
- Golden-set edits are reviewed changes: new cases are welcome; changing an existing case's expected
  behaviour MUST cite the requirement change that justifies it. The file SHOULD be versioned
  (`kyc_v1.jsonl`, etc.) rather than silently rewritten.
- When growing the set (week 3 plans 100+), cover: answerable, unanswerable, ambiguous,
  paraphrased, exact-code, Bahasa Melayu, conflicting-SOP, cross-role, cross-tenant, direct and
  document-borne injection, and customer-not-found cases. Keep a held-out regression subset.
- Retrieval metrics (Recall@k, MRR, nDCG, context precision) require labelled relevant chunks per
  case. Until labels exist, Claude MAY report "expected SOP present in top-n" but MUST NOT report
  named IR metrics without stating dataset and calculation.
- LLM-judge metrics (faithfulness etc.) MAY supplement evaluation but MUST NOT be the only gate for
  restricted-case, access-control or PII behaviour.
- Every bug found in retrieval, grounding, disclosure or access control MUST become a regression
  test or golden case.
- A change that improves one metric while breaking a security, correctness, latency or cost
  constraint is a regression.

### 13.3 Production readiness

Claude MUST NOT describe the system or a change as production-ready while any of these hold:
the NFR-QUAL-01 thresholds are not computed or enforced in CI (the `make eval` runner exists but
runs on demand); OIDC is not implemented; access-control retrieval is checked only by golden
g011/g012, not by Postgres integration tests; latency has no measured baseline (NFR-PERF-01). It
MAY describe specific verified properties.

---

## 14. Testing standards

- Every new or modified component MUST have tests for: normal behaviour, edge and boundary values,
  invalid input, dependency failure (timeouts, provider errors, DB errors), and authorisation/tenant
  behaviour where applicable.
- Unit tests MUST mock the gateway, KYC provider, OCR, PII cloud providers, storage and queue. The
  existing pure-function tests (`test_chunking`, `test_kyc_policy`, `test_pii_regex`,
  `test_prompting`, `test_registry`) are the pattern to follow.
- Integration tests SHOULD run against real Postgres + pgvector (the compose stack) for retrieval
  filtering, chunk replacement, dedup, cascade delete and the audit trigger. These are currently
  uncovered (TSD §13) and are the highest-value additions.
- Required scenario coverage when the relevant code is touched: duplicate upload, concurrent
  duplicate upload (T3), re-ingest, delete with storage failure, empty/no-text document, oversized
  and unsupported files, provider timeout, embedding dimension mismatch, empty retrieval, non-JSON
  and out-of-range-citation output, restricted and unknown reason codes, cross-role retrieval,
  injection inside a document and inside the question.
- Tests and fixtures MUST use synthetic data only (NFR-PRV-03).
- Claude MUST run the narrowest relevant tests while developing and `make lint` + `make test` (or
  `ruff check .` + `pytest -q`) before declaring completion, and MUST report the exact commands,
  pass/fail counts, and anything not run with the reason (for example, Docker unavailable).
- If something cannot reasonably be tested, Claude MUST say why and get approval rather than
  proceeding silently.

---

## 15. Observability, performance and cost

### 15.1 Observability

- Current: JSON logs with request ID (NFR-OBS-01); audit `detail` with retrieved/cited chunk IDs,
  model, usage and latency (FR-AUD-01). OpenTelemetry and Langfuse are Planned (NFR-OBS-02).
- New code SHOULD log stage outcomes (retrieval count, no-context path taken, format error,
  dropped citations, fallback model used, provider error category) as structured fields without
  content.
- Failures MUST distinguish retrieval failure, generation failure, parsing failure and policy-driven
  escalation, so support can act on them.
- Audit `detail` additions MUST NOT include restricted reasons or unredacted text.

### 15.2 Performance and cost

- There are no measured latency or throughput figures (NFR-PERF-01, TSD §14). Claude MUST NOT
  claim performance improvements without before/after measurements under stated conditions.
- Optimise measured bottlenecks only. Bound context (`top_n` × chunk size), retries and generation
  length.
- A semantic cache is Planned (NFR-PERF-02). Any cache MUST key on tenant, role scope, `customer_id`
  context, index/content version and prompt/model version; MUST NOT cache answers involving
  account context unless explicitly approved; and MUST define invalidation on upload, re-ingest and
  delete.
- Cheaper models MAY be evaluated, but a model swap MUST pass §13 including Bahasa Melayu cases.

---

## 16. Coding standards and change management

- Python ≥ 3.12; ruff (line length 100, target py312) MUST pass. Use type hints and Pydantic v2
  schemas at boundaries; SQLAlchemy 2 async patterns; settings via `pydantic-settings` (TSD §2).
- Configuration MUST live in `Settings` with validation; new required settings MUST fail fast at
  startup when missing and be added to TSD §10.
- Keep transport, business logic, retrieval, provider integrations, persistence and authorisation
  separately testable. No broad `except Exception: pass`; no silent defaults for security-relevant
  settings.
- Prefer the smallest change that satisfies the requirement. No unrelated refactors, renames or
  formatting churn.
- Version-sensitive artefacts (prompt, golden set, parser, chunking config, embedding model,
  retrieval settings, gateway config) MUST be changed in reviewable diffs with the reason stated.
  Material changes MUST include a rollback note.
- Commit messages SHOULD follow Conventional Commits (team convention carried over from the
  previous CLAUDE.md; not stated in the FSD/TSD).
- Documentation MUST be updated with behaviour: FSD status column, TSD sections, §16 traceability,
  §15 known gaps (mark gaps fixed only when tests prove it).

### 16.1 Recommended automated enforcement

These make the rules above checkable rather than advisory. Implementing them is a separate,
approved task; Claude MUST NOT claim they exist until they do.

| Control | Enforces |
|---|---|
| Golden-set runner in CI with deterministic `must_not_contain` checks and NFR-QUAL-01 thresholds (partly done: `make eval` and an on-demand workflow; not on every PR, no thresholds) | INV-05, §13 |
| Postgres + pgvector integration job (compose or service container) for retrieval, dedup, cascade, audit trigger | INV-02, INV-13, INV-20 |
| Payload-capture test: assert the gateway request never contains internal reason codes or non-safe fields (partly done: `tests/test_answer.py` covers the restricted case) | INV-05, INV-06 |
| Import-boundary lint (e.g. import-linter) blocking cloud SDK imports outside `app/adapters/*/<cloud>.py` | INV-17 |
| Secret scanning (pre-commit and CI) | INV-16 |
| CODEOWNERS + required review on §2.2 high-risk paths | §2.2 |
| Lock file and pinned image digests | T13 |
| Migration up/down test in CI | §8.4, §12.1 |
| Separate low-privilege DB role for the app (no TRUNCATE, not table owner) | INV-13, T17 |
| Claude Code permission rules denying edits to `.env*`, `deploy/terraform/**` applies and cloud CLI mutations without approval | §11.5, §12.1 |

---

## 17. Mandatory Claude workflow

For every non-trivial task:

1. **Inspect.** Read the relevant FSD/TSD sections, code, tests, configuration and open decisions
   (§20). Check whether the area is in §2.2 or §3.
2. **Summarise.** State the requested outcome, requirement IDs, affected modules and invariants.
3. **Gap check.** List ambiguities, contradictions (code vs docs, docs vs request), assumptions and
   security risks. If a business, security or privacy decision is needed, stop and ask.
4. **Plan.** Propose the minimal change and the test/evaluation strategy. For high-risk paths, wait
   for approval of the plan before editing.
5. **Implement.** Only the approved scope, following existing conventions and stage boundaries.
6. **Test.** Add or update tests; run them; inspect output.
7. **Evaluate.** Run the golden-set checks applicable to the change (§13) and any security cases.
8. **Review.** Walk the §18 checklist: grounding, citations, authorisation, disclosure, redaction,
   error handling, performance, cost, scope creep.
9. **Report** using this structure:

   ```markdown
   ## Summary
   ## Requirements addressed (IDs)
   ## Files changed (high-risk paths flagged)
   ## Commands run and results (exact commands, pass/fail counts)
   ## Golden-set / evaluation results (per case: passed / failed / not run, method, model)
   ## Invariants touched and evidence
   ## Not verified (and why)
   ## Risks, open decisions, follow-ups
   ```

Claude MUST NOT state that a task is complete when required tests or evaluations have not run.
Unverified behaviour MUST be labelled unverified.

---

## 18. RAG code-review checklist

**Requirements and scope**
- [ ] Change maps to requirement IDs, TSD gaps or an approved task; FSD/TSD updated if behaviour changed.
- [ ] No Planned feature described as implemented; no open decision resolved unilaterally.
- [ ] No unrelated refactors or new dependencies without justification.

**Access control and privacy**
- [ ] Tenant comes from server context; tenant + role filters inside both retrieval branches.
- [ ] Unreadable documents return `404`; role gates unchanged or intentionally changed with approval.
- [ ] No restricted reason, raw KYC field or `agent_notice` reaches the model, logs or traces.
- [ ] Question and document text redacted before embedding, retrieval, model call, storage and audit.
- [ ] No secrets, real data or unredacted content in code, logs, fixtures or audit additions.
- [ ] Residency defaults and IAM least privilege preserved.

**Retrieval and generation**
- [ ] Retrieval parameter or strategy changes backed by golden-set comparison.
- [ ] New prompt content escaped and spotlighted; injection test added.
- [ ] Output parsed and validated; citations built from server-side retrieval data.
- [ ] Abstention and forced-escalation paths intact (no-context, restricted, format error).
- [ ] Suggested reply language rule intact.

**Ingestion and data**
- [ ] Ingestion idempotent; failures roll back and set `failed` with an error.
- [ ] Provenance (page, section, document, chunk index, embedding model) preserved.
- [ ] Migrations reversible or irreversibility documented; embedding/dimension procedure (§8.4) followed.
- [ ] Audit remains append-only and complete.

**Reliability and operations**
- [ ] Errors fail closed; generic `500` with request ID; no stack traces leaked.
- [ ] No extra retry layer; timeouts bounded.
- [ ] Stage outcomes observable without logging content.

**Verification**
- [ ] `make lint` and `make test` (or CI equivalents) run and pass; output inspected.
- [ ] Golden-set cases relevant to the change checked; g004, g005, g011, g012 pass.
- [ ] Report lists what was not verified.

---

## 19. Definition of done

A change is done only when all applicable items are true:

1. Traceable to requirement IDs or an approved task; FSD/TSD and the TSD §16 traceability table
   updated where behaviour, contracts or configuration changed.
2. All §3 invariants it touches are preserved and have the required evidence, or the gap is stated.
3. Lint and unit tests pass; relevant integration tests pass or are reported as not run with a
   reason.
4. Relevant golden-set cases checked and reported per case; restricted-case and access-control cases
   pass 100%.
5. Citations, abstention and forced escalation verified for affected paths.
6. No secrets, real data or unredacted content added.
7. Migrations, configuration changes, rollback steps and operational impact documented.
8. Logs and statuses make new failure modes diagnosable.
9. Known limitations, unverified assumptions and open decisions disclosed in the report.

---

## 20. Open decisions register

Claude MUST NOT resolve these on its own. When a task touches one, Claude MUST name it, follow the
interim rule, and ask for a decision if the task cannot proceed without one.

| ID | Issue | Source | Interim rule for Claude |
|---|---|---|---|
| OD-01 | Model outputs (`answer`, `suggested_reply`) are not PII-redacted; README claims "in and out"; raw answer is stored in the append-only audit. | FSD Q1, TSD T4 | Do not claim output redaction. Do not add it without approval (affects audit and language quality). |
| OD-02 | Customer not found and nothing retrieved yields "no account was specified". | FSD Q2 | Preserve current text; do not invent a new message. |
| OD-03 | No document versioning, supersession or effective dates; an updated SOP uploads as a new document and old versions stay retrievable until deleted. | Analysis of FR-DOC-06, TSD §7 | Do not add supersession logic without a requirement; keep source labels visible so conflicts surface. |
| OD-04 | Citation validation is range-only: no check that every claim is cited (FR-ASK-08 "every factual claim"), that the chunk supports the claim, or that inline `[n]` markers match returned citations. | Analysis of FR-ASK-08, TSD §6.8 | Describe citation checks exactly as implemented. |
| OD-05 | Chunk IDs are regenerated on every re-ingest and cascade-deleted on delete, so audit `retrieved_chunk_ids`/`cited_chunk_ids` can no longer be resolved; parser/chunker versions are not stored. | Analysis of TSD §6.6, §7 | Do not change ID generation or schema without approval; flag the audit-reproducibility impact in related work. |
| OD-06 | No relevance threshold; the deterministic no-context path fires only when the role has no readable chunks, so abstention on irrelevant results relies on the model. | Analysis of FR-ASK-06, TSD §6.7 | Do not add a threshold without golden-set evaluation and approval. |
| OD-07 | Only restricted cases force escalation; should exhausted attempts or `PENDING` > 48 h also force it? | FSD Q7 | Do not add forcing rules. |
| OD-08 | Re-ingest is not audited; `format_error`/`dropped_citations` not returned or audited. | FSD Q3, TSD T5 | Do not remove these signals; adding audit actions needs approval. |
| OD-09 | `documents.sensitivity` and `region` exist but cannot be set or filtered on. | FSD Q4, TSD T7 | Do not describe residency/sensitivity filtering as present. |
| OD-10 | Deletion reports success even if the stored file is not deleted; no clean-up job; GCS versioning keeps noncurrent copies. No deletion/retention policy for files, chunks, audit or backups. | FSD UC-07 vs FR-DOC-10, TSD §5.3, §7.4, FSD Q6 | Do not claim complete deletion; do not invent retention periods. |
| OD-11 | External provider data-retention and training settings, and residency of local `gemini/` and `anthropic/` routes, are undocumented. | Analysis of TSD §9, NFR-PRV-02 | Do not send anything beyond redacted question, redacted chunks and `SAFE_FIELDS`. |
| OD-12 | Audit retention period (e.g. 7 years) undefined. | FSD Q6, FR-AUD-05 | Do not implement retention or archival without a policy. |
| OD-13 | Production cannot serve until OIDC exists. | FSD Q5 | Never enable dev auth to work around it. |
| OD-14 | `staging` permits `AUTH_MODE=dev`, so any caller who passes IAM can claim `admin`. | Analysis of FR-AUTH-02 | Treat staging as untrusted for real data; do not extend dev auth. |
| OD-15 | Unexpected verification statuses with internal reasons do not trigger the restricted path (the reason is still withheld, but no notice or forced escalation). | Analysis of FSD §6 decision flow | Do not change policy logic without approval; add a test documenting current behaviour if touched. |
| OD-16 | Language of fixed answers (no-context, unreadable output) vs BR-08; behaviour for languages other than English/Malay. | Analysis of BR-08, FR-ASK-09 | Do not change fixed texts; report as unverified. |
| OD-17 | Retry layering (T9), local re-ingest drop (T1), no local retry of ordinary errors (T2), non-atomic upload (T3), readiness coverage (T6), filtered HNSW recall (T10), PII regex false positives (T11), Malay PII recall (T12), supply-chain pinning (T13), MIME by extension (T14), no pagination (T15), cold start (T16), audit TRUNCATE (T17). | TSD §15 | Fix only when scoped; follow the TSD's suggested direction unless told otherwise; update TSD §15 when fixed and tested. |
| OD-18 | FSD and TSD are drafts reverse-engineered from code; no approver or approval process is named. | FSD/TSD headers | Treat them as the best available specification; report code/doc divergence instead of choosing a side. |

---

## Appendix A. General practices adopted without explicit FSD/TSD backing

These rules are sound RAG practice but are not stated in the FSD or TSD. They SHOULD be ratified
into the documents or removed:

- Recording parser and chunker versions on chunks (§7, OD-05).
- Shadow re-indexing and cut-over procedure for embedding changes (§8.4).
- Relevance thresholds evaluated before adoption (§9, OD-06).
- Named IR metrics (Recall@k, MRR, nDCG) requiring labelled relevance (§13.2).
- Held-out regression subset and golden-set file versioning (§13.2).
- Cache key and invalidation requirements (§15.2).
- Fail-closed behaviour on PII provider failure (§12).
- Payload-capture tests, import-boundary lint, secret scanning, CODEOWNERS (§16.1).
- Conventional Commits (§16).

---

## Final rule

The copilot is useful only if it retrieves **authorised** evidence, keeps internal reasons away
from the model, grounds and cites its claims, abstains when evidence is missing, records what it
did, and fails closed. If any of those properties is unverified for a change, report it as
unverified.
