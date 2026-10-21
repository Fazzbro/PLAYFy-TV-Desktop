import os, re

dir_path = r'decompiled_sources'
matches = []

for root, dirs, files in os.walk(dir_path):
    for f in files:
        if f.endswith('.java'):
            fp = os.path.join(root, f)
            with open(fp, 'r', encoding='utf-8', errors='ignore') as src:
                c = src.read()
                # Find all calls to .d("...") on Remote Config
                for m in re.finditer(r'\.d\("([^"]+)"\)', c):
                    matches.append((m.group(1), os.path.basename(fp)))

print("=== Firebase Remote Config Keys Found ===")
for k, src in sorted(set(matches)):
    print(f"  Key: {k} (in {src})")
