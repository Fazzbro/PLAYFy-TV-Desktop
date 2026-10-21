import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

session_id = None
def call_tool(name, args={}):
    global session_id
    if session_id is None:
        init_req = urllib.request.Request('http://127.0.0.1:8765/mcp', data=json.dumps({
            'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
            'params': {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name':'c','version':'1'}}
        }).encode('utf-8'), headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(init_req) as resp:
            session_id = resp.headers['mcp-session-id']
    
    req = urllib.request.Request('http://127.0.0.1:8765/mcp', data=json.dumps({
        'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
        'params': {'name': name, 'arguments': args}
    }).encode('utf-8'), headers={'Content-Type':'application/json', 'mcp-session-id': session_id})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

for query in ['app_', 'blocked', 'stream', 'event', 'channel', 'sponsor', 'donate', 'playlist', 'update', 'setting']:
    res = call_tool('get_strings', {'query': query})
    items = json.loads(res['result']['content'][0]['text']).get('items', [])
    print(f'=== Query: {query} ({len(items)} items) ===')
    for it in items[:15]:
        print(f"  {it['name']} = {it['value']}")
