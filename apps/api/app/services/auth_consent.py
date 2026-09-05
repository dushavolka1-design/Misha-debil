from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from app.security.crypto import (
    canonical_sha256,
    expires_in,
    hash_password,
    hash_token,
    new_session_token,
    new_verification_token,
    utcnow,
    verify_password,
)


EVIDENCE_SCHEMA = "consent_evidence.v1"

REQUIRED_AT_REGISTRATION = (
    "terms_of_use",
    "offer",
    "personal_data_processing",
)

OPTIONAL_AT_REGISTRATION = ("marketing",)

SPECIAL_MEDICAL = "special_categories.medical"

# Features blocked without active accept of these consent_ids
FEATURE_GATES: dict[str, tuple[str, ...]] = {
    "product_use": ("terms_of_use", "offer", "personal_data_processing"),
    "document_ordinary": ("terms_of_use", "offer", "personal_data_processing"),
    "document_medical": ("terms_of_use", "offer", "personal_data_processing", SPECIAL_MEDICAL),
    "marketing": ("marketing",),
    "payment_subscribe": ("terms_of_use", "offer", "personal_data_processing", "payment_recurring"),
}

# Always allowed even if material re-consent pending
ALWAYS_ALLOWED_ACTIONS = frozenset({"export", "delete_account", "logout", "privacy_read"})


class PublicationStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    RETIRED = "retired"


class ConsentAction(StrEnum):
    ACCEPT = "accept"
    WITHDRAW = "withdraw"


@dataclass
class LegalDoc:
    id: UUID
    consent_id: str
    consent_version: str
    locale: str
    canonical_text: str
    content_hash: str
    effective_at: datetime
    supersedes_id: UUID | None
    reviewer_id: str | None
    publication_status: PublicationStatus
    body_path: str
    immutable: bool = False


@dataclass
class ConsentEventRecord:
    id: UUID
    subject_user_id: UUID
    legal_document_id: UUID
    consent_id: str
    consent_version: str
    content_hash: str
    action: ConsentAction
    occurred_at: datetime
    ip: str | None
    user_agent: str | None
    locale: str
    request_id: str
    evidence_schema_version: str


@dataclass
class UserRecord:
    id: UUID
    tenant_id: UUID
    email: str
    password_hash: str
    role: str
    status: str
    email_verified_at: datetime | None = None
    created_at: datetime = field(default_factory=utcnow)
    display_name: str = ""
    avatar_jpeg: bytes | None = None


@dataclass
class SessionRecord:
    id: UUID
    user_id: UUID
    tenant_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    rotated_from: UUID | None = None
    user_agent: str | None = None
    ip: str | None = None


@dataclass
class EmailToken:
    user_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None


class AppendOnlyViolation(RuntimeError):
    pass


class AuthConsentError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


