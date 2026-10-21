"""
PLAYFy TV M3U Playlists Management Screen (hd.g, kd.h0)
Handles importing, managing, and streaming custom M3U/M3U8 playlists and IPTV channels.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QLineEdit, QFileDialog,
    QDialog, QDialogButtonBox, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, Signal
from m3u_parser import M3UParser

class AddPlaylistDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import M3U Playlist")
        self.setFixedWidth(460)
        self.setStyleSheet("""
            QDialog { background-color: #1E1E1E; color: white; }
            QLabel { color: #DDDDDD; font-size: 13px; }
            QLineEdit { background-color: #282828; color: white; border: 1px solid #444; padding: 8px; border-radius: 4px; }
            QPushButton { background-color: #0078D4; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #106EBE; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        layout.addWidget(QLabel("Playlist Title:"))
        self.title_input = QLineEdit(self)
        self.title_input.setPlaceholderText("e.g. My Sports IPTV")
        layout.addWidget(self.title_input)

        layout.addWidget(QLabel("Playlist URL or Local Path:"))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(self)
        self.path_input.setPlaceholderText("https://example.com/playlist.m3u or C:/path/file.m3u")
        path_layout.addWidget(self.path_input)

        self.btn_browse = QPushButton("Browse...", self)
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._browse_local_file)
        path_layout.addWidget(self.btn_browse)
        layout.addLayout(path_layout)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setStyleSheet("background-color: #444444;")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Import", self)
        self.btn_save.clicked.connect(self._on_save)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def _browse_local_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select M3U Playlist File", "", "M3U Files (*.m3u *.m3u8);;All Files (*)")
        if filename:
            self.path_input.setText(filename)
            if not self.title_input.text():
                basename = filename.split('/')[-1].split('\\')[-1].rsplit('.', 1)[0]
                self.title_input.setText(basename)

    def _on_save(self):
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Validation", "Please enter a playlist title.")
            return
        if not self.path_input.text().strip():
            QMessageBox.warning(self, "Validation", "Please enter an M3U URL or local file path.")
            return
        self.accept()

    def get_data(self):
        return self.title_input.text().strip(), self.path_input.text().strip()


class PlaylistsView(QWidget):
    stream_selected = Signal(str, list)

    def __init__(self, db, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db
        self.playlists: List[Dict[str, Any]] = []
        self.active_playlist_id: Optional[int] = None
        self.loaded_channels: List[Dict[str, Any]] = []

        self._setup_ui()
        self.refresh_playlists()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Top Bar
        header = QHBoxLayout()
        title_lbl = QLabel(" M3U Playlists & IPTV Sources", self)
        title_lbl.setProperty("class", "heading")
        header.addWidget(title_lbl)
        header.addStretch()

        self.btn_add = QPushButton(" Add Playlist", self)
        self.btn_add.setProperty("class", "primary-btn")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self._add_playlist_dialog)
        header.addWidget(self.btn_add)
        layout.addLayout(header)

        # Splitter: Left Sidebar (Playlists List) & Right Content (Channels in Playlist)
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setStyleSheet("QSplitter::handle { background: #282828; width: 2px; }")

        # 1. Left Panel: Playlists
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(8)

        left_layout.addWidget(QLabel("Imported Playlists:", left_widget))
        self.pl_scroll = QScrollArea(left_widget)
        self.pl_scroll.setWidgetResizable(True)
        self.pl_container = QWidget()
        self.pl_list_layout = QVBoxLayout(self.pl_container)
        self.pl_list_layout.setContentsMargins(0, 0, 0, 0)
        self.pl_list_layout.setSpacing(8)
        self.pl_scroll.setWidget(self.pl_container)
        left_layout.addWidget(self.pl_scroll, stretch=1)
        self.splitter.addWidget(left_widget)

        # 2. Right Panel: Channels in Selected Playlist
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)

        chan_header = QHBoxLayout()
        self.active_pl_lbl = QLabel("Select a playlist to view channels", right_widget)
        self.active_pl_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        chan_header.addWidget(self.active_pl_lbl)
        chan_header.addStretch()

        self.search_chan = QLineEdit(right_widget)
        self.search_chan.setPlaceholderText(" Filter channels...")
        self.search_chan.setFixedWidth(200)
        self.search_chan.textChanged.connect(self._filter_channels)
        chan_header.addWidget(self.search_chan)
        right_layout.addLayout(chan_header)

        self.chan_scroll = QScrollArea(right_widget)
        self.chan_scroll.setWidgetResizable(True)
        self.chan_container = QWidget()
        self.chan_grid = QGridLayout(self.chan_container)
        self.chan_grid.setContentsMargins(0, 0, 0, 0)
        self.chan_grid.setSpacing(12)
        self.chan_scroll.setWidget(self.chan_container)
        right_layout.addWidget(self.chan_scroll, stretch=1)

        self.splitter.addWidget(right_widget)
        self.splitter.setSizes([260, 700])
        layout.addWidget(self.splitter, stretch=1)

    def refresh_playlists(self):
        self.playlists = self.db.get_playlists()
        self._render_playlists_sidebar()

    def _render_playlists_sidebar(self):
        while self.pl_list_layout.count() > 0:
            item = self.pl_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.playlists:
            empty = QLabel("No playlists added yet.\nClick 'Add Playlist' above to import an M3U file or URL.", self.pl_container)
            empty.setStyleSheet("color: #777; font-size: 12px; margin: 20px 4px;")
            self.pl_list_layout.addWidget(empty)
            self.pl_list_layout.addStretch()
            return

        for pl in self.playlists:
            pl_id = pl["id"]
            title = pl["title"]
            path = pl["path"]

            card = QFrame(self.pl_container)
            card.setProperty("class", "card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(6)

            h_layout = QHBoxLayout()
            lbl = QLabel(f" {title}", card)
            lbl.setStyleSheet("color: white; font-weight: bold;")
            h_layout.addWidget(lbl, stretch=1)

            btn_del = QPushButton("", card)
            btn_del.setFixedSize(26, 26)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setStyleSheet("background-color: transparent; border: none; color: #888;")
            btn_del.clicked.connect(lambda checked=False, pid=pl_id: self._delete_playlist(pid))
            h_layout.addWidget(btn_del)
            card_layout.addLayout(h_layout)

            btn_view = QPushButton("Open Playlist", card)
            btn_view.setProperty("class", "primary-btn")
            btn_view.setCursor(Qt.PointingHandCursor)
            btn_view.clicked.connect(lambda checked=False, p=pl: self.load_playlist_channels(p))
            card_layout.addWidget(btn_view)

            self.pl_list_layout.addWidget(card)

        self.pl_list_layout.addStretch()

    def _add_playlist_dialog(self):
        dialog = AddPlaylistDialog(self)
        if dialog.exec() == QDialog.Accepted:
            title, path = dialog.get_data()
            self.db.add_playlist(title, path)
            self.refresh_playlists()

    def _delete_playlist(self, pl_id: int):
        reply = QMessageBox.question(self, "Delete Playlist", "Are you sure you want to remove this playlist?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.delete_playlist(pl_id)
            self.refresh_playlists()

    def load_playlist_channels(self, pl: Dict[str, Any]):
        self.active_playlist_id = pl["id"]
        title = pl["title"]
        path = pl["path"]
        self.active_pl_lbl.setText(f"Loading {title}...")

        try:
            items = M3UParser.load_from_source(path)
            self.loaded_channels = items
            self.active_pl_lbl.setText(f" {title} ({len(items)} channels)")
            self._render_channel_grid(self.loaded_channels)
        except Exception as e:
            self.active_pl_lbl.setText(f"Error loading {title}")
            QMessageBox.critical(self, "M3U Parse Error", f"Failed to load playlist: {e}")

    def _filter_channels(self, query: str):
        q = query.strip().lower()
        if not q:
            self._render_channel_grid(self.loaded_channels)
            return
        filtered = [
            ch for ch in self.loaded_channels
            if q in ch.get("name", "").lower() or q in ch.get("groupTitle", "").lower()
        ]
        self._render_channel_grid(filtered)

    def _render_channel_grid(self, items: List[Dict[str, Any]]):
        while self.chan_grid.count() > 0:
            item = self.chan_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not items:
            lbl = QLabel("No channels found.", self.chan_container)
            lbl.setStyleSheet("color: #777; margin: 30px;")
            self.chan_grid.addWidget(lbl, 0, 0)
            return

        row, col = 0, 0
        for ch in items[:200]:  # page limit for performance
            card = self._create_m3u_channel_card(ch)
            self.chan_grid.addWidget(card, row, col)
            col += 1
            if col >= 2:
                col = 0
                row += 1

    def _create_m3u_channel_card(self, item: Dict[str, Any]) -> QFrame:
        card = QFrame(self.chan_container)
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        name = item.get("name", "IPTV Stream")
        group = item.get("groupTitle", "General")
        link = item.get("link", "")

        header = QHBoxLayout()
        grp_lbl = QLabel(f" {group}", card)
        grp_lbl.setStyleSheet("color: #0078D4; font-size: 11px; font-weight: bold;")
        header.addWidget(grp_lbl)
        header.addStretch()

        is_fav = self.db.is_playlist_fav(link)
        fav_btn = QPushButton("" if is_fav else "", card)
        fav_btn.setFixedSize(24, 24)
        fav_btn.setCursor(Qt.PointingHandCursor)
        fav_btn.setStyleSheet(f"background-color: transparent; border: none; font-size: 16px; color: {'#FFD700' if is_fav else '#888'};")
        fav_btn.clicked.connect(lambda: self._toggle_m3u_fav(item, fav_btn))
        header.addWidget(fav_btn)
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

    def _toggle_m3u_fav(self, item: Dict[str, Any], btn: QPushButton):
        link = item.get("link", "")
        if self.db.is_playlist_fav(link):
            self.db.remove_playlist_fav(link)
            btn.setText("")
            btn.setStyleSheet("background-color: transparent; border: none; font-size: 16px; color: #888;")
        else:
            self.db.add_playlist_fav(item)
            btn.setText("")
            btn.setStyleSheet("background-color: transparent; border: none; font-size: 16px; color: #FFD700;")
