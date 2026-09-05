# Acceptance matrix — этап 1 (проектирование) и готовность к реализации

Назначение: связать требования с риском, методом проверки и ответственным. High-risk потоки **обязаны** иметь защиту в threat model и проверяемый тест.

Легенда риска: `H` high, `M` medium, `L` low.  
Роли владельца теста: `Eng`, `Sec`, `Privacy`, `QA`, `LegalReview` (внутренняя), `Product`.

Placeholders ответственности персон: `OWNER_ROLE_*` при назначении конкретных людей — вне этого файла.

---

## 1. Матрица

| Req ID | Связь | Риск | Защита / критерий | Метод тестирования | Ответственный |
|--------|-------|------|-------------------|--------------------|---------------|
| AT-FR-01 | FR-01 | H | Original, extracted text, report в разных stores/keys; нет silent overwrite | Integration: upload → assert storage keys/prefixes isolated; attempt cross-read denied | Eng + Sec |
| AT-FR-02 | FR-02 | H | Fact без provenance отклоняется API schema | Contract test JSON schema; golden fixtures | Eng + QA |
| AT-FR-03 | FR-03 | H | Disclaimer видим на analyze/compare/wizard | UI e2e + a11y text assert; snapshot locales ru-RU | QA + Product |
| AT-FR-04 | FR-04 | H | Неapproved source snapshot не попадает в user analysis | Integration: draft source → analyze → expect block/`needs_review` | Eng + LegalReview |
| AT-FR-05 | FR-05 | H | IDOR: user B не читает document/report A | Security test: swap IDs/tokens → 403/404; fuzz object IDs | Sec + QA |
| AT-FR-06 | FR-06 | H | Expired/revoked download URL не отдаёт объект | Security test TTL + revoke-on-delete | Sec |
| AT-FR-07 | FR-07 | M | Job идемпотентен; статусы наблюдаемы | Integration queue; duplicate submit | Eng |
| AT-FR-08 | FR-08 | H | Без актуального consent_version обработка не стартует | e2e consent gate; version bump forces re-consent | Privacy + QA |
| AT-FR-09 | FR-09 | H | Delete → jobs stopped, URLs revoked, erasure workflow | e2e + storage probe after crypto-erasure | Privacy + Eng |
| AT-FR-10 | FR-10 | M | Draft check pack не влияет на prod analysis | Integration feature flag / registry | Eng + LegalReview |
| AT-FR-11 | FR-11 | M | Подсветка координат совпадает с underlay page transform | Visual/golden coordinate tests | Eng + QA |
| AT-FR-12 | FR-12 | H | Модель/UI не выдаёт «заключение юриста/врача» | Red-team prompt suite + output policy classifier tests | Sec + Product + LegalReview |
| AT-FR-13 | FR-13 | M | Compare маркирует missing/diff/insufficient | Golden multi-doc fixtures | QA |
| AT-FR-14 | FR-14 | M | Ответы привязаны к form_version; смена версии не молча мигрирует | Integration version pin | Eng |
| AT-FR-15 | FR-15 | H | Break-glass без reason code невозможен; пишется audit | Security + audit log assert | Sec + Privacy |
| AT-NFR-03 | NFR-03 | H | Лог/telemetry sample не содержит full document text / raw PII fields | Log redaction tests; CI canary on logger | Sec + Privacy |
| AT-NFR-04 | NFR-04 | H | At-rest encryption enabled on original bucket | Infra/config assert; negative test misconfig | Sec + Eng |
| AT-SLO-UPLOAD | §9 | M | Reject >25MiB / >50 pages with clear error | API boundary tests | QA |
| AT-SLO-OCR | §9 | M | p95 измеряется; breach → alert (не silent) | Load/synthetic monitoring | Eng |
| AT-UNCERT | §10 | H | `insufficient_data`/`needs_review` не заменяются «ok» advice | Golden adversarial docs; policy unit tests | QA + Product |
| AT-THR-MALWARE | TM-S1 | H | Malicious upload не исполняется в trusted network; quarantine | Pipeline security test (benign eicar-like policy per `AV_PIPELINE_NEEDS_REVIEW`) | Sec |
| AT-THR-INJECT | TM-S2 | H | Prompt injection в теле PDF не эскалирует tools/exfil | Red-team corpus; adapter allowlist | Sec |
| AT-THR-SSRF | TM-S6 | H | Source fetcher blocklist private IP / metadata endpoints | Unit+integration SSRF suite | Sec |
| AT-THR-SUPPLY | TM-S7 | M | Lockfile + vuln gate CI | CI policy | Eng + Sec |
| AT-THR-TELEMETRY | TM-L2 | H | Нет утечки текста документа в стороннюю telemetry | Privacy review + traffic assert staging | Privacy + Sec |
| AT-THR-INTERNAL | TM-S9 | H | Internal admin API mTLS/SSO + RBAC | Security config tests | Sec |
| AT-THR-RECOVERY | TM-S10 | H | После erasure ключей объект недоступен; backups соблюдают policy | Restore drill + key destruction test | Privacy + Eng |
| AT-X-01 | X-01/X-02 | H | Продуктовые строки и model policy запрещают lawyer/doctor opinion | Copy review + AT-FR-12 | Product + LegalReview |

---

## 2. Минимальный набор high-risk acceptance (must-pass до prod)

1. AT-FR-05 IDOR  
2. AT-FR-06 Download URL abuse  
3. AT-FR-08 Consent gate  
4. AT-FR-09 Erasure  
5. AT-FR-12 No lawyer/doctor conclusion  
6. AT-THR-MALWARE  
7. AT-THR-INJECT  
8. AT-THR-SSRF  
9. AT-NFR-03 Log/telemetry leak  
10. AT-UNCERT Uncertainty honesty  

---

## 3. Трассировка документации этапа 1

| Артефакт | Покрытие acceptance |
|----------|---------------------|
| requirements.md | AT-FR-*, AT-NFR-*, AT-SLO-*, AT-UNCERT, AT-X-01 |
| threat-model.md | AT-THR-* |
| ADR-0003..0007 | AT-FR-01, 04, 08, 09, 11 |
| glossary.md | AT-FR-02, AT-UNCERT (термины в тестах) |

Статус этапа 1: матрица **опубликована**.  
Этап 14: автоматические тесты и evidence — [../quality/quality-gates.md](../quality/quality-gates.md), [../quality/traceability.md](../quality/traceability.md). **Production: NO-GO** until critical blockers in [../ops/staging-go-no-go.md](../ops/staging-go-no-go.md) close.
