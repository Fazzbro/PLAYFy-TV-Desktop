import base64
import hashlib
import json
from Crypto.Cipher import AES
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.hazmat.primitives import hashes, serialization

with open('live_app.json', 'r', encoding='utf-8') as f:
    data_b64 = json.load(f)['data']
raw_ct = base64.b64decode(data_b64)
first_block = raw_ct[:16]

with open('apk_extracted/META-INF/CERT.RSA', 'rb') as f:
    rsa_bytes = f.read()

certs = pkcs7.load_der_pkcs7_certificates(rsa_bytes)
cert_der = certs[0].public_bytes(serialization.Encoding.DER)
sha1_b = hashlib.sha1(cert_der).digest()
sha256_b = hashlib.sha256(cert_der).digest()
md5_b = hashlib.md5(cert_der).digest()

sig_cands = set([
    'DEFAULT1234567890',
    'com.playfy.tv',
    'playfy-tv',
    'playfy',
    sha1_b.hex().lower(),
    sha1_b.hex().upper(),
    sha256_b.hex().lower(),
    sha256_b.hex().upper(),
    md5_b.hex().lower(),
    md5_b.hex().upper(),
    base64.b64encode(sha1_b).decode(),
    base64.b64encode(sha1_b).decode().strip('='),
    base64.b64encode(sha1_b).decode() + '\n',
    base64.b64encode(sha256_b).decode(),
    base64.b64encode(sha256_b).decode().strip('='),
    base64.b64encode(md5_b).decode(),
    base64.b64encode(md5_b).decode().strip('='),
])

# Add all strings from arsc
try:
    with open('arsc_strings.txt', 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip()
            if 8 <= len(s) <= 64:
                sig_cands.add(s)
except Exception:
    pass

lora_cands = [
    'zH7hY9@lO=8uXk#f%mI/VvJd2G10Z5eU+L6Pi&aEbwA4scBCStQ3KyWqRjDgnoMRP',
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/@#%&=',
    'DEFAULT1234567890',
    'playfy-tv',
    'com.playfy.tv'
]

def derive_key_iv(sig_str, lora_str):
    sig = sig_str.encode('utf-8')
    lora = lora_str.encode('utf-8')
    fnv_basis = 0x811c9dc5
    fnv_prime = 0x01000193
    h1 = fnv_basis
    for b in sig:
        h1 = ((h1 ^ b) * fnv_prime) & 0xFFFFFFFF
    key = bytearray()
    r15d = 0
    cur_h1 = h1
    for i in range(16):
        idx1 = i % len(sig)
        eax = ((cur_h1 << 5) - cur_h1) & 0xFFFFFFFF
        sig_byte = sig[idx1]
        if sig_byte > 127: sig_byte -= 256
        val = ((sig_byte + r15d) ^ eax) & 0xFFFFFFFF
        idx2 = val % len(lora)
        key.append(lora[idx2])
        cur_h1 = val
        r15d = (r15d + 13) & 0xFFFFFFFF

    h2 = 0x811c832a
    for b in sig:
        h2 = ((h2 ^ b) * fnv_prime) & 0xFFFFFFFF
    iv = bytearray()
    r13d = 0
    cur_h2 = h2
    for step in range(0, 48, 3):
        idx1 = step % len(sig)
        ecx = (29 * cur_h2) & 0xFFFFFFFF
        sig_byte = sig[idx1]
        if sig_byte > 127: sig_byte -= 256
        val = ((sig_byte + r13d) ^ ecx) & 0xFFFFFFFF
        idx2 = val % len(lora)
        iv.append(lora[idx2])
        cur_h2 = val
        r13d = (r13d + 7) & 0xFFFFFFFF
    return bytes(key), bytes(iv)

print(f"Testing {len(sig_cands)} sig candidates with {len(lora_cands)} lora candidates...")
found = False
for lora in lora_cands:
    for s in sig_cands:
        try:
            k, iv = derive_key_iv(s, lora)
            cipher = AES.new(k, AES.MODE_CBC, iv)
            pt16 = cipher.decrypt(first_block)
            if pt16.startswith(b'{"') or pt16.startswith(b'[{"'):
                print("FOUND TRUE MATCH!")
                print("sig:", repr(s))
                print("lora:", repr(lora))
                print("Key:", repr(k))
                print("IV:", repr(iv))
                full_pt = AES.new(k, AES.MODE_CBC, iv).decrypt(raw_ct)
                print("Decrypted preview:", full_pt[:200])
                found = True
                break
        except Exception:
            pass
    if found:
        break
if not found:
    print("No match found in current candidates.")
