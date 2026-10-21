with open('arsc_strings.txt', 'r', encoding='utf-8') as f:
    lines = [line.strip() for line in f if line.strip()]

matches = []
for l in lines:
    low = l.lower()
    if any(k in low for k in ['playfy', 'http://', 'https://', 'endpoint', 'api/', 'secret', 'token', 'telegram', 'stream', 'live', 'channel', 'sponsor', 'blocked_app', 'playlist', 'match', 'event', 'highlight', 'sports', 'football', 'cricket', 'server', 'quality', 'agent']):
        matches.append(l)

with open('arsc_filtered.txt', 'w', encoding='utf-8') as out:
    for m in matches:
        out.write(m + '\n')

print(f"Filtered {len(matches)} interesting strings into arsc_filtered.txt")
