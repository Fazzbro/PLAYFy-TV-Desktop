import zipfile, hashlib
from cryptography import x509

with zipfile.ZipFile(r'D:\PLAYFy-TV-V1.7.apk', 'r') as z:
    for name in z.namelist():
        if 'META-INF' in name and (name.endswith('.RSA') or name.endswith('.DSA') or name.endswith('.EC')):
            print("Found cert file:", name)
            cert_data = z.read(name)
            # Find the certificate inside PKCS7
            # Typically 0x30 0x82 ...
            idx = 0
            candidates = []
            while True:
                idx = cert_data.find(b'\x30\x82', idx)
                if idx == -1: break
                length = (cert_data[idx+2] << 8) | cert_data[idx+3]
                candidate = cert_data[idx:idx+4+length]
                sha256 = hashlib.sha256(candidate).hexdigest()
                sha1 = hashlib.sha1(candidate).hexdigest()
                candidates.append((candidate, sha256, sha1))
                idx += 1
            print(f"Found {len(candidates)} cert candidates")
            for c, s256, s1 in candidates:
                print(f"  len={len(c)}, sha256={s256}, sha1={s1}")
                with open('apk_cert.der', 'wb') as out:
                    out.write(c)