class AuthConsentStore:
    """In-memory store for local/test; mirrors durable schema semantics."""

    def __init__(self) -> None:
        self.users: dict[UUID, UserRecord] = {}
        self.users_by_email: dict[str, UUID] = {}
        self.users_by_name: dict[str, UUID] = {}
        self.sessions: dict[UUID, SessionRecord] = {}
        self.sessions_by_token: dict[str, UUID] = {}
        self.legal: dict[UUID, LegalDoc] = {}
        self.consent_events: list[ConsentEventRecord] = []
        self.email_tokens: list[EmailToken] = []
        self.deletion_requests: dict[UUID, datetime] = {}
        self.export_requests: dict[UUID, datetime] = {}
        self._consent_locked = True

    def publish_legal(
        self,
        *,
        consent_id: str,
        consent_version: str,
        locale: str,
        canonical_text: str,
        body_path: str,
        reviewer_id: str,
        supersedes_id: UUID | None = None,
        effective_at: datetime | None = None,
    ) -> LegalDoc:
        content_hash = canonical_sha256(canonical_text)
        doc = LegalDoc(
            id=uuid4(),
            consent_id=consent_id,
            consent_version=consent_version,
            locale=locale,
            canonical_text=canonical_text,
            content_hash=content_hash,
            effective_at=effective_at or utcnow(),
            supersedes_id=supersedes_id,
            reviewer_id=reviewer_id,
            publication_status=PublicationStatus.PUBLISHED,
            body_path=body_path,
            immutable=True,
        )
        if supersedes_id and supersedes_id in self.legal:
            old = self.legal[supersedes_id]
            if old.immutable and old.publication_status == PublicationStatus.PUBLISHED:
                old.publication_status = PublicationStatus.RETIRED
        self.legal[doc.id] = doc
        return doc

    def index_user(self, user: UserRecord) -> None:
        self.users[user.id] = user
        self.users_by_email[user.email.lower()] = user.id
        if user.display_name:
            self.users_by_name[user.display_name.casefold()] = user.id

    def drop_name_index(self, user: UserRecord) -> None:
        if not user.display_name:
            return
        key = user.display_name.casefold()
        if self.users_by_name.get(key) == user.id:
            del self.users_by_name[key]

    def lookup_login(self, identifier: str) -> UUID | None:
        raw = (identifier or "").strip()
        if not raw:
            return None
        if "@" in raw:
            return self.users_by_email.get(raw.lower())
        return self.users_by_name.get(raw.casefold())

    def mutate_published(self, doc_id: UUID, **_: Any) -> None:
        doc = self.legal[doc_id]
        if doc.immutable and doc.publication_status in {
            PublicationStatus.PUBLISHED,
            PublicationStatus.RETIRED,
        }:
            raise AuthConsentError("immutable_legal", "Published legal document cannot be edited", http_status=409)

    def active_legal(self, consent_id: str, locale: str = "ru-RU") -> LegalDoc | None:
        candidates = [
            d
            for d in self.legal.values()
            if d.consent_id == consent_id
            and d.locale == locale
            and d.publication_status == PublicationStatus.PUBLISHED
            and d.effective_at <= utcnow()
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda d: (d.effective_at, d.consent_version), reverse=True)[0]

    def append_consent_event(self, event: ConsentEventRecord) -> ConsentEventRecord:
        self.consent_events.append(event)
        return event

    def update_consent_event(self, _event_id: UUID, **_: Any) -> None:
        raise AppendOnlyViolation("consent_events are append-only")

    def delete_consent_event(self, _event_id: UUID) -> None:
        raise AppendOnlyViolation("consent_events are append-only")

    def latest_action(self, user_id: UUID, consent_id: str) -> ConsentEventRecord | None:
        events = [e for e in self.consent_events if e.subject_user_id == user_id and e.consent_id == consent_id]
        if not events:
            return None
        return sorted(events, key=lambda e: e.occurred_at, reverse=True)[0]

    def has_active_accept(self, user_id: UUID, consent_id: str, *, require_current: bool = True) -> bool:
        active = self.active_legal(consent_id)
        if not active:
            return False
        latest = self.latest_action(user_id, consent_id)
        if not latest or latest.action != ConsentAction.ACCEPT:
            return False
        if require_current and latest.content_hash != active.content_hash:
            return False
        return True


def seed_demo_legal(store: AuthConsentStore, legal_root: str) -> None:
    from pathlib import Path

    from app.services.legal_package import LEGAL_DOC_SEED

    root = Path(legal_root)
    for consent_id, version, locale, folder in LEGAL_DOC_SEED:
        already = next(
            (
                d
                for d in store.legal.values()
                if d.consent_id == consent_id and d.consent_version == version and d.locale == locale
            ),
            None,
        )
        if already:
            continue
        path = root / folder / consent_id / f"{version}.{locale}.md"
        text = path.read_text(encoding="utf-8")
        previous = store.active_legal(consent_id, locale)
        store.publish_legal(
            consent_id=consent_id,
            consent_version=version,
            locale=locale,
            canonical_text=text,
            body_path=str(path.as_posix()),
            reviewer_id="reviewer_demo_local_only",
            supersedes_id=previous.id if previous else None,
        )


