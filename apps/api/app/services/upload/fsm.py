from __future__ import annotations

from enum import StrEnum


class DocumentState(StrEnum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    QUARANTINED = "QUARANTINED"
    SCANNING = "SCANNING"
    CLEAN = "CLEAN"
    PROCESSING = "PROCESSING"
    READY = "READY"
    REJECTED = "REJECTED"
    INFECTED = "INFECTED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    DELETING = "DELETING"
    DELETED = "DELETED"


TERMINAL = frozenset(
    {
        DocumentState.REJECTED,
        DocumentState.INFECTED,
        DocumentState.FAILED,
        DocumentState.EXPIRED,
        DocumentState.DELETED,
    },
)

# Allowed transitions (from → frozenset(to))
TRANSITIONS: dict[DocumentState, frozenset[DocumentState]] = {
    DocumentState.CREATED: frozenset({DocumentState.UPLOADING, DocumentState.EXPIRED, DocumentState.DELETING}),
    DocumentState.UPLOADING: frozenset(
        {DocumentState.QUARANTINED, DocumentState.REJECTED, DocumentState.EXPIRED, DocumentState.DELETING, DocumentState.FAILED},
    ),
    DocumentState.QUARANTINED: frozenset(
        {DocumentState.SCANNING, DocumentState.REJECTED, DocumentState.DELETING, DocumentState.EXPIRED},
    ),
    DocumentState.SCANNING: frozenset(
        {
            DocumentState.CLEAN,
            DocumentState.INFECTED,
            DocumentState.FAILED,
            DocumentState.DELETING,
            DocumentState.EXPIRED,
        },
    ),
    DocumentState.CLEAN: frozenset({DocumentState.PROCESSING, DocumentState.DELETING, DocumentState.EXPIRED}),
    DocumentState.PROCESSING: frozenset(
        {DocumentState.READY, DocumentState.FAILED, DocumentState.DELETING, DocumentState.EXPIRED},
    ),
    DocumentState.READY: frozenset({DocumentState.DELETING, DocumentState.EXPIRED}),
    DocumentState.REJECTED: frozenset({DocumentState.DELETING}),
    DocumentState.INFECTED: frozenset({DocumentState.DELETING}),
    DocumentState.FAILED: frozenset({DocumentState.DELETING, DocumentState.SCANNING, DocumentState.PROCESSING}),
    DocumentState.EXPIRED: frozenset({DocumentState.DELETING}),
    DocumentState.DELETING: frozenset({DocumentState.DELETED}),
    DocumentState.DELETED: frozenset(),
}

# States where user/app may download derived (never quarantine)
DOWNLOADABLE = frozenset({DocumentState.READY})
# Quarantine readable only by scanner/worker internals
QUARANTINE_READABLE_BY_PIPELINE = frozenset(
    {DocumentState.QUARANTINED, DocumentState.SCANNING, DocumentState.CLEAN, DocumentState.PROCESSING},
)


class InvalidTransition(ValueError):
    pass


def transition(current: DocumentState, target: DocumentState) -> DocumentState:
    allowed = TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidTransition(f"{current} -> {target} not allowed")
    return target


def can_process(state: DocumentState) -> bool:
    return state in {DocumentState.CLEAN, DocumentState.PROCESSING}


def can_user_download(state: DocumentState) -> bool:
    return state in DOWNLOADABLE
