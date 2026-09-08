"""Regression checks for untrusted model output at the schema boundary."""

import unittest
from copy import deepcopy
from typing import Any

from app.services.analysis.validate import (
    SchemaValidationError,
    reject_invalid_llm_findings,
    validate_facts_payload,
    validate_finding,
)


def finding() -> dict[str, Any]:
    return {
        "kind": "fact",
        "entity_type": "amount.value",
        "raw_text": "100 рублей",
        "normalized_value": 100,
        "confidence": 0.8,
        "uncertainty_state": "ok",
        "citation": {"page": 1, "bbox": {"x": 0, "y": 0, "w": 10, "h": 10}, "quote": "100 рублей"},
    }


class AnalysisSchemaBoundaryTests(unittest.TestCase):
    def test_valid_payload_is_preserved(self) -> None:
        item = finding()
        before = deepcopy(item)
        validate_facts_payload({"findings": [item]})
        accepted, rejected = reject_invalid_llm_findings([item])
        self.assertEqual(rejected, [])
        self.assertEqual(accepted, [before])
        self.assertIs(accepted[0], item)

    def test_non_finite_confidence_is_rejected(self) -> None:
        for value in [float("nan"), float("inf"), float("-inf"), True, -0.1, 1.1]:
            with self.subTest(value=value):
                item = {**finding(), "confidence": value}
                accepted, rejected = reject_invalid_llm_findings([item])
                self.assertEqual(accepted, [])
                self.assertEqual(len(rejected), 1)
                self.assertIn("$.confidence", rejected[0])

    def test_non_finite_coordinates_are_rejected(self) -> None:
        for key in ["x", "y", "w", "h"]:
            item = finding()
            item["citation"]["bbox"][key] = float("nan")
            with self.subTest(key=key), self.assertRaises(SchemaValidationError):
                validate_finding(item)

    def test_citation_page_must_be_positive_integer(self) -> None:
        for value in [True, 0, 1.5, "1"]:
            item = finding()
            item["citation"]["page"] = value
            with self.subTest(value=value), self.assertRaises(SchemaValidationError):
                validate_finding(item)

    def test_invalid_shapes_required_fields_and_enum_fail(self) -> None:
        item = finding()
        del item["citation"]
        invalid = [None, [], "value", item, {**finding(), "kind": "invented"}, {**finding(), "raw_text": ""}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(SchemaValidationError):
                validate_finding(value)

    def test_extra_keys_do_not_leak_into_error_or_crash_sorting(self) -> None:
        item = finding()
        item["synthetic-sensitive-key"] = "synthetic-sensitive-value"
        accepted, rejected = reject_invalid_llm_findings([item])
        self.assertEqual(accepted, [])
        self.assertNotIn("synthetic-sensitive", rejected[0])
        # Non-JSON callers may also pass mixed key types; reject predictably.
        with self.assertRaises(SchemaValidationError):
            validate_finding({**item, 17: "unexpected"})

    def test_rejection_does_not_drop_other_valid_findings(self) -> None:
        good = finding()
        bad = {**finding(), "confidence": float("nan")}
        accepted, rejected = reject_invalid_llm_findings([bad, good])
        self.assertEqual(accepted, [good])
        self.assertEqual(len(rejected), 1)


if __name__ == "__main__":
    unittest.main()
