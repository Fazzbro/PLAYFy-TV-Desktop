with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    data = f.read()

offsets = [
    0x693a5 - 0x574e0,
    0x693ac - 0x575ca,
    0x693c6 - 0x5735e,
    0x693cd - 0x586a2,
    0x69426 - 0x58315
]

for off in offsets:
    end = data.find(b'\x00', off)
    s = data[off:end]
    print(f"Offset 0x{off:x}: {s}")
