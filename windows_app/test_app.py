import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crypto import derive_key_iv, decrypt_payload
from database import Database
from m3u_parser import M3UParser
from api_client import ApiClient

print("1. Testing Crypto Module...")
k, iv = derive_key_iv("DEFAULT1234567890", "zH7hY9@lO=8uXk#f%mI/VvJd2G10Z5eU+L6Pi&aEbwA4scBCStQ3KyWqRjDgnoMRP")
assert len(k) == 16 and len(iv) == 16, f"Invalid key/iv lengths: {len(k)}, {len(iv)}"
print(f"   Key: {k.hex()}, IV: {iv.hex()} -> OK")

print("2. Testing Database Module...")
db = Database(":memory:")
db.add_favorite(101, "Sky Sports Premier League", "https://img.icons8.com/color/96/sport.png", [{"title": "1080p", "link": "https://example.com/live.m3u8"}])
favs = db.get_favorites()
assert len(favs) == 1
assert db.is_favorite(101)
db.remove_favorite(101)
assert not db.is_favorite(101)

pl_id = db.add_playlist("Test Sports M3U", "https://example.com/playlist.m3u")
pls = db.get_playlists()
assert len(pls) == 1
assert pls[0]["title"] == "Test Sports M3U"
db.delete_playlist(pl_id)
assert len(db.get_playlists()) == 0
print("   Database operations -> OK")

print("3. Testing M3U Parser Module...")
m3u_sample = """#EXTM3U
#EXTINF:-1 tvg-name="Sky Sports Main Event" tvg-logo="https://logo.png" group-title="UK Sports",Sky Sports Main Event HD
#EXTVLCOPT:http-user-agent=PLAYFy/1.7
#EXTVLCOPT:http-referrer=https://playfy.tv
https://stream.example.com/live/skymain.m3u8
#EXTINF:-1 tvg-name="TNT Sports 1" group-title="UK Sports",TNT Sports 1 HD
https://stream.example.com/live/tnt1.m3u8
"""
items = M3UParser.parse_content(m3u_sample)
assert len(items) == 2
assert items[0]["name"] == "Sky Sports Main Event HD"
assert items[0]["groupTitle"] == "UK Sports"
assert items[0]["userAgent"] == "PLAYFy/1.7"
assert items[0]["referrer"] == "https://playfy.tv"
assert items[1]["name"] == "TNT Sports 1 HD"
print(f"   Parsed {len(items)} channels from sample M3U -> OK")

print("4. Testing API Client Module...")
client = ApiClient()
events = client.get_live_events()
assert "channels" in events and len(events["channels"]) > 0
cats = client.get_categories()
assert len(cats) > 0
highlights = client.get_highlights()
assert "channels" in highlights
print(f"   Events: {len(events['channels'])}, Categories: {len(cats)}, Highlights: {len(highlights['channels'])} -> OK")

print("5. Testing Qt 6 GUI Components & Layout...")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)
from ui.main_window import MainWindow

win = MainWindow()
assert win.stack.count() == 7
print(f"   MainWindow created successfully with {win.stack.count()} views.")
print("   All 5 verification suites PASSED successfully!")
