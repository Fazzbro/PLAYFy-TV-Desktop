import urllib.request, json

base_url = "https://vorasp.online/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json'
}

endpoints = [
    'app.json',
    'cc.json',
    'cats/live-events.json',
    'cats/highlights.json'
]

for ep in endpoints:
    url = base_url + ep
    print(f"\nFetching {url}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode('utf-8', errors='replace')
            print(f"SUCCESS: Status {resp.status}, Size: {len(data)} bytes")
            print("Preview:", data[:300].replace('\n', ' '))
            with open(f"live_{ep.replace('/', '_')}", 'w', encoding='utf-8') as f:
                f.write(data)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        if hasattr(e, 'read'):
            print("Response:", e.read().decode('utf-8', errors='replace')[:200])
