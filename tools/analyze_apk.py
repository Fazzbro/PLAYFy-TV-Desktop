import os
import re

dir_path = r'decompiled_sources/app_core'
files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith('.java')]

print(f'Scanning {len(files)} files for URLs, endpoints, Retrofit/Net calls, and Room entities...')

url_regex = re.compile(r'https?://[^\s"\'<>]+')
api_path_regex = re.compile(r'"(/[^"]+)"')

urls = set()
api_paths = set()
entities = []

for fp in files:
    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        for u in url_regex.findall(content):
            urls.add((u, os.path.basename(fp)))
        for p in api_path_regex.findall(content):
            if any(k in p for k in ['api', 'v1', 'v2', 'event', 'channel', 'stream', 'playlist', 'cat', 'match', 'app', 'setting', 'donate', 'user', 'banner', 'highlight']):
                api_paths.add((p, os.path.basename(fp)))
        if '@Entity' in content or 'RoomDatabase' in content or 'Dao' in content or 'CREATE TABLE' in content or 'MyDB' in content:
            entities.append(os.path.basename(fp))

print('=== URLs Found ===')
for u, f in sorted(urls):
    print(f'  {u}  (in {f})')

print('=== API Paths Found ===')
for p, f in sorted(api_paths):
    print(f'  {p}  (in {f})')

print('=== DB / Room files ===')
for e in sorted(entities):
    print(f'  {e}')
