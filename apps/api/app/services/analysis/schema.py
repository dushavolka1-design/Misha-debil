"""Strict JSON Schema for LLM fact extraction. Extra fields are rejected."""

from __future__ import annotations

FINDING_ITEM_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "kind",
        "entity_type",
        "raw_text",
        "normalized_value",
        "confidence",
        "uncertainty_state",
        "citation",
    ],
    "properties": {
        "kind": {"type": "string", "enum": ["fact", "inference"]},
        "entity_type": {
            "type": "string",
            "enum": [
                "document.type",
                "doc.title",
                "doc.number",
                "party.name",
                "party.role",
                "party.identifier",
                "party.address",
                "doc.date.sign",
                "doc.date.effective",
                "doc.date.end",
                "duration",
                "amount.value",
                "amount.currency",
                "amount.vat",
                "obligation.summary",
                "right.summary",
                "penalty.clause",
                "termination.clause_ref",
                "renewal.clause_ref",
                "dispute.jurisdiction",
                "personal_data.clause",
                "annex.ref",
                "reference.ref",
                "signature.block",
            ],
        },
        "raw_text": {"type": "string", "minLength": 1, "maxLength": 2000},
        "normalized_value": {},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "uncertainty_state": {
            "type": "string",
            "enum": ["ok", "low_confidence", "ambiguous", "insufficient_data", "needs_review"],
        },
        "citation": {
            "type": "object",
            "additionalProperties": False,
            "required": ["page", "bbox", "quote"],
            "properties": {
                "page": {"type": "integer", "minimum": 1},
                "bbox": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["x", "y", "w", "h"],
                    "properties": {
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "w": {"type": "number"},
                        "h": {"type": "number"},
                    },
                },
                "quote": {"type": "string", "minLength": 1, "maxLength": 500},
            },
        },
    },
}

FACTS_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["findings"],
    "properties": {
        "findings": {"type": "array", "items": FINDING_ITEM_SCHEMA},
    },
}

SCHEMA_VERSION = "finding_schema.v1"
PIPELINE_VERSION = "analysis.pipeline.v1"
PROMPT_VERSION = "facts.extract.v1"
