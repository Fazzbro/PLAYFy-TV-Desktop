import base64, json

with open('live_app.json', 'r', encoding='utf-8') as f:
    j = json.load(f)

b64_str = j['data']
raw = base64.b64decode(b64_str)
print(f"Decoded data length: {len(raw)} bytes")
print("First 32 bytes hex:", raw[:32].hex())
print("Length % 16:", len(raw) % 16)

# Test AES-CBC with various candidate keys from lora
# lora = "zH7hY9@lO=8uXk#f%mI/VvJd2G10Z5eU+L6Pi&aEbwA4scBCStQ3KyWqRjDgnoMRP"
lora = "zH7hY9@lO=8uXk#f%mI/VvJd2G10Z5eU+L6Pi&aEbwA4scBCStQ3KyWqRjDgnoMRP"
print("Lora length:", len(lora))
