"""
PLAYFy TV Favorites Screen (hd.g)
Displays bookmarked native channels and bookmarked M3U playlist streams from SQLite.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QButtonGroup
)
from PySide6.QtCore import Qt, Signal

class FavoritesView(QWidget):
    stream_selected = Signal(str, list)

    def __init__(self, db, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.active_subtab = "channels"

        self._setup_ui()
        self.refresh_favorites()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header Title
        header = QHBoxLayout()
        title_lbl = QLabel("⭐ Bookmarks & Favorites", self)
        title_lbl.setProperty("class", "heading")
        header.addWidget(title_lbl)
        header.addStretch()

        self.btn_refresh = QPushButton("⟳ Refresh", self)
        self.btn_refresh.setProperty("class", "primary-btn")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_favorites)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        # Subtab Buttons (Channels vs Playlist Streams)
        tabs_layout = QHBoxLayout()
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)

        self.btn_tab_ch = QPushButton("Live Channels", self)
        self.btn_tab_ch.setCheckable(True)
        self.btn_tab_ch.setChecked(True)
        self.btn_tab_ch.setProperty("class", "chip")
        self.btn_tab_ch.setCursor(Qt.PointingHandCursor)
        self.btn_tab_ch.clicked.connect(lambda: self._switch_tab("channels"))
        self.tab_group.addButton(self.btn_tab_ch)
        tabs_layout.addWidget(self.btn_tab_ch)

        self.btn_tab_pl = QPushButton("M3U Playlist Streams", self)
        self.btn_tab_pl.setCheckable(True)
        self.btn_tab_pl.setProperty("class", "chip")
        self.btn_tab_pl.setCursor(Qt.PointingHandCursor)
        self.btn_tab_pl.clicked.connect(lambda: self._switch_tab("playlist"))
        self.tab_group.addButton(self.btn_tab_pl)
        tabs_layout.addWidget(self.btn_tab_pl)

        tabs_layout.addStretch()
        layout.addLayout(tabs_layout)

        # Cards Scroll Area
        self.cards_scroll = QScrollArea(self)
        self.cards_scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setSpacing(14)
        self.cards_scroll.setWidget(self.cards_container)
        layout.addWidget(self.cards_scroll, stretch=1)

    def _switch_tab(self, subtab: str):
        self.active_subtab = subtab
        self.refresh_favorites()

    def refresh_favorites(self):
        while self.cards_grid.count() > 0:
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.active_subtab == "channels":
            favs = self.db.get_favorites()
            if not favs:
                empty = QLabel("No channel favorites saved yet.\nClick the star icon '' on any channel to add it here.", self.cards_container)
                empty.setStyleSheet("color: #777; font-size: 14px; margin: 40px;")
                empty.setAlignment(Qt.AlignCenter)
                self.cards_grid.addWidget(empty, 0, 0)
                return

            row, col = 0, 0
            for item in favs:
                card = self._create_fav_channel_card(item)
                self.cards_grid.addWidget(card, row, col)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1

        else:
            pl_favs = self.db.get_playlist_favorites()
            if not pl_favs:
                empty = QLabel("No M3U stream favorites saved yet.\nClick the star icon '' on any playlist stream to add it here.", self.cards_container)
                empty.setStyleSheet("color: #777; font-size: 14px; margin: 40px;")
                empty.setAlignment(Qt.AlignCenter)
                self.cards_grid.addWidget(empty, 0, 0)
                return

            row, col = 0, 0
            for item in pl_favs:
                card = self._create_fav_playlist_card(item)
                self.cards_grid.addWidget(card, row, col)
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

    def _create_fav_channel_card(self, item: Dict[str, Any]) -> QFrame:
        card = QFrame(self.cards_container)
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        ch_id = item.get("id")
        title = item.get("title", "Channel")
        formats = item.get("formats", [])

        header = QHBoxLayout()
        title_lbl = QLabel(title, card)
        title_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        title_lbl.setWordWrap(True)
        header.addWidget(title_lbl, stretch=1)

        btn_del = QPushButton("", card)
        btn_del.setFixedSize(28, 28)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("background-color: transparent; border: none; font-size: 18px; color: #FFD700;")
        btn_del.clicked.connect(lambda: self._remove_channel_fav(ch_id))
        header.addWidget(btn_del)
        layout.addLayout(header)

        btn_play = QPushButton("▶ Play Stream", card)
        btn_play.setProperty("class", "primary-btn")
        btn_play.setCursor(Qt.PointingHandCursor)
        btn_play.clicked.connect(lambda checked=False, t=title, f_list=formats: self.stream_selected.emit(t, f_list))
        layout.addWidget(btn_play)

        return card

    def _create_fav_playlist_card(self, item: Dict[str, Any]) -> QFrame:
        card = QFrame(self.cards_container)
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        name = item.get("name", "M3U Stream")
        group = item.get("groupTitle", "General")
        link = item.get("link", "")

        header = QHBoxLayout()
        grp_lbl = QLabel(f" {group}", card)
        grp_lbl.setStyleSheet("color: #0078D4; font-size: 11px; font-weight: bold;")
        header.addWidget(grp_lbl)
        header.addStretch()

        btn_del = QPushButton("", card)
        btn_del.setFixedSize(28, 28)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("background-color: transparent; border: none; font-size: 18px; color: #FFD700;")
        btn_del.clicked.connect(lambda: self._remove_m3u_fav(link))
        header.addWidget(btn_del)
        layout.addLayout(header)

        name_lbl = QLabel(name, card)
        name_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)

        btn_play = QPushButton("▶ Play Stream", card)
        btn_play.setProperty("class", "primary-btn")
        btn_play.setCursor(Qt.PointingHandCursor)
        btn_play.clicked.connect(lambda checked=False, t=name, l=link: self.stream_selected.emit(t, [{"title": "Default", "link": l}]))
        layout.addWidget(btn_play)

        return card

    def _remove_channel_fav(self, channel_id: int):
        self.db.remove_favorite(channel_id)
        self.refresh_favorites()

    def _remove_m3u_fav(self, link: str):
        self.db.remove_playlist_fav(link)
        self.refresh_favorites()
