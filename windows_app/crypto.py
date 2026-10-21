"""
PLAYFy TV Clean-Room Cryptographic Engine
Implements the exact dual FNV-1a key/IV derivation and AES-128-CBC decryption
as reverse-engineered from libnative-lib.so (0x6b4c0, 0x69340).
"""

import base64
from typing import Tuple, Optional
from Crypto.Cipher import AES

# Remote Config defaults derived from APK analysis
DEFAULT_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/@#%&="
DEFAULT_LORA = "zH7hY9@lO=8uXk#f%mI/VvJd2G10Z5eU+L6Pi&aEbwA4scBCStQ3KyWqRjDgnoMRP"
APK_CERT_SIG = "Mc1pOdG+rjLRsO8tlGCxcBFqGIU"
DEFAULT_FALLBACK_SIG = "DEFAULT1234567890"
DEFAULT_SIG = APK_CERT_SIG

def derive_key_iv(sig_str: str, lora_str: str = "") -> Tuple[bytes, bytes]:
    """
    Derives 16-byte Key and 16-byte IV using the dual FNV-1a KDF algorithm.
    """
    if not sig_str:
        sig_str = DEFAULT_SIG
    if not lora_str:
        lora_str = DEFAULT_LORA

    sig = sig_str.encode('utf-8')
    lora = lora_str.encode('utf-8')
    if len(lora) == 0:
        lora = DEFAULT_ALPHABET.encode('utf-8')

    fnv_prime = 0x01000193

    # 1. Key Derivation (FNV-1a with basis 0x811c9dc5)
    h1 = 0x811c9dc5
    for b in sig:
        h1 = ((h1 ^ b) * fnv_prime) & 0xFFFFFFFF

    key = bytearray()
    r15d = 0
    cur_h1 = h1
    for i in range(16):
        idx1 = i % len(sig)
        eax = ((cur_h1 << 5) - cur_h1) & 0xFFFFFFFF  # cur_h1 * 31
        sig_byte = sig[idx1]
        if sig_byte > 127:
            sig_byte -= 256
        val = ((sig_byte + r15d) ^ eax) & 0xFFFFFFFF
        idx2 = val % len(lora)
        key.append(lora[idx2])
        cur_h1 = val
        r15d = (r15d + 13) & 0xFFFFFFFF

    # 2. IV Derivation (FNV-1a with secondary basis 0x811c832a)
    h2 = 0x811c832a
    for b in sig:
        h2 = ((h2 ^ b) * fnv_prime) & 0xFFFFFFFF

    iv = bytearray()
    r13d = 0
    cur_h2 = h2
    for step in range(0, 48, 3):  # 16 iterations
        idx1 = step % len(sig)
        ecx = (29 * cur_h2) & 0xFFFFFFFF
        sig_byte = sig[idx1]
        if sig_byte > 127:
            sig_byte -= 256
        val = ((sig_byte + r13d) ^ ecx) & 0xFFFFFFFF
        idx2 = val % len(lora)
        iv.append(lora[idx2])
        cur_h2 = val
        r13d = (r13d + 7) & 0xFFFFFFFF

    return bytes(key), bytes(iv)


def decrypt_payload(b64_ciphertext: str, sig_str: str = DEFAULT_SIG, lora_str: str = "") -> Optional[bytes]:
    """
    Decodes Base64 ciphertext, runs AES-128-CBC decryption, and removes PKCS7 padding.
    If decryption fails or padding is invalid with sig_str, falls back to DEFAULT_FALLBACK_SIG.
    """
    candidates = [sig_str]
    if DEFAULT_FALLBACK_SIG not in candidates:
        candidates.append(DEFAULT_FALLBACK_SIG)
    if APK_CERT_SIG not in candidates:
        candidates.append(APK_CERT_SIG)

    raw_ct = None
    try:
        raw_ct = base64.b64decode(b64_ciphertext)
        if len(raw_ct) % 16 != 0 or len(raw_ct) == 0:
            return None
    except Exception:
        return None

    lora_candidates = [lora_str] if lora_str else []
    for l in [DEFAULT_LORA, DEFAULT_ALPHABET]:
        if l not in lora_candidates:
            lora_candidates.append(l)

    for candidate_lora in lora_candidates:
        for candidate_sig in candidates:
            try:
                key, iv = derive_key_iv(candidate_sig, candidate_lora)
                cipher = AES.new(key, AES.MODE_CBC, iv)
                pt = cipher.decrypt(raw_ct)
                # Try standard PKCS7 unpad first
                pad_len = pt[-1]
                if 1 <= pad_len <= 16 and pt[-pad_len:] == bytes([pad_len] * pad_len):
                    return pt[:-pad_len]
                # If server padded with spaces or nulls, verify JSON bounds
                cleaned = pt.rstrip(b' \t\r\n\x00')
                if (cleaned.startswith(b'{') and cleaned.endswith(b'}')) or (cleaned.startswith(b'[') and cleaned.endswith(b']')):
                    return cleaned
            except Exception:
                continue
    return None
