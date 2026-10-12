# Evaluation

`golden/kyc_v0.jsonl` is the starter golden set (12 items). It covers disclosable rejections,
restricted (tipping-off) cases, prompt injection, refusals, Bahasa Melayu and role-based access.

Week 3 adds the runner: DeepEval + RAGAS metrics (faithfulness, answer relevancy, context
precision/recall) plus deterministic checks (`must_not_contain`, expected citation, behaviour),
wired into CI as a quality gate. Grow this set to 100+ items, and add every real failure you see.
