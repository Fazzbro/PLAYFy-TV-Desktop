import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from windows_app.crypto import decrypt_payload

with open('live_cats_live-events.json', 'r') as f:
    ct = json.load(f)['data']

with open('remote_config.json', 'r') as f:
    lora = json.load(f)['lora']

sig = 'Mc1pOdG+rjLRsO8tlGCxcBFqGIU'
dec = decrypt_payload(ct, sig, lora)
data = json.loads(dec)

with open('decrypted_cats_live-events.json', 'wb') as f:
    f.write(dec)

print("Decrypted live-events saved!")
football = [ch for ch in data['channels'] if ch.get('category') == 'Football']
print(f"Total football events: {len(football)}")
for i, fb in enumerate(football):
    ev = fb.get('eventInfo', {})
    print(f"{i+1}. {fb.get('title')} [{ev.get('eventName')}]: {ev.get('teamA')} vs {ev.get('teamB')} (Start: {ev.get('startTime')}, Pinned: {ev.get('isPinned')})")
    print(f"   Formats: {fb.get('formats')}")
