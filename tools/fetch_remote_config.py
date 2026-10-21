import urllib.request, json

api_key = "AIzaSyDdHIwVAD3XgP5bEwZOcR1QIz7gO5q5EoM"
project_id = "playfy-tv"
app_id = "1:239487160038:android:308875071ce6f0fd48f527"

# 1. Register installation to get auth token
install_url = f"https://firebaseinstallations.googleapis.com/v1/projects/{project_id}/installations"
install_body = json.dumps({
    "appId": app_id,
    "authVersion": "FIS_v2",
    "sdkVersion": "a:18.0.0"
}).encode('utf-8')

install_req = urllib.request.Request(
    install_url,
    data=install_body,
    headers={
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key
    }
)

try:
    with urllib.request.urlopen(install_req) as resp:
        install_res = json.loads(resp.read().decode('utf-8'))
        print("Installation success!")
        fid = install_res.get('fid')
        token = install_res.get('authToken', {}).get('token')
        print("FID:", fid)
        print("Auth Token:", token[:20] + "...")
        
        # 2. Fetch Remote Config
        rc_url = f"https://firebaseremoteconfig.googleapis.com/v1/projects/{project_id}/namespaces/firebase:fetch"
        rc_body = json.dumps({
            "appId": app_id,
            "appInstanceId": fid,
            "appInstanceIdToken": token,
            "packageName": "com.playfy.tv",
            "languageCode": "en-US",
            "sdkVersion": "21.6.0"
        }).encode('utf-8')
        
        rc_req = urllib.request.Request(
            rc_url,
            data=rc_body,
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': api_key,
                'x-goog-firebase-installations-auth': token
            }
        )
        
        with urllib.request.urlopen(rc_req) as rc_resp:
            rc_data = json.loads(rc_resp.read().decode('utf-8'))
            print("\n=== Remote Config Fetched Successfully! ===")
            entries = rc_data.get('entries', {})
            for k, v in entries.items():
                print(f"  {k} = {v}")
            with open('remote_config.json', 'w', encoding='utf-8') as out:
                json.dump(entries, out, indent=2)

except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print("Details:", e.read().decode('utf-8'))
