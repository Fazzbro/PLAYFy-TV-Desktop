"""
PLAYFy TV Settings Screen (n6.d Case 1)
Provides direct network stream playback, quality settings (forceLow),
Remote Config refresh, and community links.
"""

from typing import Optional
import webbrowser
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QCheckBox, QLineEdit, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal

class SettingsView(QWidget):
    play_direct_stream = Signal(str, str)  # title, url

    def __init__(self, api_client, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.api_client = api_client
        self.force_low = False

        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(20)

        # Header Title
        title_lbl = QLabel(" Settings & Stream Tools", container)
        title_lbl.setProperty("class", "heading")
        layout.addWidget(title_lbl)

        # 1. Network Stream Launcher Box
        stream_card = QFrame(container)
        stream_card.setProperty("class", "card")
        sc_layout = QVBoxLayout(stream_card)
        sc_layout.setContentsMargins(18, 16, 18, 16)
        sc_layout.setSpacing(10)

        sc_title = QLabel(" Open Network Stream", stream_card)
        sc_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0078D4;")
        sc_layout.addWidget(sc_title)

        sc_sub = QLabel("Play any custom live stream directly (HLS .m3u8, MPEG-DASH .mpd, or progressive MP4):", stream_card)
        sc_sub.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        sc_layout.addWidget(sc_sub)

        input_layout = QHBoxLayout()
        self.stream_input = QLineEdit(stream_card)
        self.stream_input.setPlaceholderText("https://example.com/live/stream.m3u8")
        input_layout.addWidget(self.stream_input, stretch=1)

        self.btn_play_direct = QPushButton("▶ Play Stream", stream_card)
        self.btn_play_direct.setProperty("class", "primary-btn")
        self.btn_play_direct.setCursor(Qt.PointingHandCursor)
        self.btn_play_direct.clicked.connect(self._on_play_direct)
        input_layout.addWidget(self.btn_play_direct)
        sc_layout.addLayout(input_layout)
        layout.addWidget(stream_card)

        # 2. General Preferences Card
        pref_card = QFrame(container)
        pref_card.setProperty("class", "card")
        p_layout = QVBoxLayout(pref_card)
        p_layout.setContentsMargins(18, 16, 18, 16)
        p_layout.setSpacing(14)

        p_title = QLabel("General Preferences", pref_card)
        p_title.setStyleSheet("font-size: 15px; font-weight: bold; color: white;")
        p_layout.addWidget(p_title)

        # forceLow toggle
        self.chk_force_low = QCheckBox("Enable Low Quality Mode (forceLow)", pref_card)
        self.chk_force_low.setStyleSheet("color: white; font-size: 13px;")
        self.chk_force_low.stateChanged.connect(self._on_force_low_changed)
        p_layout.addWidget(self.chk_force_low)

        chk_sub = QLabel("Forces the video player to request lowest bitrate rendition to save bandwidth.", pref_card)
        chk_sub.setStyleSheet("color: #888888; font-size: 11px; margin-left: 20px;")
        p_layout.addWidget(chk_sub)

        # Refresh Remote Config Button
        btn_refresh_rc = QPushButton("⟳ Reload Firebase Remote Config & CDN Endpoints", pref_card)
        btn_refresh_rc.setProperty("class", "chip")
        btn_refresh_rc.setCursor(Qt.PointingHandCursor)
        btn_refresh_rc.clicked.connect(self._refresh_remote_config)
        p_layout.addWidget(btn_refresh_rc)
        layout.addWidget(pref_card)

        # 3. Community & Support Card
        comm_card = QFrame(container)
        comm_card.setProperty("class", "card")
        c_layout = QVBoxLayout(comm_card)
        c_layout.setContentsMargins(18, 16, 18, 16)
        c_layout.setSpacing(12)

        c_title = QLabel("Community & Support", comm_card)
        c_title.setStyleSheet("font-size: 15px; font-weight: bold; color: white;")
        c_layout.addWidget(c_title)

        comm_btns = QHBoxLayout()
        btn_tg = QPushButton(" Official Telegram Channel", comm_card)
        btn_tg.setProperty("class", "chip")
        btn_tg.setCursor(Qt.PointingHandCursor)
        btn_tg.clicked.connect(lambda: webbrowser.open("https://t.me/playfy_tv"))
        comm_btns.addWidget(btn_tg)

        btn_faq = QPushButton(" App Instructions & FAQ", comm_card)
        btn_faq.setProperty("class", "chip")
        btn_faq.setCursor(Qt.PointingHandCursor)
        btn_faq.clicked.connect(self._show_instructions)
        comm_btns.addWidget(btn_faq)
        c_layout.addLayout(comm_btns)
        layout.addWidget(comm_card)

        # 4. About & Legal Card
        about_card = QFrame(container)
        about_card.setProperty("class", "card")
        a_layout = QVBoxLayout(about_card)
        a_layout.setContentsMargins(18, 16, 18, 16)
        a_layout.setSpacing(8)

        a_title = QLabel("About PLAYFy TV Desktop", about_card)
        a_title.setStyleSheet("font-size: 15px; font-weight: bold; color: white;")
        a_layout.addWidget(a_title)

        info_lbl = QLabel(
            "Version: 1.7.0 (Clean-Room Desktop Edition)\n"
            "Backend CDN: https://vorasp.online/\n"
            "Engine: Qt 6 Multimedia / DirectShow Hardware Acceleration\n"
            "Clean-Room Protocol Specification: CLONE_SPEC.md",
            about_card
        )
        info_lbl.setStyleSheet("color: #888888; font-size: 12px; line-height: 1.5;")
        a_layout.addWidget(info_lbl)
        layout.addWidget(about_card)

        layout.addStretch()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _on_play_direct(self):
        url = self.stream_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a stream URL.")
            return
        title = "Direct Network Stream"
        self.play_direct_stream.emit(title, url)

    def _on_force_low_changed(self, state):
        self.force_low = (state == Qt.Checked)

    def _refresh_remote_config(self):
        entries = self.api_client.fetch_remote_config()
        QMessageBox.information(
            self, "Remote Config",
            f"Successfully updated configuration!\n\nBase URL: {entries.get('baseUrl')}\nLora Alphabet: {entries.get('lora', '')[:20]}..."
        )

    def _show_instructions(self):
        QMessageBox.information(
            self, "Instructions",
            "PLAYFy TV Desktop Guide:\n\n"
            "1. Live Sports: Watch live tournaments and games sorted by league and status.\n"
            "2. Channels: Browse TV channels by category with stream format selection.\n"
            "3. Highlights: Catch up on match replays and summaries.\n"
            "4. M3U Playlists: Import custom IPTV files or URLs and stream seamlessly.\n"
            "5. Bookmarks: Click the star icon to save any channel or stream to local favorites."
        )
