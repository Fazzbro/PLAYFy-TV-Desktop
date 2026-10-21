"""
PLAYFy TV Categories & Channels Screen (kd.i, kd.l)
Allows browsing TV channels by category, adding favorites to SQLite, and stream playback.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QButtonGroup, QLineEdit
)
from PySide6.QtCore import Qt, Signal

class ChannelsView(QWidget):
    stream_selected = Signal(str, list)
    open_playlist_url = Signal(str, str)  # title, url

    def __init__(self, api_client, db, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.api_client = api_client
        self.db = db
        self.categories: List[Dict[str, Any]] = []
        self.current_channels: List[Dict[str, Any]] = []
        self.active_cat_id: Optional[int] = None

        self._setup_ui()
        self.refresh_categories()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Title and Search Bar
        header = QHBoxLayout()
        title_lbl = QLabel(" Channels & Categories", self)
        title_lbl.setProperty("class", "heading")
        header.addWidget(title_lbl)
        header.addStretch()

        self.search_box = QLineEdit(self)
        self.search_box.setPlaceholderText(" Search channels...")
        self.search_box.setFixedWidth(240)
        self.search_box.textChanged.connect(self._on_search_changed)
        header.addWidget(self.search_box)
        layout.addLayout(header)

        # Categories Horizontal Chip Bar
        self.cat_scroll = QScrollArea(self)
        self.cat_scroll.setFixedHeight(48)
        self.cat_scroll.setWidgetResizable(True)
        self.cat_container = QWidget()
        self.cat_layout = QHBoxLayout(self.cat_container)
        self.cat_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_layout.setSpacing(8)
        self.cat_scroll.setWidget(self.cat_container)
        layout.addWidget(self.cat_scroll)

        # Channels Grid Area
        self.chan_scroll = QScrollArea(self)
        self.chan_scroll.setWidgetResizable(True)
        self.chan_container = QWidget()
        self.chan_grid = QGridLayout(self.chan_container)
        self.chan_grid.setContentsMargins(0, 0, 0, 0)
        self.chan_grid.setSpacing(16)
        self.chan_scroll.setWidget(self.chan_container)
        layout.addWidget(self.chan_scroll, stretch=1)

    def refresh_categories(self):
        self.categories = self.api_client.get_categories()
        self._populate_category_chips()
        if self.categories:
            self._select_category(self.categories[0])

    def _populate_category_chips(self):
        while self.cat_layout.count() > 0:
            item = self.cat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.cat_group = QButtonGroup(self)
        self.cat_group.setExclusive(True)

        for i, c in enumerate(self.categories):
            btn = QPushButton(c.get("title", f"Category {i+1}"), self.cat_container)
            btn.setCheckable(True)
            btn.setProperty("class", "chip")
            btn.setCursor(Qt.PointingHandCursor)
            if i == 0:
                btn.setChecked(True)
            self.cat_group.addButton(btn)
            self.cat_layout.addWidget(btn)
            btn.clicked.connect(lambda checked=False, cat=c: self._select_category(cat))

        self.cat_layout.addStretch()

    def _select_category(self, cat: Dict[str, Any]):
        self.active_cat_id = cat.get("id")
        cat_link = cat.get("catLink", "")
        title = cat.get("title", "Category")

        # Fetch channel list directly from catalog or M3U playlist
        raw_channels = self.api_client.get_channels_by_category(title, cat_link)

        # When browsing Sports, restrict strictly to Cricket and Football channels (purge all others)
        if "sport" in title.lower():
            EXCLUDED_KEYWORDS = [
                "ufc", "fight", "combat", "wwe", "impact", "boxing",
                "f1", "motor", "nba", "basketball", "nfl", "mlb", "baseball",
                "tennis", "rugby", "pga", "golf", "strongman", "red bull"
            ]
            filtered_sports = []
            for ch in raw_channels:
                ch_title = ch.get("title", "").lower()
                if any(kw in ch_title for kw in EXCLUDED_KEYWORDS):
                    continue
                filtered_sports.append(ch)
            self.current_channels = filtered_sports
        else:
            self.current_channels = raw_channels

        self._render_channel_cards(self.current_channels)

    def _on_search_changed(self, text: str):
        query = text.strip().lower()
        if not query:
            self._render_channel_cards(self.current_channels)
            return
        filtered = [
            c for c in self.current_channels
            if query in c.get("title", "").lower()
        ]
        self._render_channel_cards(filtered)

    def _render_channel_cards(self, channels: List[Dict[str, Any]]):
        while self.chan_grid.count() > 0:
            item = self.chan_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not channels:
            empty = QLabel("No channels found in this category.", self.chan_container)
            empty.setStyleSheet("color: #777777; font-size: 14px; margin: 30px;")
            empty.setAlignment(Qt.AlignCenter)
            self.chan_grid.addWidget(empty, 0, 0, 1, 3)
            return

        row, col = 0, 0
        for ch in channels:
            card = self._create_channel_card(ch)
            self.chan_grid.addWidget(card, row, col)
            col += 1
            if col >= 3:  # 3 columns layout
                col = 0
                row += 1

    def _create_channel_card(self, channel: Dict[str, Any]) -> QFrame:
        card = QFrame(self.chan_container)
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        ch_id = channel.get("id", 0)
        title = channel.get("title", "Live Channel")
        image = channel.get("image", "")
        formats = channel.get("formats", [])

        # Header: Channel Title and Favorite Button
        header = QHBoxLayout()
        icon_lbl = QLabel("", card)
        icon_lbl.setStyleSheet("font-size: 18px;")
        header.addWidget(icon_lbl)

        title_lbl = QLabel(title, card)
        title_lbl.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 14px;")
        title_lbl.setWordWrap(True)
        header.addWidget(title_lbl, stretch=1)

        # Favorite Button
        is_fav = self.db.is_favorite(ch_id)
        fav_btn = QPushButton("" if is_fav else "", card)
        fav_btn.setFixedSize(30, 30)
        fav_btn.setCursor(Qt.PointingHandCursor)
        fav_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: none; font-size: 18px;
                color: {"#FFD700" if is_fav else "#888888"};
            }}
            QPushButton:hover {{ color: #FFD700; }}
        """)
        fav_btn.clicked.connect(lambda: self._toggle_favorite(channel, fav_btn))
        header.addWidget(fav_btn)
        card_layout.addLayout(header)

        # Stream Play Buttons with dynamic backlink resolution
        action_layout = QHBoxLayout()
        action_layout.setSpacing(6)

        btn_watch = QPushButton("▶ Watch Live", card)
        btn_watch.setProperty("class", "primary-btn")
        btn_watch.setCursor(Qt.PointingHandCursor)
        btn_watch.clicked.connect(lambda checked=False, ch=channel: self._on_channel_watch_clicked(ch))
        action_layout.addWidget(btn_watch)
        action_layout.addStretch()
        card_layout.addLayout(action_layout)

        return card

    def _on_channel_watch_clicked(self, channel: Dict[str, Any]):
        title = channel.get("title", "Live Channel")
        ch_id = channel.get("id")

        # Resolve real live stream backlinks dynamically from channels/{id}.json
        real_streams = self.api_client.get_channel_stream_links(ch_id)
        if not real_streams:
            real_streams = [f for f in channel.get("formats", []) if isinstance(f, dict) and f.get("link")]
        if not real_streams:
            raw_fmts = channel.get("formats", [])
            real_streams = [{"title": f.get("title") if isinstance(f, dict) else str(f), "link": ""} for f in raw_fmts]

        # Prioritize direct HLS .m3u8 feeds for immediate playback
        def stream_sorter(s):
            link = s.get("link", "").lower()
            is_hls = ".m3u8" in link
            is_dash = ".mpd" in link or s.get("is_dash", False)
            if is_hls and not is_dash:
                return 0
            if not is_dash:
                return 1
            return 2

        real_streams.sort(key=stream_sorter)

        if real_streams:
            self.stream_selected.emit(title, real_streams)

    def _toggle_favorite(self, channel: Dict[str, Any], btn: QPushButton):
        ch_id = channel.get("id", 0)
        title = channel.get("title", "")
        image = channel.get("image", "")
        formats = channel.get("formats", [])

        if self.db.is_favorite(ch_id):
            self.db.remove_favorite(ch_id)
            btn.setText("")
            btn.setStyleSheet("background-color: transparent; border: none; font-size: 18px; color: #888888;")
        else:
            self.db.add_favorite(ch_id, title, image, formats)
            btn.setText("")
            btn.setStyleSheet("background-color: transparent; border: none; font-size: 18px; color: #FFD700;")
