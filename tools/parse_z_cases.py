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

res = call_tool('get_class_source', {'class_name': 'androidx.lifecycle.z'})
txt = res['result']['content'][0]['text']

with open('z_source.java', 'w', encoding='utf-8') as f:
    f.write(txt)

import re
cases = re.findall(r'case (\d+):.*?(?=case \d+:|default:|$)', txt, re.DOTALL)
print(f"Total cases: {len(cases)}")
for num, c in re.findall(r'case (\d+):(.*?)(?=case \d+:|default:|$)', txt, re.DOTALL):
    endpoints = re.findall(r'\.c\("([^"]+)"\)', c)
    models = re.findall(r'kotlin\.jvm\.internal\.x\.c\(([^)]+)\)', c)
    types = re.findall(r'com\.playfy\.tv\.models\.\w+', c)
    if endpoints or models or types:
        print(f"Case {num}: Endpoints={endpoints}, Models={models}, Types={types}")
