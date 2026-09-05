"""Display name, password strength, and avatar re-encode for registration/profile."""

from __future__ import annotations

import base64
import io
import re

from app.services.auth_consent import AuthConsentError

DISPLAY_NAME_MIN = 2
DISPLAY_NAME_MAX = 80
MAX_AVATAR_INPUT_BYTES = 400_000
AVATAR_SIDE = 128

_NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё'\- ]*$")
_URLISH = re.compile(r"https?://|www\.|@", re.IGNORECASE)
_LETTER = re.compile(r"[A-Za-zА-Яа-яЁё]")
_DIGIT = re.compile(r"\d")
_COMMON = frozenset(
    {
        "password123",
        "password12",
        "1234567890",
        "qwerty12345",
        "qwerty1234",
        "docly12345",
        "admin12345",
    },
)


def normalize_display_name(raw: str) -> str:
    name = " ".join((raw or "").split())
    if len(name) < DISPLAY_NAME_MIN or len(name) > DISPLAY_NAME_MAX:
        raise AuthConsentError(
            "invalid_display_name",
            "Укажите имя от 2 до 80 символов",
            http_status=400,
        )
    if _URLISH.search(name) or not _NAME_RE.fullmatch(name):
        raise AuthConsentError(
            "invalid_display_name",
            "Имя может содержать буквы, пробел, дефис и апостроф",
            http_status=400,
        )
    return name


def assert_password_strength(password: str, email: str) -> None:
    if len(password) < 10 or len(password) > 128:
        raise AuthConsentError("weak_password", "Пароль не короче 10 символов")
    if not _LETTER.search(password) or not _DIGIT.search(password):
        raise AuthConsentError("weak_password", "В пароле нужны и буква, и цифра")
    if password.lower() in _COMMON:
        raise AuthConsentError("weak_password", "Этот пароль слишком распространён")
    local = (email or "").split("@", 1)[0].strip().lower()
    if len(local) >= 4 and local in password.lower():
        raise AuthConsentError("weak_password", "Пароль не должен содержать адрес почты")


def decode_avatar_jpeg(data_url: str | None) -> bytes | None:
    if not data_url:
        return None
    payload = data_url.strip()
    if payload.startswith("data:"):
        header, _, b64 = payload.partition(",")
        if "base64" not in header.lower() or not b64:
            raise AuthConsentError("invalid_avatar", "Не удалось прочитать изображение")
        mime = header[5:].split(";", 1)[0].strip().lower()
        if mime not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
            raise AuthConsentError("invalid_avatar", "Допустимы JPEG, PNG или WebP")
    else:
        b64 = payload
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception as exc:
        raise AuthConsentError("invalid_avatar", "Не удалось прочитать изображение") from exc
    if not raw or len(raw) > MAX_AVATAR_INPUT_BYTES:
        raise AuthConsentError("invalid_avatar", "Изображение слишком большое")
    try:
        from PIL import Image
    except ImportError as exc:
        raise AuthConsentError("invalid_avatar", "Обработка изображения недоступна") from exc
    try:
        image = Image.open(io.BytesIO(raw))
        image = image.convert("RGB")
        image.thumbnail((AVATAR_SIDE, AVATAR_SIDE))
        canvas = Image.new("RGB", (AVATAR_SIDE, AVATAR_SIDE), (255, 255, 255))
        x = (AVATAR_SIDE - image.width) // 2
        y = (AVATAR_SIDE - image.height) // 2
        canvas.paste(image, (x, y))
        out = io.BytesIO()
        canvas.save(out, format="JPEG", quality=85, optimize=True)
        data = out.getvalue()
    except AuthConsentError:
        raise
    except Exception as exc:
        raise AuthConsentError("invalid_avatar", "Не удалось обработать изображение") from exc
    if not data or len(data) > 80_000:
        raise AuthConsentError("invalid_avatar", "Не удалось сохранить изображение")
    return data
