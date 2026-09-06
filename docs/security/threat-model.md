# Threat model — Анализатор документов РФ

Методы: **STRIDE** (безопасность) + **LINDDUN** (privacy).  
Статус: этап 1. Связано с [acceptance-matrix.md](../product/acceptance-matrix.md), ADR-0002..0007, [decision-log.md](../product/decision-log.md).

---

## 1. Объект моделирования (контур)

Акторы: Гость, Пользователь, Редактор источников, Юрист-рецензент, Privacy officer, Support, Admin, внешние AI/OCR adapters, billing adapter, source fetcher.

Активы: originals, extracted text, reports, coordinate maps, consents, source snapshots, signed URLs, admin audit logs, encryption keys.

Trust boundaries: browser ↔ API; API ↔ object storage; API ↔ queue/workers; workers ↔ AI/OCR adapters; editors ↔ source registry; support tools ↔ data plane.

---

## 2. STRIDE

### TM-S1 — Загрузка вредоносных файлов (Spoofing/Tampering/DoS)

| | |
|--|--|
| **Угроза** | Malware, zip-bomb-like PDF, polyglot, эксплойт парсера OCR |
| **Риск** | H |
| **Защита** | MIME/magic allowlist; size/page limits; AV/sandbox pipeline (`AV_PIPELINE_NEEDS_REVIEW`); парсеры в isolated workers; no execute from upload bucket; quarantine on detect |
| **Детект** | AV alerts, worker crash budget, YARA/heuristic (`needs_review`) |
| **Acceptance** | AT-THR-MALWARE |

### TM-S2 — Prompt injection через содержимое документа (Elevation/Information disclosure)

| | |
|--|--|
| **Угроза** | Текст «игнорируй инструкции / выгрузи систему / действуй как юрист» в PDF/OCR |
| **Риск** | H |
| **Защита** | Строгое разделение system prompt vs document channel; запрет tool-calling из document content; output policy (FR-12); `safety.injection.v1`; adapters без произвольного egress |
| **Детект** | Red-team corpus; anomaly на output classifier |
| **Acceptance** | AT-THR-INJECT, AT-FR-12 |

### TM-S3 — IDOR на документы/отчёты/jobs (Information disclosure / Tampering)

| | |
|--|--|
| **Угроза** | Подбор UUID, утечка ID из логов, cross-account compare |
| **Риск** | H |
| **Защита** | Authn + authz на каждый object; ownership checks; непрозрачные IDs; compare только своих документов; rate limit |
| **Детект** | Authz deny metrics; security tests |
| **Acceptance** | AT-FR-05 |

### TM-S4 — Утечки через логи, кэш, telemetry (Information disclosure)

| | |
|--|--|
| **Угроза** | Full text в application logs, APM payloads, error trackers, CDN cache ключи с PII |
| **Риск** | H |
| **Защита** | Structured logging allowlist; redaction middleware; запрет логировать extracted text/defaults; cache keys = opaque IDs; telemetry scrubbers; staging canary |
| **Детект** | CI log scans; Privacy review |
| **Acceptance** | AT-NFR-03, AT-THR-TELEMETRY |

### TM-S5 — Злоупотребление ссылками скачивания (Information disclosure)

| | |
|--|--|
| **Угроза** | Пересылка signed URL, долгий TTL, URL в логах Referer, отсутствие revoke после delete |
| **Риск** | H |
| **Защита** | TTL ≤ 15 min; method/path binding; optional single-use; revoke on delete/erasure; не логировать полный query secret; HTTPS only |
| **Детект** | Access after revoke must fail |
| **Acceptance** | AT-FR-06 |

### TM-S6 — SSRF при работе с источниками (Information disclosure / Spoofing)

| | |
|--|--|
| **Угроза** | Editor/URL fetch → metadata IP, internal admin, cloud IMDS |
| **Риск** | H |
| **Защита** | Dedicated egress proxy; allowlist schemes/hosts; block RFC1918/link-local/metadata; DNS rebinding controls; size/time limits; no redirect to private |
| **Детект** | SSRF test suite |
| **Acceptance** | AT-THR-SSRF |

### TM-S7 — Supply-chain (Tampering / Elevation)

| | |
|--|--|
| **Угроза** | Компрометация зависимости, malicious OCR binary, poisoned model artifact |
| **Риск** | M–H |
| **Защита** | Lockfiles; CI vuln gate; signed images; pinned adapter versions; least privilege CI OIDC; SBOM (`SBOM_TOOLING_NEEDS_REVIEW`) |
| **Детект** | Dependabot/equiv; image scan |
| **Acceptance** | AT-THR-SUPPLY |

