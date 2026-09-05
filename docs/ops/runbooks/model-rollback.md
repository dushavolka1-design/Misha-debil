# Runbook: Model / prompt rollback

1. Identify bad `prompt_version` / `llm_model_version` from analysis runs + AI eval spike (unsupported claims, injection fails).
2. Pin previous known-good versions via env/config; disable new model in factory.
3. Quarantine in-flight jobs; requeue with pinned version if safe.
4. Re-run `python -m app.scripts.run_ai_eval`; require gate PASS before re-enable.
5. Audit: who changed model, when, why; update decision-log if policy changed.

Do not hot-fix prompts in production without eval + LegalReview for policy strings.
