from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class Envelope:
    dek_id: str
    wrapped_dek: bytes
    ciphertext: bytes  # nonce(12) || ciphertext+tag


def _aes_key_from_dek(dek: bytes) -> bytes:
    return hashlib.sha256(dek).digest()


def encrypt_envelope(*, plaintext: bytes, dek: bytes, dek_id: str, wrapped_dek: bytes) -> Envelope:
    key = _aes_key_from_dek(dek)
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, plaintext, associated_data=dek_id.encode())
    return Envelope(dek_id=dek_id, wrapped_dek=wrapped_dek, ciphertext=nonce + ct)


def decrypt_envelope(*, envelope: Envelope, dek: bytes) -> bytes:
    key = _aes_key_from_dek(dek)
    nonce, ct = envelope.ciphertext[:12], envelope.ciphertext[12:]
    return AESGCM(key).decrypt(nonce, ct, associated_data=envelope.dek_id.encode())
