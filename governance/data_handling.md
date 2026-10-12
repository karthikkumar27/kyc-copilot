# Data handling

**Synthetic only.** No real customer data is ever used. Customers are fictional `CUS-` references.

**Flow.** Upload → object storage (private) → OCR → PII redaction → chunks + embeddings in Postgres.
Questions are redacted before retrieval and before reaching any model. Only redacted text is stored
in chunks and the audit log.

**Identifiers.** Agents reference customers by `CUS-` number. The API rejects any other format.

**Tipping-off rule.** Internal review reasons (for example sanctions screening or suspected fraud)
are removed in code before the model sees account data. Unknown reason codes are treated as
internal (fail closed). The agent gets a fixed notice and script SCR-REVIEW-01.

**Residency.** Documents carry a region tag (default MY). On GCP everything runs in the configured
region; Document AI is opt-in because its processors run outside the region.

**Deletion.** Deleting a document removes its chunks and embeddings (cascade) and the stored file.
**Audit.** `audit_log` is append-only (database trigger). Retention policy: to be defined (e.g. 7
years, then archived), implemented as a privileged job rather than application deletes.
