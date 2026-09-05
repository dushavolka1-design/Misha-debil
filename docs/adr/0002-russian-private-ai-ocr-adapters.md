# ADR-0002 — Российский приватный AI/OCR через adapters

- Status: Accepted (этап 1)
- Date: 2026-08-11

## Context

OCR и LLM-анализ необходимы, но вендоры, договоры обработки и контуры ещё не зафиксированы (`DL-011`, `PROCESSOR_DPA_NEEDS_REVIEW`). Нужна замена провайдера без переписывания доменной логики и контроль над тем, что уходит наружу.

## Decision

Все вызовы AI/OCR идут только через **Adapters**:

```text
Domain workers → OcrPort / LlmPort → AdapterImpl(vendor)
```

Требования к порту:

- вход: bytes/refs + purpose + consent_version id;
- выход: структурированный OCR/analysis result без «свободного юридического вердикта»;
- timeouts, retries, circuit breaker;
- redaction hooks до telemetry;
- версия модели/провайдера в provenance fact/inference.

Конкретные вендоры **не** выбираются в этом ADR.

## Alternatives

| Alternative | Why not |
|-------------|---------|
| Прямые SDK вызовы из доменного кода | Vendor lock-in, сложно аудировать egress |
| Один self-host only | Может стать целью позже; сейчас риск срока/качества |
| Публичный зарубежный API по умолчанию | Конфликт с продуктовой установкой «российский приватный контур» без decision log |

## Consequences

- **+** Смена вендора = новый adapter + contract test.  
- **+** Единая точка enforce consent и output policy.  
- **−** Нужны fake adapters для CI.  
- **−** Остаточный риск disclosure у процессора (RR-02).

## Links

requirements FR-08/12; threat-model TM-S2/TM-L5; AT-FR-08, AT-FR-12, AT-THR-INJECT.
