"""
PLAYFy TV API Client Module
Handles Remote Config bootstrap, content CDN queries, payload decryption,
real live stream backlink extraction (channels/{id}.json), and M3U playlist parsing.
"""

import urllib.request
import json
import os
from typing import Dict, Any, List, Optional, Union
from crypto import decrypt_payload, DEFAULT_SIG, DEFAULT_ALPHABET
from m3u_parser import M3UParser

DEFAULT_BASE_URL = "https://vorasp.online/"
FIREBASE_API_KEY = "AIzaSyDdHIwVAD3XgP5bEwZOcR1QIz7gO5q5EoM"
FIREBASE_PROJECT_ID = "playfy-tv"
FIREBASE_APP_ID = "1:239487160038:android:308875071ce6f0fd48f527"

class ApiClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, lora: str = "", sig: str = DEFAULT_SIG):
        self.base_url = base_url if base_url.endswith('/') else base_url + '/'
        self.lora = lora or "zH7hY9@lO=8uXk#f%mI/VvJd2G10Z5eU+L6Pi&aEbwA4scBCStQ3KyWqRjDgnoMRP"
        self.sig = sig
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        self._streams_cache: Dict[str, List[Dict[str, Any]]] = {}

    def update_config(self, base_url: Optional[str] = None, lora: Optional[str] = None):
        if base_url:
            self.base_url = base_url if base_url.endswith('/') else base_url + '/'
        if lora:
            self.lora = lora

    def fetch_remote_config(self) -> Dict[str, str]:
        """
        Queries Firebase Remote Config directly.
        """
        try:
            # Step 1: Installations
            inst_url = f"https://firebaseinstallations.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/installations"
            inst_body = json.dumps({
                "appId": FIREBASE_APP_ID,
                "authVersion": "FIS_v2",
                "sdkVersion": "a:18.0.0"
            }).encode('utf-8')
            inst_req = urllib.request.Request(inst_url, data=inst_body, headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': FIREBASE_API_KEY
            })
            with urllib.request.urlopen(inst_req, timeout=8) as resp:
                inst_res = json.loads(resp.read().decode('utf-8'))
                fid = inst_res.get('fid')
                token = inst_res.get('authToken', {}).get('token')

            # Step 2: Fetch Remote Config
            rc_url = f"https://firebaseremoteconfig.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/namespaces/firebase:fetch"
            rc_body = json.dumps({
                "appId": FIREBASE_APP_ID,
                "appInstanceId": fid,
                "appInstanceIdToken": token,
                "packageName": "com.playfy.tv",
                "languageCode": "en-US",
                "sdkVersion": "21.6.0"
            }).encode('utf-8')
            rc_req = urllib.request.Request(rc_url, data=rc_body, headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': FIREBASE_API_KEY,
                'x-goog-firebase-installations-auth': token
            })
            with urllib.request.urlopen(rc_req, timeout=8) as resp:
                rc_data = json.loads(resp.read().decode('utf-8'))
                entries = rc_data.get('entries', {})
                if 'baseUrl' in entries:
                    self.update_config(base_url=entries['baseUrl'])
                if 'lora' in entries:
                    self.update_config(lora=entries['lora'])
                return entries
        except Exception:
            return {"baseUrl": self.base_url, "lora": self.lora}

    def _fetch_and_decrypt(self, endpoint: str) -> Optional[Any]:
        url = self.base_url + endpoint.lstrip('/')
        req = urllib.request.Request(url, headers={
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_text = resp.read().decode('utf-8', errors='replace')
                data_json = json.loads(raw_text)

                if isinstance(data_json, dict) and "data" in data_json:
                    # Encrypted wrapper
                    pt = decrypt_payload(data_json["data"], self.sig, self.lora)
                    if pt:
                        cleaned = pt.rstrip(b' \t\r\n\x00')
                        return json.loads(cleaned.decode('utf-8', errors='replace'))
                    return None
                else:
                    return data_json
        except Exception:
            return None

    def get_channel_stream_links(self, channel_id: Union[int, str]) -> List[Dict[str, Any]]:
        """
        Extracts real live stream backlinks from 'channels/{channel_id}.json'.
        Parses headers, clearKey DRM tokens, and stream URLs.
        Evidence: od.c0 (androidx.lifecycle.c lines 514-550) and PlayerActivity.f0.
        """
        cid_str = str(channel_id).strip()
        if not cid_str:
            return []

        if cid_str in self._streams_cache:
            return self._streams_cache[cid_str]

        endpoint = f"channels/{cid_str}.json"
        data = self._fetch_and_decrypt(endpoint)

        if not data or not isinstance(data, list):
            return []

        parsed_streams: List[Dict[str, Any]] = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                continue

            raw_title = item.get("title") or f"Server {idx+1}"
            raw_link = item.get("link", "")
            if not raw_link:
                continue

            # Parse custom HTTP headers if present after '|' (PlayerActivity.f0)
            clean_url = raw_link
            headers = {}
            if "|" in raw_link:
                parts = raw_link.split("|", 1)
                clean_url = parts[0]
                header_str = parts[1]
                for part in header_str.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        headers[k.strip()] = v.strip()

            is_hls = ".m3u8" in clean_url.lower()
            is_dash = ".mpd" in clean_url.lower() or str(item.get("type", "0")) == "1"

            parsed_streams.append({
                "id": f"{cid_str}_{idx}",
                "server_index": idx,
                "title": raw_title.strip(),
                "link": clean_url.strip(),
                "raw_link": raw_link.strip(),
                "headers": headers,
                "api": item.get("api", "").strip(),
                "type": str(item.get("type", "0")),
                "is_hls": is_hls,
                "is_dash": is_dash,
                "webLink": item.get("webLink", ""),
                "defaultLanguage": item.get("defaultLanguage", ""),
                "geo": item.get("geo", "ALL")
            })

        if parsed_streams:
            self._streams_cache[cid_str] = parsed_streams

        return parsed_streams

    def get_app_config(self) -> Dict[str, Any]:
        data = self._fetch_and_decrypt("app.json")
        if data and isinstance(data, dict):
            return data
        return {
            "sig": "playfy_v1",
            "dataRows": [],
            "ads": "",
            "updateUrl": None,
            "items": []
        }

    def get_categories(self) -> List[Dict[str, Any]]:
        data = self._fetch_and_decrypt("cc.json")
        if data and isinstance(data, list):
            return data
        # Fallback category catalog
        return [
            {"id": 1, "title": "Sports", "image": "https://img.icons8.com/color/96/football2--v1.png", "isChecked": True, "catLink": None},
            {"id": 2, "title": "News", "image": "https://img.icons8.com/color/96/news.png", "isChecked": False, "catLink": "https://cdn.playfytvapk.com/News.m3u"},
            {"id": 14, "title": "UK", "image": "https://img.icons8.com/color/96/great-britain.png", "isChecked": False, "catLink": "https://raw.githubusercontent.com/bugsfreeweb/LiveTVCollector/refs/heads/main/LiveTV/UK/LiveTV.m3u"},
            {"id": 16, "title": "SONYLIV", "image": "https://img.icons8.com/color/96/tv.png", "isChecked": False, "catLink": "https://raw.githubusercontent.com/doctor-8trange/zyphora/refs/heads/main/data/sony.m3u"}
        ]

    def get_live_events(self) -> Dict[str, Any]:
        """
        Fetches live sports events and football matchups from 'cats/live-events.json'.
        """
        data = self._fetch_and_decrypt("cats/live-events.json")
        if not data or not isinstance(data, dict) or "channels" not in data:
            # Fallback to local cached fixture
            try:
                import sys
                base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                fixture_path = os.path.join(base_dir, "decrypted_cats_live-events.json")
                if os.path.exists(fixture_path):
                    with open(fixture_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
            except Exception:
                data = None

        if not data or "channels" not in data:
            return {"cats": [], "channels": []}

        # Normalize channel formats
        for ch in data.get("channels", []):
            ch_id = ch.get("id")
            raw_fmts = ch.get("formats", [])
            # If already cached, attach real backlinks
            if str(ch_id) in self._streams_cache:
                ch["formats"] = self._streams_cache[str(ch_id)]
            else:
                norm_fmts = []
                for idx, fmt in enumerate(raw_fmts):
                    if isinstance(fmt, str):
                        norm_fmts.append({
                            "title": fmt.strip(),
                            "link": "",
                            "channel_id": ch_id,
                            "needs_resolution": True
                        })
                    elif isinstance(fmt, dict):
                        norm_fmts.append(fmt)
                ch["formats"] = norm_fmts

        return data

    def get_channels_by_category(self, category_title: str, cat_link: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetches live channels for a category.
        If cat_link is an M3U URL, downloads and parses it directly.
        If cat_link is None, queries 'cats/{slug}.json' (e.g. 'cats/sports.json' for 44 sports channels).
        """
        # Case 1: External M3U playlist URL
        if cat_link and isinstance(cat_link, str) and cat_link.startswith("http") and (".m3u" in cat_link.lower() or ".php" in cat_link.lower()):
            try:
                req = urllib.request.Request(cat_link, headers={'User-Agent': self.user_agent})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    content = resp.read().decode('utf-8', errors='ignore')
                    items = M3UParser.parse_content(content)
                    channels = []
                    for idx, it in enumerate(items):
                        channels.append({
                            "id": f"{category_title}_{idx+1}",
                            "title": it["name"],
                            "image": it.get("logo", ""),
                            "category": it.get("groupTitle", category_title),
                            "formats": [
                                {
                                    "title": "Live Broadcast",
                                    "link": it["link"],
                                    "raw_link": it["link"],
                                    "headers": {"User-Agent": it["userAgent"]} if it.get("userAgent") else {},
                                    "is_hls": ".m3u8" in it["link"].lower(),
                                    "is_dash": ".mpd" in it["link"].lower()
                                }
                            ]
                        })
                    if channels:
                        return channels
            except Exception as e:
                print(f"Error fetching M3U playlist {cat_link}: {e}")

        # Case 2: Server catalog JSON (cats/{slug}.json)
        slug = category_title.strip().lower().replace(" ", "-").replace("/", "-")
        endpoint = f"cats/{slug}.json"
        data = self._fetch_and_decrypt(endpoint)

        if not data or not isinstance(data, list):
            # Fallback for sports if network issue
            if slug == "sports":
                return [
                    {"id": 384, "title": "Sky Cricket HD", "image": "https://img.icons8.com/color/96/cricket.png", "formats": [{"title": "Sky Cricket HD", "link": "https://bl.rutube.ru/livestream/7c13a51576b9ff2601f08f5d57dd5169/index.m3u8?s=uiXES2ePt7xT"}]},
                    {"id": 346, "title": "TNT Sports HD", "image": "https://img.icons8.com/color/96/sport.png", "formats": [{"title": "TNT Sports 1", "link": ""}]},
                    {"id": 347, "title": "beiN Sports HD", "image": "https://img.icons8.com/color/96/trophy.png", "formats": [{"title": "beiN Sports 1", "link": ""}]}
                ]
            return []

        # Return real channels
        channels = []
        for ch in data:
            ch_id = ch.get("id")
            raw_fmts = ch.get("formats", [])
            cached = self._streams_cache.get(str(ch_id))
            if cached:
                ch["formats"] = cached
            else:
                norm_fmts = []
                for fmt in raw_fmts:
                    if isinstance(fmt, str):
                        norm_fmts.append({
                            "title": fmt.strip(),
                            "link": "",
                            "channel_id": ch_id,
                            "needs_resolution": True
                        })
                    elif isinstance(fmt, dict):
                        norm_fmts.append(fmt)
                ch["formats"] = norm_fmts
            channels.append(ch)

        return channels

    def get_category_channels(self, cat_link: Optional[str] = None, title: str = "Sports") -> List[Dict[str, Any]]:
        return self.get_channels_by_category(title, cat_link)

    def get_highlights(self) -> Dict[str, Any]:
        data = self._fetch_and_decrypt("cats/highlights.json")
        if data and isinstance(data, dict) and "channels" in data:
            return data
        return {
            "cats": [
                {"id": 301, "title": "All Highlights", "image": "", "isChecked": True},
                {"id": 302, "title": "Soccer", "image": "", "isChecked": False}
            ],
            "channels": []
        }
