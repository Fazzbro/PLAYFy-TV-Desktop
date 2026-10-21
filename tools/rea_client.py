import requests
import json
import sys

class ReaMcpClient:
    def __init__(self, base_url="http://127.0.0.1:8765/mcp"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session_id = None
        self._init_session()

    def _init_session(self):
        r1 = self.session.post(self.base_url, json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "rea-client", "version": "1.0"}
            }
        })
        self.session_id = r1.headers.get("mcp-session-id")
        if self.session_id:
            self.session.headers["mcp-session-id"] = self.session_id
        self.session.post(self.base_url, json={
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })

    def call_tool(self, tool_name, arguments={}):
        r = self.session.post(self.base_url, json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        })
        res = r.json()
        if "error" in res:
            raise Exception(f"Tool error: {res['error']}")
        content = res.get("result", {}).get("content", [])
        if content and content[0].get("type") == "text":
            return content[0].get("text")
        return json.dumps(content)

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    client = ReaMcpClient()
    if len(sys.argv) > 1:
        tool = sys.argv[1]
        args = {}
        for arg in sys.argv[2:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                args[k] = v
        print(client.call_tool(tool, args))
    else:
        print("Usage: rea_client.py <tool_name> [k=v ...]")
