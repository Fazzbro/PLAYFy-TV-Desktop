import base64
import json

def derive_key_iv(sig_str, lora_str):
    sig = sig_str.encode('utf-8')
    lora = lora_str.encode('utf-8')
    
    # 1. Derive KEY
    # FNV-1a with basis 0x811c9dc5
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
        eax = ((cur_h1 << 5) - cur_h1) & 0xFFFFFFFF # cur_h1 * 31
        # in x86: movsx ebx, byte ptr [rdi + rdx]; add ebx, r15d; xor ebx, eax
        # Note: in C signed int:
        sig_byte = sig[idx1]
        if sig_byte > 127: sig_byte -= 256
        val = (sig_byte + r15d) ^ eax
        # cmp rbx, rsi; div esi -> unsigned division by len(lora)
        idx2 = (val & 0xFFFFFFFF) % len(lora)
        key.append(lora[idx2])
        cur_h1 = val & 0xFFFFFFFF # ebx is updated
        r15d = (r15d + 13) & 0xFFFFFFFF

    # 2. Derive IV
    # FNV-1a with basis 0x811c832a
    h2 = 0x811c832a
    for b in sig:
        h2 = ((h2 ^ b) * fnv_prime) & 0xFFFFFFFF
    
    iv = bytearray()
    r13d = 0
    cur_h2 = h2
    for step in range(0, 48, 3): # 16 iterations
        idx1 = step % len(sig)
        # lea eax, [rbx + rbx*8] (9*rbx); lea eax, [rax + rax*2] (27*rbx); add ebx, ebx (2*rbx); add ecx, eax (29*rbx)
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

for cand_sig in ["DEFAULT1234567890", "com.playfy.tv"]:
    k, iv = derive_key_iv(cand_sig, lora)
    print(f"Sig: {cand_sig}")
    print(f"  Key: {k.decode('latin-1')} (hex: {k.hex()})")
    print(f"  IV:  {iv.decode('latin-1')} (hex: {iv.hex()})")

    # Try AES decrypt
    from Crypto.Cipher import AES
    with open('live_app.json', 'r', encoding='utf-8') as f:
        data_b64 = json.load(f)['data']
    raw_ct = base64.b64decode(data_b64)
    cipher = AES.new(k, AES.MODE_CBC, iv)
    pt = cipher.decrypt(raw_ct)
    print("  Decrypted preview:", pt[:100])
