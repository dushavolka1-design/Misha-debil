from __future__ import annotations

"""Append-only feedback — never mutates analysis results."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4


class FeedbackKind(StrEnum):
    USEFUL = "useful"
    ERROR = "error"
    BAD_CITATION = "bad_citation"


@dataclass(frozen=True)
class FeedbackEvent:
    id: UUID
    user_id: UUID
    target_type: str  # finding|rule_hit|report
    target_id: str
    kind: FeedbackKind
    comment: str | None
    created_at: datetime
    # Explicit: does not rewrite results


@dataclass
class FeedbackStore:
    events: list[FeedbackEvent] = field(default_factory=list)

    def add(
        self,
        *,
        user_id: UUID,
        target_type: str,
        target_id: str,
        kind: FeedbackKind,
        comment: str | None = None,
    ) -> FeedbackEvent:
        ev = FeedbackEvent(
            id=uuid4(),
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            kind=kind,
            comment=comment,
            created_at=datetime.now(timezone.utc),
        )
        self.events.append(ev)
        return ev

    def for_target(self, target_id: str) -> list[FeedbackEvent]:
        return [e for e in self.events if e.target_id == target_id]
