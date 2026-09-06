# Runbook: Breach / personal data incident

1. **Contain** — revoke sessions, rotate secrets, isolate buckets, disable egress.
2. **Assess** — data classes from [data-inventory.md](../../quality/data-inventory.md); count affected subjects.
3. **Notify** — Privacy officer leads regulator/user notices per `BREACH_NOTICE_POLICY_NEEDS_REVIEW` (do not invent timelines).
4. **Preserve** — forensic copies under legal hold; do not silently purge audit.
5. **Eradicate & recover** — patch, rotate keys, restore from clean backup if integrity lost.
6. **Lessons** — update threat-model + quality gates; schedule follow-up drill.

Never paste document text into tickets/chat.
