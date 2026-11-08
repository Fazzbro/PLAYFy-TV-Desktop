"""
PLAYFy TV - High Performance Backend Service
Clean-Room Implementation of:
1. Reverse-Engineered Crypto & Dynamic Backlinks (od.c0 / PlayerActivity.f0)
2. Embed Stream Sniffer / Capture Engine (jd.z, jd.b0, jd.e0)
3. 3-Level Match Sorting & Sub-Filters (od.e, od.g, od.h, od.s.k)
4. ClearKey DRM Extraction for MPEG-DASH Streams
5. CORS Video Streaming Proxy
"""

import sys
import os
import re
import json
import base64
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Determine base directory whether running from source or compiled PyInstaller bundle
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add windows_app to import path for crypto and api_client
APP_DIR = os.path.join(BUNDLE_DIR, "windows_app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from api_client import ApiClient
from crypto import decrypt_payload
from score_engine import ScoreEngine

app = FastAPI(title="PLAYFy TV Core Engine", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = ApiClient()
score_engine = ScoreEngine()

# ---------------------------------------------------------------------------
# Embed Stream Capture Engine (Recovered from jd.z, jd.b0, jd.e0)
# ---------------------------------------------------------------------------

STREAM_EXT_RE = re.compile(
    r'https?://[^\s"\'<>`\\]{6,}\.(?:m3u8|mpd|mp4|webm|mkv|ts)(?:\?[^\s"\'<>`\\]*)?',
    re.IGNORECASE
)
PHP_STREAM_RE = re.compile(
    r'https?://[^\s"\'<>`\\]+\.php\?[^\s"\'<>`\\]*(?:m3u8|mpd)[^\s"\'<>`\\]*',
    re.IGNORECASE
)
CALL_SITE_RE = re.compile(
    r'\.(?:loadSource|load|setSource|setSrc)\s*\(\s*["\'`](https?://[^"\'`\s<>\\]+)',
    re.IGNORECASE
)
JSON_SRC_RE = re.compile(
    r'["\'](?:file|src|source|sources|hls|dash|url|stream|video|playback_url)["\']\s*:\s*["\'`](https?://[^"\'`\s<>\\]+)',
    re.IGNORECASE
)
B64_RE = re.compile(r'["\'`]([A-Za-z0-9+/]{30,}={0,2})["\'`]')
IFRAME_RE = re.compile(r'<iframe[^>]+src=["\'](https?://[^"\']+)["\']', re.IGNORECASE)
META_TAG_RE = re.compile(r'<meta[^>]+content=["\'](https?://[^"\']+)["\']', re.IGNORECASE)


def sniff_stream_from_html(html: str, base_url: str = "") -> List[str]:
    """
    Implements the 5-phase extraction algorithm from jd.z evaluateJavascript:
    1. Direct Regex scan of stream extensions (.m3u8, .mpd, .ts)
    2. Player API calls & JSON key bindings (.loadSource, "file":"...", "src":"...")
    3. Base64 decoded payloads (≥30 chars)
    4. HTML5 <video> / <source> / <meta> video tags
    5. Nested <iframe> embed fallbacks
    """
    found = []

    def add_if_valid(u: str):
        if not u or not isinstance(u, str):
            return
        cleaned = u.strip().replace('\\/', '/').replace('\\', '')
        if cleaned.startswith('//'):
            cleaned = 'https:' + cleaned
        if not cleaned.startswith('http'):
            return
        is_stream = bool(re.search(r'\.(?:m3u8|mpd|mp4|webm|mkv|ts)(\?|&|$|#)', cleaned, re.I)) or bool(re.search(r'\.php\?.*(?:m3u8|mpd)', cleaned, re.I))
        if is_stream and cleaned not in found:
            found.append(cleaned)

    # 1. Regex scan for stream extensions
    for m in STREAM_EXT_RE.finditer(html):
        add_if_valid(m.group(0))
    for m in PHP_STREAM_RE.finditer(html):
        add_if_valid(m.group(0))

    # 2. Player API and JSON configuration objects
    for m in CALL_SITE_RE.finditer(html):
        add_if_valid(m.group(1))
    for m in JSON_SRC_RE.finditer(html):
        add_if_valid(m.group(1))

    # 3. Base64 string candidates (jd.z line 64: atob)
    if not found:
        for bm in B64_RE.finditer(html):
            try:
                candidate = bm.group(1)
                decoded = base64.b64decode(candidate).decode('utf-8', errors='ignore')
                for m in STREAM_EXT_RE.finditer(decoded):
                    add_if_valid(m.group(0))
                for m in PHP_STREAM_RE.finditer(decoded):
                    add_if_valid(m.group(0))
                if found:
                    break
            except Exception:
                continue

    # 4. Meta video tags (og:video, twitter:player:stream)
    if not found:
        for m in META_TAG_RE.finditer(html):
            url = m.group(1)
            add_if_valid(url)

    return found


def capture_stream_from_url(target_url: str, depth: int = 0) -> Dict[str, Any]:
    """
    Fetches target page and crawls stream links matching jd.b0 WebView interceptor.
    Follows nested iframes if primary page contains no direct media.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Referer": target_url,
        "Accept": "*/*",
    }
    try:
        req = urllib.request.Request(target_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "")
            # Direct stream response
            if any(ext in content_type for ext in ["vnd.apple.mpegurl", "x-mpegURL", "dash+xml", "video/"]):
                return {
                    "success": True,
                    "stream_url": target_url,
                    "is_hls": ".m3u8" in target_url,
                    "is_dash": ".mpd" in target_url,
                    "headers": headers,
                    "depth": depth
                }
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return {"success": False, "error": str(e)}

    # Sniff stream URLs from page HTML
    streams = sniff_stream_from_html(html, target_url)
    if streams:
        primary = streams[0]
        return {
            "success": True,
            "stream_url": primary,
            "all_streams": streams,
            "is_hls": ".m3u8" in primary.lower(),
            "is_dash": ".mpd" in primary.lower(),
            "headers": {
                "User-Agent": headers["User-Agent"],
                "Referer": target_url
            },
            "depth": depth
        }

    # Recurse into nested iframes (up to depth 1)
    if depth < 1:
        iframes = IFRAME_RE.findall(html)
        for ifr in iframes:
            if not ifr.startswith("http"):
                continue
            nested = capture_stream_from_url(ifr, depth=depth + 1)
            if nested.get("success"):
                return nested

    return {"success": False, "error": "No media stream detected in document or embeds."}


# ---------------------------------------------------------------------------
# Helper: Parse Time and State Machine (p.q3 / gd.m / od.e)
# ---------------------------------------------------------------------------

def parse_match_time(time_str: str) -> Optional[datetime]:
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        clean = time_str.strip()
        return datetime.strptime(clean, "%Y/%m/%d %H:%M:%S %z").astimezone(timezone.utc)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(time_str.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def calculate_match_status(start_dt: Optional[datetime], end_dt: Optional[datetime], now_dt: Optional[datetime] = None) -> Dict[str, Any]:
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)

    if not start_dt:
        return {
            "state": "UPCOMING",
            "state_priority": 1,
            "badge_text": "Scheduled",
            "badge_color": "#888888",
            "seconds_left": 0,
            "elapsed_seconds": 0
        }

    now_ts = now_dt.timestamp()
    start_ts = start_dt.timestamp()
    end_ts = end_dt.timestamp() if end_dt else (start_ts + 7200)

    # 1. LIVE
    if start_ts <= now_ts < end_ts:
        elapsed = int(now_ts - start_ts)
        return {
            "state": "LIVE",
            "state_priority": 2,
            "badge_text": f"LIVE {format_duration(elapsed)}",
            "badge_color": "#ffffff",
            "seconds_left": int(end_ts - now_ts),
            "elapsed_seconds": elapsed
        }

    diff_start = start_ts - now_ts

    # 2. STARTING SOON (within 2 hours)
    if 0 < diff_start <= 7200:
        return {
            "state": "STARTING_SOON",
            "state_priority": 1,
            "badge_text": f"Starts in {format_duration(int(diff_start))}",
            "badge_color": "#cccccc",
            "seconds_left": int(diff_start),
            "elapsed_seconds": 0
        }

    # 3. UPCOMING
    if diff_start > 7200:
        return {
            "state": "UPCOMING",
            "state_priority": 1,
            "badge_text": start_dt.strftime("%d %b %H:%M UTC"),
            "badge_color": "#888888",
            "seconds_left": int(diff_start),
            "elapsed_seconds": 0
        }

    # 4. ENDED
    return {
        "state": "ENDED",
        "state_priority": 0,
        "badge_text": "Full Time",
        "badge_color": "#555555",
        "seconds_left": 0,
        "elapsed_seconds": int(now_ts - start_ts)
    }


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "service": "PLAYFy TV Native Core Engine",
        "version": "2.0.0",
        "features": [
            "Real live stream backlinks extraction (channels/{id}.json)",
            "Embed link capture / sniffing engine (jd.z / jd.b0)",
            "MPEG-DASH ClearKey DRM resolution",
            "Pure Cricket & Football filter",
            "3-Level APK match priority sorting"
        ]
    }


@app.get("/api/events")
def get_events(category: Optional[str] = None, timeline: Optional[str] = None, search: Optional[str] = None):
    """
    Returns Live Sports Events strictly filtered to Cricket and Football.
    Applies the recovered 3-level sort order:
    1. State Priority (LIVE=2 > UPCOMING=1 > ENDED=0)
    2. Pinned Status (isPinned=1 > isPinned=0)
    3. Start Time Delta (earlier start times first)
    """
    raw_data = client.get_live_events()
    channels = raw_data.get("channels", [])

    # Strict restriction to Cricket and Football
    ALLOWED = {"Football", "Cricket"}
    filtered_channels = [ch for ch in channels if ch.get("category") in ALLOWED]

    now_dt = datetime.now(timezone.utc)
    today_date = now_dt.date()

    processed = []
    for ch in filtered_channels:
        ev_info = ch.get("eventInfo", {})
        cat = ch.get("category", "")

        # Category Filter
        if category and category != "All" and cat.lower() != category.lower():
            continue

        # Search Query Filter
        if search:
            q = search.lower().strip()
            t_a = (ev_info.get("teamA") or "").lower()
            t_b = (ev_info.get("teamB") or "").lower()
            evt = (ev_info.get("eventName") or "").lower()
            title = (ch.get("title") or "").lower()
            if q not in t_a and q not in t_b and q not in evt and q not in title:
                continue

        start_dt = parse_match_time(ev_info.get("startTime", ""))
        end_dt = parse_match_time(ev_info.get("endTime", ""))
        status = score_engine.calculate_status_and_score(
            match_id=ch.get("id"),
            team_a=ev_info.get("teamA", ""),
            team_b=ev_info.get("teamB", ""),
            category=cat,
            start_dt=start_dt,
            end_dt=end_dt,
            now_dt=now_dt
        )
        state = status["state"]

        # Timeline Filter (od.s.k)
        if timeline == "live" and state != "LIVE":
            continue
        elif timeline == "today":
            if not start_dt or start_dt.date() != today_date:
                continue
        elif timeline == "upcoming":
            if state not in ("STARTING_SOON", "UPCOMING"):
                continue
        elif timeline == "finished" and state != "ENDED":
            continue

        item = {
            "id": ch.get("id"),
            "title": ch.get("title"),
            "category": cat,
            "image": ch.get("image", ""),
            "eventInfo": {
                "eventName": ev_info.get("eventName", "Sports Championship"),
                "teamA": ev_info.get("teamA", "Team A"),
                "teamB": ev_info.get("teamB", "Team B"),
                "teamAFlag": ev_info.get("teamAFlag", ""),
                "teamBFlag": ev_info.get("teamBFlag", ""),
                "startTime": ev_info.get("startTime", ""),
                "endTime": ev_info.get("endTime", ""),
                "isPinned": int(ev_info.get("isPinned", 0)) == 1,
                "eventBanner": ev_info.get("eventBanner", "")
            },
            "status": status,
            "formats_count": len(ch.get("formats", [])),
            "formats_preview": [f.get("title") if isinstance(f, dict) else str(f) for f in ch.get("formats", [])]
        }
        processed.append((item, status["state_priority"], 1 if item["eventInfo"]["isPinned"] else 0, start_dt.timestamp() if start_dt else float('inf')))

    # 3-Level APK Priority Sort
    def sort_fn(x):
        return (-x[1], -x[2], x[3])

    processed.sort(key=sort_fn)
    results = [p[0] for p in processed]

    football_total = sum(1 for ch in filtered_channels if ch.get("category") == "Football")
    cricket_total = sum(1 for ch in filtered_channels if ch.get("category") == "Cricket")

    return {
        "total": len(results),
        "counts": {
            "all": len(filtered_channels),
            "football": football_total,
            "cricket": cricket_total
        },
        "events": results
    }


@app.get("/api/categories")
def get_categories():
    return [
        {"id": "football", "title": "Football", "icon": "football", "slug": "football"},
        {"id": "cricket", "title": "Cricket", "icon": "cricket", "slug": "cricket"},
    ]


@app.get("/api/channels")
def get_channels(sport: Optional[str] = None):
    """
    Returns TV channels from cats/sports.json filtered to Cricket and Football.
    """
    sports_channels = client.get_channels_by_category("Sports")
    EXCLUDED = [
        "ufc", "fight", "combat", "wwe", "impact", "boxing",
        "f1", "motor", "nba", "basketball", "nfl", "mlb", "baseball",
        "tennis", "rugby", "pga", "golf", "strongman", "red bull",
        "hard knocks", "dp world", "world tour"
    ]
    filtered = []
    for ch in sports_channels:
        t = ch.get("title", "").lower()
        if any(ex in t for ex in EXCLUDED):
            continue

        # Classify as Cricket or Football
        is_cricket = any(kw in t for kw in ["cricket", "willow", "fancode", "t sports"])
        ch_sport = "Cricket" if is_cricket else "Football"

        if sport and sport.lower() != "all" and ch_sport.lower() != sport.lower():
            continue

        filtered.append({
            "id": ch.get("id"),
            "title": ch.get("title"),
            "image": ch.get("image", ""),
            "sport": ch_sport,
            "formats_count": len(ch.get("formats", [])),
            "formats_preview": [f.get("title") if isinstance(f, dict) else str(f) for f in ch.get("formats", [])]
        })

    return {
        "total": len(filtered),
        "channels": filtered
    }


@app.get("/api/streams/{channel_id}")
def get_channel_streams(channel_id: str):
    """
    Dynamically queries channels/{id}.json, extracting real live stream backlinks.
    Detects ClearKey DRM keys ('api' parameter) and provides parsed headers.
    """
    streams = client.get_channel_stream_links(channel_id)
    if not streams:
        return {"channel_id": channel_id, "streams": [], "error": "No broadcast servers currently online for this event."}

    parsed_servers = []
    for idx, s in enumerate(streams):
        raw_url = s.get("link", "")
        headers = s.get("headers", {})
        api_token = s.get("api", "").strip()

        # ClearKey DRM detection: e.g. 'd1a163914db8ffad2c3e94f979896a0d:9728800a3959aafdd5b0bcfbf3768811'
        clearkeys = {}
        has_clearkey = False
        if api_token and ":" in api_token:
            parts = api_token.split(":")
            if len(parts) == 2 and len(parts[0]) == 32 and len(parts[1]) == 32:
                clearkeys[parts[0]] = parts[1]
                has_clearkey = True

        is_hls = ".m3u8" in raw_url.lower()
        is_dash = ".mpd" in raw_url.lower() or s.get("is_dash", False)

        # Quality badge
        title_lower = s.get("title", "").lower()
        quality = "FHD" if "fhd" in title_lower or "1080" in title_lower else ("HD" if "hd" in title_lower or "720" in title_lower else "SD")

        # Determine if proxy is needed:
        # Standard User-Agent alone does NOT require proxying because the desktop browser already sends a valid User-Agent.
        # Direct CDN links (e.g. Amazon CloudFront, Akamai) allow direct CORS playback and fast streaming.
        # Proxy is only needed if custom Referer, Origin, or non-standard auth headers exist.
        needs_proxy = False
        ref_header = None
        origin_header = None
        if headers:
            for hk, hv in headers.items():
                if hk.lower() in ("referer", "origin"):
                    needs_proxy = True
                    if hk.lower() == "referer":
                        ref_header = hv
                    if hk.lower() == "origin":
                        origin_header = hv

        proxy_params = f"url={urllib.parse.quote(raw_url)}"
        if ref_header:
            proxy_params += f"&ref={urllib.parse.quote(ref_header)}"
        if origin_header:
            proxy_params += f"&origin={urllib.parse.quote(origin_header)}"
        proxy_url = f"/api/proxy?{proxy_params}"

        parsed_servers.append({
            "id": f"{channel_id}_{idx}",
            "server_index": idx,
            "title": s.get("title"),
            "link": raw_url,
            "proxy_link": proxy_url if needs_proxy else None,
            "quality": quality,
            "is_hls": is_hls,
            "is_dash": is_dash,
            "has_drm": has_clearkey,
            "clearkey": clearkeys,
            "headers": headers,
            "direct_playable": True
        })

    # Preserve exact original server broadcast order matching the APK's formats list
    return {
        "channel_id": channel_id,
        "total_servers": len(parsed_servers),
        "streams": parsed_servers
    }


@app.post("/api/capture-stream")
async def capture_stream(request: Request):
    """
    Embed link capture feature (reproduced from jd.z / jd.b0):
    Accepts any embed URL or streaming page and executes the 5-step sniffer to extract the live feed.
    """
    body = await request.json()
    url = body.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter in request body.")

    result = capture_stream_from_url(url)
    return result


@app.get("/api/proxy")
def stream_proxy(url: str, request: Request):
    """
    CORS-bypassing streaming proxy for feeds requiring specific Referer or User-Agent headers.
    Automatically handles relative segment resolution for DASH (MPD) and HLS (M3U8).
    """
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter.")

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    }
    # Forward Referer and Origin if passed in query parameters
    ref = request.query_params.get("ref")
    if ref:
        req_headers["Referer"] = ref
    origin = request.query_params.get("origin")
    if origin:
        req_headers["Origin"] = origin

    # Forward range headers for video seek
    if "range" in request.headers:
        req_headers["Range"] = request.headers["range"]

    try:
        req = urllib.request.Request(url, headers=req_headers)
        resp = urllib.request.urlopen(req, timeout=12)
        content_type = resp.headers.get("Content-Type", "")

        # 1. For DASH MPD manifests: inject BaseURL so relative segment templates resolve correctly to remote CDN
        if ".mpd" in url.lower() or "dash+xml" in content_type:
            raw_text = resp.read().decode('utf-8', errors='replace')
            if "<BaseURL>" not in raw_text and "<BaseURL " not in raw_text:
                base_folder = url.rsplit('/', 1)[0] + '/'
                pattern = re.compile(r'(<MPD\b[^>]*>)', re.IGNORECASE)
                raw_text = pattern.sub(r'\1\n  <BaseURL>' + base_folder + r'</BaseURL>', raw_text, count=1)
            mpd_bytes = raw_text.encode('utf-8')
            resp_headers = {
                "Content-Type": "application/dash+xml",
                "Content-Length": str(len(mpd_bytes)),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Cache-Control": "no-cache"
            }
            return Response(content=mpd_bytes, status_code=200, headers=resp_headers)

        # 2. For HLS M3U8 playlists: rewrite relative segments to absolute URLs
        if ".m3u8" in url.lower() or "mpegurl" in content_type.lower():
            raw_text = resp.read().decode('utf-8', errors='replace')
            lines = raw_text.splitlines()
            rewritten = []
            for line in lines:
                sline = line.strip()
                if not sline:
                    rewritten.append(line)
                elif sline.startswith('#'):
                    def repl_uri(m):
                        sub_uri = m.group(1)
                        if not sub_uri.startswith('http'):
                            sub_uri = urllib.parse.urljoin(url, sub_uri)
                        return f'URI="{sub_uri}"'
                    line = re.sub(r'URI=["\']([^"\']+)["\']', repl_uri, line)
                    rewritten.append(line)
                elif not sline.startswith('http'):
                    rewritten.append(urllib.parse.urljoin(url, sline))
                else:
                    rewritten.append(line)
            m3u8_bytes = "\n".join(rewritten).encode('utf-8')
            resp_headers = {
                "Content-Type": "application/vnd.apple.mpegurl",
                "Content-Length": str(len(m3u8_bytes)),
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Cache-Control": "no-cache"
            }
            return Response(content=m3u8_bytes, status_code=200, headers=resp_headers)

        # 3. For video chunks, ts files, and initialization segments: stream chunks
        def iter_chunks():
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

        resp_headers = {}
        for h in ["Content-Type", "Content-Length", "Accept-Ranges", "Content-Range"]:
            if h in resp.headers:
                resp_headers[h] = resp.headers[h]

        resp_headers["Access-Control-Allow-Origin"] = "*"
        resp_headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"

        return StreamingResponse(iter_chunks(), status_code=resp.status, headers=resp_headers)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Proxy streaming failed: {e}")


# ---------------------------------------------------------------------------
# Serve Production React Frontend
# ---------------------------------------------------------------------------

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

DIST_DIR = os.path.join(BUNDLE_DIR, "react_app", "dist")
if os.path.exists(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")
        target_file = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

