"""
PLAYFy TV SQLite Database Module
Implements persistence identical to Room OpenHelper (hd.g):
- favorites (built-in channel bookmarks)
- playlistFav (M3U stream bookmarks)
- playlists (user imported M3U sources)
"""

import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.expanduser("~"), ".playfy_tv.db")

class Database:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._shared_conn = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. favorites
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER NOT NULL PRIMARY KEY,
                    title TEXT NOT NULL,
                    image TEXT NOT NULL,
                    formats TEXT NOT NULL
                )
            """)
            # 2. playlistFav
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlistFav (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    groupTitle TEXT,
                    logo TEXT,
                    link TEXT NOT NULL,
                    userAgent TEXT,
                    referrer TEXT,
                    origin TEXT,
                    cookie TEXT,
                    drmLicense TEXT,
                    drmScheme TEXT
                )
            """)
            # 3. playlists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    path TEXT NOT NULL
                )
            """)
            conn.commit()

    # --- Favorites Operations ---
    def get_favorites(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT id, title, image, formats FROM favorites ORDER BY id DESC").fetchall()
            result = []
            for r in rows:
                try:
                    formats = json.loads(r["formats"])
                except Exception:
                    formats = []
                result.append({
                    "id": r["id"],
                    "title": r["title"],
                    "image": r["image"],
                    "formats": formats
                })
            return result

    def is_favorite(self, channel_id: int) -> bool:
        with self._get_connection() as conn:
            row = conn.execute("SELECT 1 FROM favorites WHERE id = ?", (channel_id,)).fetchone()
            return row is not None

    def add_favorite(self, channel_id: int, title: str, image: str, formats: List[Dict[str, Any]]):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO favorites (id, title, image, formats) VALUES (?, ?, ?, ?)",
                (channel_id, title, image, json.dumps(formats))
            )
            conn.commit()

    def remove_favorite(self, channel_id: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM favorites WHERE id = ?", (channel_id,))
            conn.commit()

    # --- Playlists Operations ---
    def get_playlists(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT id, title, path FROM playlists ORDER BY id DESC").fetchall()
            return [{"id": r["id"], "title": r["title"], "path": r["path"]} for r in rows]

    def add_playlist(self, title: str, path: str) -> int:
        with self._get_connection() as conn:
            cur = conn.execute("INSERT INTO playlists (title, path) VALUES (?, ?)", (title, path))
            conn.commit()
            return cur.lastrowid

    def delete_playlist(self, playlist_id: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
            conn.commit()

    # --- Playlist Favorites (playlistFav) ---
    def get_playlist_favorites(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, name, groupTitle, logo, link, userAgent, referrer, origin, cookie, drmLicense, drmScheme 
                FROM playlistFav ORDER BY id DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def is_playlist_fav(self, link: str) -> bool:
        with self._get_connection() as conn:
            row = conn.execute("SELECT 1 FROM playlistFav WHERE link = ?", (link,)).fetchone()
            return row is not None

    def add_playlist_fav(self, item: Dict[str, Any]) -> int:
        with self._get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO playlistFav (name, groupTitle, logo, link, userAgent, referrer, origin, cookie, drmLicense, drmScheme)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get("name"), item.get("groupTitle"), item.get("logo"), item.get("link"),
                item.get("userAgent"), item.get("referrer"), item.get("origin"), item.get("cookie"),
                item.get("drmLicense"), item.get("drmScheme")
            ))
            conn.commit()
            return cur.lastrowid

    def remove_playlist_fav(self, link: str):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM playlistFav WHERE link = ?", (link,))
            conn.commit()
