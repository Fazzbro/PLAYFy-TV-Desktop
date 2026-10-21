"""
PLAYFy TV Clean-Room M3U / M3U8 Parser
Extracts PlaylistItem objects (kd.h0) from standard and extended M3U streams.
"""

import re
import urllib.request
import os
from typing import List, Dict, Any

class M3UParser:
    @staticmethod
    def parse_content(content: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        lines = [line.strip() for line in content.splitlines() if line.strip()]

        current_item: Dict[str, Any] = {
            "name": "",
            "groupTitle": "General",
            "logo": "",
            "link": "",
            "userAgent": None,
            "referrer": None,
            "origin": None,
            "cookie": None,
            "drmLicense": None,
            "drmScheme": None
        }

        for line in lines:
            if line.startswith("#EXTINF:"):
                # Extract attributes
                # tvg-name="..."
                m_name = re.search(r'tvg-name=["\']([^"\']+)["\']', line, re.IGNORECASE)
                # tvg-logo="..."
                m_logo = re.search(r'tvg-logo=["\']([^"\']+)["\']', line, re.IGNORECASE)
                # group-title="..."
                m_group = re.search(r'group-title=["\']([^"\']+)["\']', line, re.IGNORECASE)
                
                # Title after comma
                comma_idx = line.rfind(',')
                title = line[comma_idx + 1:].strip() if comma_idx != -1 else ""

                if m_name and not title:
                    title = m_name.group(1).strip()
                if not title:
                    title = "Unknown Channel"

                current_item["name"] = title
                if m_group:
                    current_item["groupTitle"] = m_group.group(1).strip()
                if m_logo:
                    current_item["logo"] = m_logo.group(1).strip()

            elif line.startswith("#EXTVLCOPT:"):
                opt = line[len("#EXTVLCOPT:"):].strip()
                if opt.lower().startswith("http-user-agent="):
                    current_item["userAgent"] = opt[len("http-user-agent="):].strip()
                elif opt.lower().startswith("http-referrer="):
                    current_item["referrer"] = opt[len("http-referrer="):].strip()

            elif line.startswith("#KODIPROP:"):
                prop = line[len("#KODIPROP:"):].strip()
                if "license_key=" in prop.lower():
                    current_item["drmLicense"] = prop.split("=", 1)[1].strip()
                elif "license_type=" in prop.lower():
                    current_item["drmScheme"] = prop.split("=", 1)[1].strip()

            elif not line.startswith("#"):
                # Stream URL
                current_item["link"] = line
                if not current_item["name"]:
                    # Fallback title from URL tail
                    current_item["name"] = line.split('/')[-1].split('?')[0] or "Channel"
                items.append(dict(current_item))

                # Reset item
                current_item = {
                    "name": "",
                    "groupTitle": "General",
                    "logo": "",
                    "link": "",
                    "userAgent": None,
                    "referrer": None,
                    "origin": None,
                    "cookie": None,
                    "drmLicense": None,
                    "drmScheme": None
                }

        return items

    @classmethod
    def load_from_source(cls, source: str) -> List[Dict[str, Any]]:
        """
        Loads and parses M3U content from an HTTP URL or local file path.
        """
        if source.startswith("http://") or source.startswith("https://"):
            req = urllib.request.Request(source, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode('utf-8', errors='replace')
                return cls.parse_content(content)
        elif os.path.exists(source):
            with open(source, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                return cls.parse_content(content)
        else:
            raise FileNotFoundError(f"Cannot locate M3U source: {source}")