@dataclass
class AcceptSpec:
    consent_id: str
    consent_version: str
    content_hash: str


class AuthConsentService:
    def __init__(self, store: AuthConsentStore) -> None:
        self.store = store

    def register(
        self,
        *,
        email: str,
        password: str,
        accepts: list[AcceptSpec],
        locale: str,
        ip: str | None,
        user_agent: str | None,
        request_id: str,
        display_name: str,
        avatar_jpeg: bytes | None = None,
    ) -> tuple[UserRecord, str, str]:
        """Returns user, verification_token (plaintext once), generic message token for anti-enum."""
        from app.services.auth_profile import assert_password_strength, normalize_display_name

        email_n = email.strip().lower()
        # Anti-enumeration: always take similar work even if email exists
        existing = self.store.users_by_email.get(email_n)
        required = set(REQUIRED_AT_REGISTRATION)
        got = {a.consent_id for a in accepts}
        # marketing optional
        if not required.issubset(got):
            raise AuthConsentError(
                "consents_required",
                "Required consents missing: terms, offer, and ordinary personal data",
                http_status=400,
            )
        if SPECIAL_MEDICAL in got:
            raise AuthConsentError(
                "medical_consent_forbidden_at_registration",
                "Medical special-category consent must not be collected at registration",
                http_status=400,
            )

        for spec in accepts:
            active = self.store.active_legal(spec.consent_id, locale)
            if not active:
                raise AuthConsentError("legal_missing", f"No active legal document for {spec.consent_id}")
            if (
                active.consent_version != spec.consent_version
                or active.content_hash != spec.content_hash
            ):
                raise AuthConsentError(
                    "legal_version_mismatch",
                    "Consent version/hash does not match active published document",
                    http_status=400,
                )

        if existing:
            # Uniform response path: do not create user, still return generic
            return (
                self.store.users[existing],
                "",
                "If the email is eligible, a verification message was sent",
            )

        name = normalize_display_name(display_name)
        taken = self.store.users_by_name.get(name.casefold())
        if taken and taken != existing:
            raise AuthConsentError("username_taken", "Это имя пользователя уже занято", http_status=400)
        assert_password_strength(password, email_n)

        user = UserRecord(
            id=uuid4(),
            tenant_id=uuid4(),
            email=email_n,
            password_hash=hash_password(password),
            role="user",
            status="pending_verification",
            display_name=name,
            avatar_jpeg=avatar_jpeg,
        )
        self.store.index_user(user)

        for spec in accepts:
            active = self.store.active_legal(spec.consent_id, locale)
            assert active is not None
            self._record_accept(
                user=user,
                doc=active,
                locale=locale,
                ip=ip,
                user_agent=user_agent,
                request_id=request_id,
            )

        verify = new_verification_token()
        self.store.email_tokens.append(
            EmailToken(user_id=user.id, token_hash=hash_token(verify), expires_at=expires_in(hours=24)),
        )
        return user, verify, "If the email is eligible, a verification message was sent"

    def verify_email(self, token: str) -> bool:
        th = hash_token(token)
        for item in self.store.email_tokens:
            if item.token_hash == th and item.used_at is None and item.expires_at >= utcnow():
                item.used_at = utcnow()
                user = self.store.users[item.user_id]
                user.email_verified_at = utcnow()
                user.status = "active"
                return True
        return False

    def login(
        self,
        *,
        password: str,
        ip: str | None,
        user_agent: str | None,
        email: str | None = None,
        username: str | None = None,
        previous_session_token: str | None = None,
        require_verified: bool = False,
    ) -> tuple[str, SessionRecord] | None:
        ident = (username or email or "").strip()
        user_id = self.store.lookup_login(ident)
        # Dummy hash verify timing pad
        dummy = hash_password("timing-pad-password-xx")
        if not user_id:
            verify_password(dummy, password)
            return None
        user = self.store.users[user_id]
        if not verify_password(user.password_hash, password):
            return None
        if user.status == "deletion_requested":
            return None
        if require_verified and user.status == "pending_verification":
            return None
        if previous_session_token:
            self.revoke_session_token(previous_session_token)
        raw = new_session_token()
        sess = SessionRecord(
            id=uuid4(),
            user_id=user.id,
            tenant_id=user.tenant_id,
            token_hash=hash_token(raw),
            expires_at=expires_in(days=14),
            user_agent=user_agent,
            ip=ip,
        )
        self.store.sessions[sess.id] = sess
        self.store.sessions_by_token[sess.token_hash] = sess.id
        return raw, sess

    def revoke_session_token(self, raw_token: str) -> None:
        th = hash_token(raw_token)
        sid = self.store.sessions_by_token.get(th)
        if not sid:
            return
        self.store.sessions[sid].revoked_at = utcnow()

    def revoke_all_sessions(self, user_id: UUID, *, except_token: str | None = None) -> int:
        keep = hash_token(except_token) if except_token else None
        n = 0
        for sess in self.store.sessions.values():
            if sess.user_id == user_id and sess.revoked_at is None:
                if keep and sess.token_hash == keep:
                    continue
                sess.revoked_at = utcnow()
                n += 1
        return n

    def user_from_session(self, raw_token: str) -> UserRecord | None:
        th = hash_token(raw_token)
        sid = self.store.sessions_by_token.get(th)
        if not sid:
            return None
        sess = self.store.sessions[sid]
        if sess.revoked_at is not None or sess.expires_at < utcnow():
            return None
        return self.store.users.get(sess.user_id)

    def _record_accept(
        self,
        *,
        user: UserRecord,
        doc: LegalDoc,
        locale: str,
        ip: str | None,
        user_agent: str | None,
        request_id: str,
    ) -> ConsentEventRecord:
        event = ConsentEventRecord(
            id=uuid4(),
            subject_user_id=user.id,
            legal_document_id=doc.id,
            consent_id=doc.consent_id,
            consent_version=doc.consent_version,
            content_hash=doc.content_hash,
            action=ConsentAction.ACCEPT,
            occurred_at=utcnow(),
            ip=ip,
            user_agent=(user_agent or "")[:300] or None,
            locale=locale,
            request_id=request_id,
            evidence_schema_version=EVIDENCE_SCHEMA,
        )
        return self.store.append_consent_event(event)

    def accept(
        self,
        user: UserRecord,
        *,
        consent_id: str,
        consent_version: str,
        content_hash: str,
        locale: str,
        ip: str | None,
        user_agent: str | None,
        request_id: str,
    ) -> ConsentEventRecord:
        active = self.store.active_legal(consent_id, locale)
        if not active or active.consent_version != consent_version or active.content_hash != content_hash:
            raise AuthConsentError("legal_version_mismatch", "Active legal version mismatch")
        return self._record_accept(
            user=user,
            doc=active,
            locale=locale,
            ip=ip,
            user_agent=user_agent,
            request_id=request_id,
        )

    def withdraw(
        self,
        user: UserRecord,
        *,
        consent_id: str,
        locale: str,
        ip: str | None,
        user_agent: str | None,
        request_id: str,
    ) -> ConsentEventRecord:
        active = self.store.active_legal(consent_id, locale)
        if not active:
            raise AuthConsentError("legal_missing", "No active document")
        # Must have prior accept to withdraw
        if not self.store.has_active_accept(user.id, consent_id, require_current=False):
            raise AuthConsentError("nothing_to_withdraw", "No prior acceptance")
        event = ConsentEventRecord(
            id=uuid4(),
            subject_user_id=user.id,
            legal_document_id=active.id,
            consent_id=active.consent_id,
            consent_version=active.consent_version,
            content_hash=active.content_hash,
            action=ConsentAction.WITHDRAW,
            occurred_at=utcnow(),
            ip=ip,
            user_agent=(user_agent or "")[:300] or None,
            locale=locale,
            request_id=request_id,
            evidence_schema_version=EVIDENCE_SCHEMA,
        )
        return self.store.append_consent_event(event)

    def assert_feature_allowed(self, user: UserRecord, feature: str) -> None:
        if feature in ALWAYS_ALLOWED_ACTIONS or feature in {"export", "delete_account"}:
            return
        needed = FEATURE_GATES.get(feature, FEATURE_GATES["product_use"])
        missing = [c for c in needed if not self.store.has_active_accept(user.id, c)]
        if missing:
            raise AuthConsentError(
                "consent_required",
                "Active consent required: " + ", ".join(missing),
                http_status=403,
            )

    def proof_text(self, event_id: UUID) -> str:
        for e in self.store.consent_events:
            if e.id == event_id:
                doc = self.store.legal[e.legal_document_id]
                if canonical_sha256(doc.canonical_text) != e.content_hash:
                    raise AuthConsentError("hash_mismatch", "Stored text does not match event hash", http_status=500)
                return doc.canonical_text
        raise AuthConsentError("not_found", "Consent event not found", http_status=404)

    def privacy_dashboard(self, user: UserRecord) -> dict[str, Any]:
        items = []
        for consent_id in [
            *REQUIRED_AT_REGISTRATION,
            *OPTIONAL_AT_REGISTRATION,
            SPECIAL_MEDICAL,
        ]:
            active = self.store.active_legal(consent_id)
            latest = self.store.latest_action(user.id, consent_id)
            items.append(
                {
                    "consent_id": consent_id,
                    "active_version": active.consent_version if active else None,
                    "active_hash": active.content_hash if active else None,
                    "legal_document_id": str(active.id) if active else None,
                    "status": (
                        "accepted_current"
                        if latest
                        and latest.action == ConsentAction.ACCEPT
                        and active
                        and latest.content_hash == active.content_hash
                        else "accepted_outdated"
                        if latest and latest.action == ConsentAction.ACCEPT
                        else "withdrawn"
                        if latest and latest.action == ConsentAction.WITHDRAW
                        else "missing"
                    ),
                    "last_action_at": latest.occurred_at.isoformat() if latest else None,
                    "last_event_id": str(latest.id) if latest else None,
                },
            )
        return {
            "user_id": str(user.id),
            "email": user.email,
            "display_name": user.display_name or "",
            "has_avatar": bool(user.avatar_jpeg),
            "email_verified": user.email_verified_at is not None,
            "consents": items,
            "deletion_requested_at": self.store.deletion_requests.get(user.id),
            "export_requested_at": self.store.export_requests.get(user.id),
        }

    def update_profile(
        self,
        user: UserRecord,
        *,
        display_name: str | None = None,
        avatar_jpeg: bytes | None = None,
        clear_avatar: bool = False,
    ) -> UserRecord:
        from app.services.auth_profile import normalize_display_name

        if display_name is not None:
            name = normalize_display_name(display_name)
            taken = self.store.users_by_name.get(name.casefold())
            if taken and taken != user.id:
                raise AuthConsentError("username_taken", "Это имя пользователя уже занято", http_status=400)
            self.store.drop_name_index(user)
            user.display_name = name
            self.store.index_user(user)
        if clear_avatar:
            user.avatar_jpeg = None
        elif avatar_jpeg is not None:
            user.avatar_jpeg = avatar_jpeg
        self.store.users[user.id] = user
        return user

    def request_export(self, user: UserRecord) -> None:
        self.store.export_requests[user.id] = utcnow()

    def request_deletion(self, user: UserRecord) -> None:
        # Allowed even without re-accept of new offer
        self.store.deletion_requests[user.id] = utcnow()
        user.status = "deletion_requested"
        self.revoke_all_sessions(user.id)

    def medical_withdraw_consequences(self) -> dict[str, str]:
        return {
            "summary": "Отзыв специального согласия останавливает новые загрузки/анализ потенциально медицинских документов.",
            "erasure": "Связанные medical-derived артефакты ставятся в erasure workflow (RETENTION_*_NEEDS_REVIEW).",
            "account": "Аккаунт и обычные документы сохраняются, пока вы не запросите удаление аккаунта.",
        }
