import zipfile, hashlib

with zipfile.ZipFile(r'D:\PLAYFy-TV-V1.7.apk', 'r') as z:
    for name in z.namelist():
        if 'META-INF' in name and (name.endswith('.RSA') or name.endswith('.DSA') or name.endswith('.EC')):
            print("Found cert file:", name)
            cert_data = z.read(name)
            # The X.509 cert in PKCS7:
            # Let's compute SHA256 of cert_data or parse ASN.1
            print("Raw cert file size:", len(cert_data))

# Or check Android APK signing block (v2/v3)
with open(r'D:\PLAYFy-TV-V1.7.apk', 'rb') as f:
    apk_bytes = f.read()

# Let's search for ASN.1 sequence in META-INF
for name in z.namelist():
    if name.startswith('META-INF/') and name.endswith('.RSA'):
        data = z.read(name)
        # In PKCS#7 format, the X.509 certificate starts with 0x30 0x82 ...
        idx = 0
        while True:
            idx = data.find(b'\x30\x82', idx)
            if idx == -1: break
            length = (data[idx+2] << 8) | data[idx+3]
            candidate = data[idx:idx+4+length]
            sha256 = hashlib.sha256(candidate).hexdigest()
            print(f"Candidate cert at {idx}, len {len(candidate)}: SHA256 = {sha256}")
            idx += 1
