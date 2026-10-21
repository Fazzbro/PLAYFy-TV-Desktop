with open(r'apk_extracted\lib\x86_64\libumairi-lib.so', 'rb') as f:
    data = f.read()

import re
for m in re.findall(b'Hmac[^\x00]+', data):
    print("Hmac:", m)
for m in re.findall(b'SHA[^\x00]+', data):
    print("SHA:", m)
