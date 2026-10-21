import os
import re

dir_path = r'decompiled_sources/app_core'

serializers = ['kd.d.java', 'kd.w.java', 'kd.k.java', 'kd.t.java', 'kd.z.java', 'kd.o0.java', 'kd.h.java', 'kd.b.java', 'kd.f0.java']

for s in serializers:
    fp = os.path.join(dir_path, s)
    if not os.path.exists(fp):
        continue
    with open(fp, 'r', encoding='utf-8') as f:
        src = f.read()
    print(f"\n==================== Serializer: {s} ====================")
    # Find all string literals added to PluginGeneratedSerialDescriptor
    desc_strings = re.findall(r'addElement\("([^"]+)"', src)
    if not desc_strings:
        desc_strings = re.findall(r'"([^"\\]+)"', src)
    # Filter only relevant field names
    fields = [x for x in desc_strings if not x.startswith('kd.') and not x.startswith('com.') and len(x) < 30]
    print("JSON Fields:", fields)
