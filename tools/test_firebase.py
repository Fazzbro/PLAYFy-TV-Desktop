import urllib.request, json

headers = {'User-Agent': 'Mozilla/5.0'}
urls = [
    'https://firebasestorage.googleapis.com/v0/b/playfy-tv.firebasestorage.app/o/app.json?alt=media',
    'https://firebasestorage.googleapis.com/v0/b/playfy-tv.firebasestorage.app/o/cc.json?alt=media',
    'https://firebasestorage.googleapis.com/v0/b/playfy-tv.firebasestorage.app/o/cats%2Flive-events.json?alt=media',
    'https://firebasestorage.googleapis.com/v0/b/playfy-tv.firebasestorage.app/o/cats%2Fhighlights.json?alt=media'
]

for u in urls:
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode('utf-8', errors='replace')
            name = u.split('/o/')[1].split('?')[0]
            print(f'SUCCESS {name}: status {resp.status}, size {len(data)}')
            print('  Preview:', data[:200].replace('\n', ' '))
            with open(f"live_{name.replace('%2F', '_')}", 'w', encoding='utf-8') as out:
                out.write(data)
    except Exception as e:
        print(f'FAIL {u}: {e}')
