import os, struct

def parse_elf(path):
    print(f"\n==================== ELF: {path} ====================")
    with open(path, 'rb') as f:
        data = f.read()
    
    if data[:4] != b'\x7fELF':
        print("Not an ELF file")
        return
    
    is_64 = data[4] == 2
    endian = '<' if data[5] == 1 else '>'
    print(f"Class: {'64-bit' if is_64 else '32-bit'}, Endian: {endian}")
    
    # Extract readable strings
    import re
    strings = re.findall(b'[\x20-\x7e]{5,}', data)
    print(f"Found {len(strings)} strings. Interesting strings:")
    for s in strings:
        st = s.decode('latin-1')
        if any(k in st.lower() for k in ['ohmy', 'ninty', 'aes', 'des', 'rc4', 'key', 'iv', 'decrypt', 'encrypt', 'base64', 'java_', 'playfy']):
            print("  ", st)

for lib in ['libnative-lib.so', 'libumairi-lib.so']:
    p = os.path.join(r'apk_extracted\lib\x86_64', lib)
    if os.path.exists(p):
        parse_elf(p)
