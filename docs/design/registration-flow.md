# Registration/login — increment 1

Status: source implementation and isolated QA; full application/backend validation pending.

## Flow
1. Username/display_name, email, one password. Welcome integrated. No passport, medical data, repeated password or signup avatar; avatar remains in profile.
2. Current legal documents from /legal/documents/active. Required terms_of_use, offer and personal_data_processing separate and false. Marketing optional/false. Versioned full-text links and matching consent_id/version/hash payload. Invalid, duplicate or missing required metadata blocks registration. Privacy linked when returned; no medical consent.
3. Conditional next-step screen: checking mailbox is not proof of delivery or verification. Existing login link; no fake resend timer/recovery action.

## API and safety
Existing apiFetch, retries:0 on POST. Register retains display_name/email/password/locale ru-RU/accepts; login retains username/password and /app/analyzer destination. No backend/cookie/session/consent-evidence schema changes.

Field errors/summary, legal loading/failure/retry, disabled pending action plus synchronous duplicate-submit guard, generic auth errors and rate-limit feedback. Network/timeout has uncertain outcome, no automatic mutation retry. No raw CORS/backend errors or verification_token_dev. Password remains in React memory, clears on success, never written to localStorage/sessionStorage/logs.

## Missing workflows
Complete verification, resend, reset-password, expired/used links, blocked account, session expiry, onboarding and first-run setup are not implemented. Inspected backend has verify-email but no reset/resend endpoints. Safe contracts/mail-link flow required first. No end-to-end anti-enumeration audit is claimed.

RU implemented; shared PasswordInput labels configurable and demonstrated in English. Full RU/EN localization not implemented. No passport transliteration.
