with open(r'apk_extracted\lib\x86_64\libumairi-lib.so', 'rb') as f:
    data = f.read()

# Let's search near 0x111bc and 0x1143d in data for other method names
chunk = data[0x11000:0x12500]
import re
for m in re.findall(b'[\x20-\x7e]{3,}', chunk):
    print(m.decode('latin-1'))
