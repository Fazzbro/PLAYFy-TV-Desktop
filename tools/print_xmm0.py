with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    data = f.read()

off = 0x657b7 - 0x52987
print("Bytes at 0x%x:" % off, data[off:off+32])
print("Hex:", data[off:off+32].hex())
print("ASCII/utf-8:", data[off:off+32])