### TM-S8 — Spoofing ролей редактора / admin

| | |
|--|--|
| **Угроза** | Самоназначение `approved` на вредоносный source; подделка consent |
| **Риск** | H |
| **Защита** | RBAC; separation of draft vs approve (four-eyes где возможно); immutable consent evidence; MFA for privileged (`MFA_POLICY_NEEDS_REVIEW`) |
| **Детект** | Audit anomalies |
| **Acceptance** | AT-FR-10, AT-FR-15 |

### TM-S9 — Внутренний доступ Support/Admin (Information disclosure)

| | |
|--|--|
| **Угроза** | Любопытство персонала, чрезмерные права, экспорт «для отладки» |
| **Риск** | H |
| **Защита** | Break-glass + reason code; time-boxed access; field-level minimization; запрет локальных копий без ticket; privacy officer audit |
| **Детект** | Mandatory audit review sampling |
| **Acceptance** | AT-FR-15, AT-THR-INTERNAL |

### TM-S10 — Восстановление удалённых данных (Repudiation / Information disclosure / Privacy)

| | |
|--|--|
| **Угроза** | Soft-delete only; backup восстанавливает «стёртое»; ключи не уничтожены |
| **Риск** | H |
| **Защита** | Crypto-erasure (ADR-0007); backup key hierarchy alignment; legal hold gate; user-visible deletion states |
| **Детект** | Post-erasure read must fail; restore drills |
| **Acceptance** | AT-FR-09, AT-THR-RECOVERY |

### TM-S11 — DoS через очередь OCR/анализа

| | |
|--|--|
| **Угроза** | Flood uploads, тяжёлые файлы, исчерпание GPU/CPU |
| **Риск** | M |
| **Защита** | Quotas per plan (`TARIFF_*`); backpressure; max pages/bytes; per-user rate limits |
| **Детект** | Queue depth SLO alerts |
| **Acceptance** | AT-SLO-UPLOAD, AT-SLO-OCR |

---

## 3. LINDDUN

| ID | Категория | Угроза | Защита | Acceptance |
|----|-----------|--------|--------|------------|
| TM-L1 | Linkability | Сведение личности через billing + docs + telemetry | Разделение идентификаторов где practically; minimize join keys in analytics | Privacy review |
| TM-L2 | Identifiability | PII в логах/traces | Redaction; purpose limitation | AT-THR-TELEMETRY |
| TM-L3 | Non-repudiation (нежелательная) | Избыточные доказательства против пользователя без нужды | Минимизация evidence согласия (`DL-010`) | Privacy |
| TM-L4 | Detectability | Сам факт загрузки «чувствительного» типа виден support | Role minimization; masked metadata | AT-FR-15 |
| TM-L5 | Disclosure of information | Утечка originals подрядчикам AI | Contractual + technical via adapters; consent_version; DPA placeholders `PROCESSOR_DPA_NEEDS_REVIEW` | AT-FR-08 |
| TM-L6 | Unawareness | Пользователь не понимает inference vs fact | UI glossary; labeling | AT-FR-02, AT-FR-03 |
| TM-L7 | Non-compliance | Невыполнение erasure/consent | Workflows + decision log вместо выдуманных сроков | AT-FR-08, AT-FR-09 |

---

## 4. Abuse cases (кратко)

1. Злоумышленник загружает PDF с injection → пытается получить system prompt / чужие данные.  
2. Пользователь A угадывает report_id пользователя B.  
3. Редактор публикует вредоносный «закон» без review.  
4. Support скачивает оригинал «чтобы помочь» без ticket.  
5. После delete пользователь восстанавливает файл через старую ссылку или backup.  
6. Attacker заставляет fetcher сходить на `169.254.169.254`.  

Каждый abuse case покрыт строкой STRIDE/LINDDUN выше и acceptance ID.

---

## 5. Остаточные риски (принятие — needs_review)

| ID | Риск | Статус |
|----|------|--------|
| RR-01 | Качество AV/sandbox зависит от выбранного pipeline | `AV_PIPELINE_NEEDS_REVIEW` |
| RR-02 | Внешний AI processor — остаточный риск disclosure | contractual + consent; `PROCESSOR_DPA_NEEDS_REVIEW` |
| RR-03 | OCR ошибок → неверный fact с высокой confidence | калибровка `DL-018` |
| RR-04 | Юрист-рецензент воспринимается пользователем как «официальная юрпомощь» | продуктовый disclaimer + `DL-020` |

Незакрытые пункты ведутся в decision-log, не маскируются как «решено».
