import struct

with open(r'apk_extracted/resources.arsc', 'rb') as f:
    data = f.read()

# Chunk header: type (uint16), header_size (uint16), size (uint32)
chunk_type, header_size, chunk_size = struct.unpack_from('<HHI', data, 0)
print(f"Root chunk: type=0x{chunk_type:04x}, header_size={header_size}, size={chunk_size}")

# Followed by global string pool:
sp_type, sp_header_size, sp_size = struct.unpack_from('<HHI', data, header_size)
print(f"StringPool: type=0x{sp_type:04x}, header_size={sp_header_size}, size={sp_size}")

string_count, style_count, flags, strings_start, styles_start = struct.unpack_from('<IIIII', data, header_size + 8)
print(f"String count: {string_count}, flags: 0x{flags:x}, strings_start: {strings_start}")

is_utf8 = bool(flags & (1 << 8))
print("Is UTF-8:", is_utf8)

sp_base = header_size
string_offsets = [struct.unpack_from('<I', data, sp_base + 28 + i * 4)[0] for i in range(string_count)]

strings = []
for off in string_offsets:
    pos = sp_base + strings_start + off
    if is_utf8:
        # utf8 string pool: first u8 or u16 is u16 length, next is u8 length
        u16_len = data[pos]
        pos += 1
        if u16_len & 0x80:
            u16_len = ((u16_len & 0x7f) << 8) | data[pos]
            pos += 1
        u8_len = data[pos]
        pos += 1
        if u8_len & 0x80:
            u8_len = ((u8_len & 0x7f) << 8) | data[pos]
            pos += 1
        s = data[pos:pos + u8_len].decode('utf-8', errors='replace')
    else:
        u16_len = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        if u16_len & 0x8000:
            u16_len = ((u16_len & 0x7fff) << 16) | struct.unpack_from('<H', data, pos)[0]
            pos += 2
        s = data[pos:pos + u16_len * 2].decode('utf-16le', errors='replace')
    strings.append(s)

print(f"Extracted {len(strings)} strings from ARSC string pool.")

# Filter for interesting strings
with open('arsc_strings.txt', 'w', encoding='utf-8') as out:
    for s in strings:
        out.write(s + '\n')

print("Wrote arsc_strings.txt!")
