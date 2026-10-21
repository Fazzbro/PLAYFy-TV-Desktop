with open(r'apk_extracted\lib\x86_64\libumairi-lib.so', 'rb') as f:
    data = f.read()

import re
matches = re.findall(b'AES[^\x00]+', data)
for m in matches:
    print("umairi AES match:", m)

matches2 = re.findall(b'javax/crypto/[^\x00]+', data)
for m in matches2:
    print("umairi crypto match:", m)

with open(r'apk_extracted\lib\x86_64\libnative-lib.so', 'rb') as f:
    data2 = f.read()

for m in re.findall(b'AES[^\x00]+', data2):
    print("native-lib AES match:", m)

for m in re.findall(b'javax/crypto/[^\x00]+', data2):
    print("native-lib crypto match:", m)
