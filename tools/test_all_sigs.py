import base64
import json
from Crypto.Cipher import AES

def derive_key_iv(sig_str, lora_str):
    if isinstance(sig_str, str):
        sig = sig_str.encode('utf-8')
    else:
        sig = sig_str
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
        val = (sig_byte + r15d) ^ eax
        idx2 = (val & 0xFFFFFFFF) % len(lora)
        key.append(lora[idx2])
        cur_h1 = val & 0xFFFFFFFF
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
        val = (sig_byte + r13d) ^ ecx
        idx2 = (val & 0xFFFFFFFF) % len(lora)
        iv.append(lora[idx2])
        cur_h2 = val & 0xFFFFFFFF
        r13d = (r13d + 7) & 0xFFFFFFFF
        
    return bytes(key), bytes(iv)

lora = "zH7hY9@lO=8uXk#f%mI/VvJd2G10Z5eU+L6Pi&aEbwA4scBCStQ3KyWqRjDgnoMRP"

with open('live_app.json', 'r', encoding='utf-8') as f:
    data_b64 = json.load(f)['data']
raw_ct = base64.b64decode(data_b64)

# Candidate signatures
candidates = [
    "38cde288f060fa8f476ab6811ff215767c35117bf6248fd8ad157cd4566898cc",
    "38CDE288F060FA8F476AB6811FF215767C35117BF6248FD8AD157CD4566898CC",
    "31cd6939d1beae32d1b0ef2d9460b170116a1885",
    "31CD6939D1BEAE32D1B0EF2D9460B170116A1885",
    "DEFAULT1234567890",
    "com.playfy.tv",
    "playfy-tv",
    "playfy",
    "vorasp.online",
    "https://vorasp.online/"
]

for cand in candidates:
    k, iv = derive_key_iv(cand, lora)
    cipher = AES.new(k, AES.MODE_CBC, iv)
    pt = cipher.decrypt(raw_ct)
    if b'{"' in pt or b'sig' in pt or b'updateUrl' in pt or b'channels' in pt:
        print(f"!!! SUCCESS with signature: {cand} !!!")
        print("Decrypted plaintext:\n", pt[:500].decode('utf-8', errors='replace'))
        break
else:
    print("No candidate matched yet, will test byte candidates.")
