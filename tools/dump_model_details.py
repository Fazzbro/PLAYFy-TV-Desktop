import os

dir_path = r'decompiled_sources/app_core'
models = ['kd.f.java', 'kd.x.java', 'kd.l.java', 'kd.u.java', 'kd.a0.java', 'kd.h0.java', 'kd.j0.java', 'kd.p0.java', 'kd.i.java', 'kd.c.java', 'kd.m0.java', 'kd.o.java', 'kd.r.java']

for m in models:
    fp = os.path.join(dir_path, m)
    if not os.path.exists(fp):
        continue
    with open(fp, 'r', encoding='utf-8') as f:
        src = f.read()
    print(f"==================== {m} ====================")
    # Print constructor and toString methods
    lines = src.split('\n')
    for l in lines:
        if 'public ' in l and '(' in l and ')' in l:
            print(' ', l.strip())
        elif 'toString()' in l:
            idx = lines.index(l)
            print(' ', '\n  '.join([line.strip() for line in lines[idx:idx+15]]))
            break
