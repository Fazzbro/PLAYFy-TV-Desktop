"""
PLAYFy TV Windows Native Application Host Window
Main navigation shell with sidebar, stacked content pages, and media player view.
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QFrame, QButtonGroup, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QFont

from api_client import ApiClient
from database import Database
from player import VideoPlayerWidget
from ui.events_view import EventsView
from ui.channels_view import ChannelsView
from ui.highlights_view import HighlightsView
from ui.playlists_view import PlaylistsView
from ui.favorites_view import FavoritesView
from ui.settings_view import SettingsView
from ui.styles import DARK_THEME

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PLAYFy TV Desktop")
        self.resize(1180, 760)
        self.setMinimumSize(960, 600)
        self.setStyleSheet(DARK_THEME)

        # Initialize Backend Services
        self.api_client = ApiClient()
        self.db = Database()

        # State tracking
        self.last_view_index = 0

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        self.sidebar = QFrame(central_widget)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 20, 14, 20)
        sidebar_layout.setSpacing(6)

        # App Logo & Branding
        logo_layout = QHBoxLayout()
        logo_icon = QLabel("", self.sidebar)
        logo_icon.setStyleSheet("font-size: 26px;")
        logo_layout.addWidget(logo_icon)

        brand_lbl = QLabel("PLAYFy TV", self.sidebar)
        brand_lbl.setStyleSheet("font-size: 18px; font-weight: 900; color: #0078D4; letter-spacing: 1px;")
        logo_layout.addWidget(brand_lbl)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)

        ver_lbl = QLabel("v1.7 Windows Edition", self.sidebar)
        ver_lbl.setStyleSheet("color: #666666; font-size: 11px; margin-left: 4px; margin-bottom: 18px;")
        sidebar_layout.addWidget(ver_lbl)

        # Navigation Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_nav_events = self._create_nav_btn("  Live Sports", 0)
        self.btn_nav_channels = self._create_nav_btn("  Channels", 1)
        self.btn_nav_highlights = self._create_nav_btn("  Highlights", 2)
        self.btn_nav_playlists = self._create_nav_btn("  M3U Playlists", 3)
        self.btn_nav_favorites = self._create_nav_btn("⭐  Favorites", 4)
        self.btn_nav_settings = self._create_nav_btn("  Settings", 5)

        self.btn_nav_events.setChecked(True)

        for btn in [
            self.btn_nav_events, self.btn_nav_channels, self.btn_nav_highlights,
            self.btn_nav_playlists, self.btn_nav_favorites, self.btn_nav_settings
        ]:
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Connection Status
        status_frame = QFrame(self.sidebar)
        status_frame.setStyleSheet("background-color: #222222; border-radius: 6px; padding: 8px;")
        st_layout = QHBoxLayout(status_frame)
        st_layout.setContentsMargins(6, 4, 6, 4)
        dot = QLabel("●", status_frame)
        dot.setStyleSheet("color: #00FF88; font-size: 12px;")
        st_layout.addWidget(dot)
        st_lbl = QLabel("Server: Online", status_frame)
        st_lbl.setStyleSheet("color: #AAAAAA; font-size: 11px;")
        st_layout.addWidget(st_lbl)
        sidebar_layout.addWidget(status_frame)

        main_layout.addWidget(self.sidebar)

        # 2. Main Stacked Views Area
        self.stack = QStackedWidget(central_widget)

        self.events_view = EventsView(self.api_client, self)
        self.channels_view = ChannelsView(self.api_client, self.db, self)
        self.highlights_view = HighlightsView(self.api_client, self)
        self.playlists_view = PlaylistsView(self.db, self)
        self.favorites_view = FavoritesView(self.db, self)
        self.settings_view = SettingsView(self.api_client, self)
        self.player_view = VideoPlayerWidget(self)

        self.stack.addWidget(self.events_view)        # Index 0
        self.stack.addWidget(self.channels_view)      # Index 1
        self.stack.addWidget(self.highlights_view)    # Index 2
        self.stack.addWidget(self.playlists_view)     # Index 3
        self.stack.addWidget(self.favorites_view)     # Index 4
        self.stack.addWidget(self.settings_view)      # Index 5
        self.stack.addWidget(self.player_view)        # Index 6

        main_layout.addWidget(self.stack, stretch=1)

    def _create_nav_btn(self, text: str, page_idx: int) -> QPushButton:
        btn = QPushButton(text, self.sidebar)
        btn.setCheckable(True)
        btn.setProperty("class", "nav-btn")
        btn.setCursor(Qt.PointingHandCursor)
        self.nav_group.addButton(btn)
        btn.clicked.connect(lambda: self._switch_page(page_idx))
        return btn

    def _switch_page(self, page_idx: int):
        self.last_view_index = page_idx
        self.stack.setCurrentIndex(page_idx)

    def _connect_signals(self):
        # Stream playback signals from all views
        self.events_view.stream_selected.connect(self._open_player)
        self.channels_view.stream_selected.connect(self._open_player)
        self.highlights_view.stream_selected.connect(self._open_player)
        self.playlists_view.stream_selected.connect(self._open_player)
        self.favorites_view.stream_selected.connect(self._open_player)
        self.settings_view.play_direct_stream.connect(self._play_direct_url)

        # Playlist launcher from category view
        self.channels_view.open_playlist_url.connect(self._open_category_m3u)

        # Player close signal
        self.player_view.close_requested.connect(self._close_player)

    def _open_player(self, title: str, formats: List[Dict[str, Any]]):
        self.player_view.load_stream(title, formats)
        self.stack.setCurrentIndex(6)

    def _play_direct_url(self, title: str, url: str):
        self.player_view.play_url(title, url)
        self.stack.setCurrentIndex(6)

    def _open_category_m3u(self, title: str, m3u_url: str):
        self.playlists_view.load_playlist_channels({"title": title, "path": m3u_url, "id": -1})
        self.btn_nav_playlists.setChecked(True)
        self.stack.setCurrentIndex(3)

    def _close_player(self):
        self.stack.setCurrentIndex(self.last_view_index)
