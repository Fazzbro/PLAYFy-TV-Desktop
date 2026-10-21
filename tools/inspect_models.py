import os
import re

dir_path = r'decompiled_sources/app_core'
kd_files = [f for f in os.listdir(dir_path) if f.startswith('kd.') and f.endswith('.java')]

print(f"Inspecting {len(kd_files)} files in kd package...")

for fn in sorted(kd_files):
    fp = os.path.join(dir_path, fn)
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract class declaration and fields
    cls_match = re.search(r'public final class (\w+)(?: implements|\{)', content)
    cls_name = cls_match.group(1) if cls_match else fn
    
    # Check if data class / model (has fields with types)
    fields = re.findall(r'public final ([\w\<\>\[\], ]+) (\w+);', content)
    if fields:
        print(f"\nModel: {fn} (class {cls_name}):")
        for ftype, fname in fields:
            print(f"    {fname}: {ftype}")
