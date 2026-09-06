from app.services.analysis.local_facts import extract_local_facts
from app.services.analysis.records import PageRecord


def _page(text: str, number: int = 1) -> PageRecord:
    return PageRecord(
        page_number=number,
        width=595,
        height=842,
        rotation=0,
        confidence=0.9,
        language="ru",
        source="embedded_text",
        text=text,
        layout=[],
        words=[],
    )


def test_local_facts_always_keep_excerpt() -> None:
    pages = [_page("УВЕДОМЛЕНИЕ о прибытии. Сумма 10 000 руб. ИНН 7707083893 01.02.2026")]
    findings = extract_local_facts(pages)
    types = {f.entity_type for f in findings}
    assert "doc.excerpt" in types
    excerpt = next(f for f in findings if f.entity_type == "doc.excerpt")
    assert excerpt.citation["page"] == 1
    assert excerpt.citation["quote"]
    assert any(f.entity_type == "amount.value" for f in findings)


def test_local_facts_empty_scan_is_honest() -> None:
    pages = [_page("   ")]
    findings = extract_local_facts(pages)
    assert findings
    assert findings[0].entity_type == "doc.extract"
    assert findings[0].citation["quote"]


def test_local_facts_all_pages_parties_and_ogrn() -> None:
    pages = [
        _page("ДОГОВОР подряда\nРаботодатель: ООО Пример\nИНН 7707083893\nОГРН 1027700132195"),
        _page("Исполнитель: Иванов Иван Иванович\nСумма 25 000 руб.\nАдрес: г. Москва, ул. Тверская, д. 1"),
    ]
    findings = extract_local_facts(pages)
    types = {f.entity_type for f in findings}
    assert "doc.excerpt" in types
    assert "doc.title" in types
    assert "party.role" in types
    assert "party.identifier" in types
    excerpt = next(f for f in findings if f.entity_type == "doc.excerpt")
    assert "Иванов" in excerpt.normalized_value
    assert any(f.entity_type == "party.name" for f in findings)
    ogrn = [
        f
        for f in findings
        if f.entity_type == "party.identifier"
        and isinstance(f.normalized_value, dict)
        and f.normalized_value.get("type") == "ogrn"
    ]
    assert ogrn
