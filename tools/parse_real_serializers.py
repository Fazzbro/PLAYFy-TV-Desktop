import os
import re

dir_path = r'decompiled_sources/app_core'
serializers = ['kd.v.java', 'kd.j.java', 'kd.s.java', 'kd.y.java', 'kd.n0.java', 'kd.g.java', 'kd.a.java', 'kd.b.java', 'kd.e0.java']

for s in serializers:
    fp = os.path.join(dir_path, s)
    if not os.path.exists(fp):
        continue
    with open(fp, 'r', encoding='utf-8') as f:
        src = f.read()
    print(f"\n==================== Serializer: {s} ====================")
    desc_strings = re.findall(r'addElement\("([^"]+)"', src)
    if not desc_strings:
        desc_strings = re.findall(r'a\("([^"]+)"', src)
    if not desc_strings:
        desc_strings = re.findall(r'"([^"\\]+)"', src)
    fields = [x for x in desc_strings if not x.startswith('kd.') and not x.startswith('com.') and len(x) < 30]
    print("JSON Fields:", fields)
