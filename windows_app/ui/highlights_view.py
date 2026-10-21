"""
PLAYFy TV Highlights & Replays Screen (kd.x, kd.u)
Displays match replay packages, video highlights, and full game summaries.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QButtonGroup
)
from PySide6.QtCore import Qt, Signal

class HighlightsView(QWidget):
    stream_selected = Signal(str, list)

    def __init__(self, api_client, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.api_client = api_client
        self.highlights_data: Dict[str, Any] = {}
        self.active_cat = "All"

        self._setup_ui()
        self.refresh_highlights()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header Title
        header = QHBoxLayout()
        title_lbl = QLabel(" Match Highlights & Replays", self)
        title_lbl.setProperty("class", "heading")
        header.addWidget(title_lbl)
        header.addStretch()

        self.btn_refresh = QPushButton("⟳ Refresh", self)
        self.btn_refresh.setProperty("class", "primary-btn")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_highlights)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        # Category Chips
        self.cat_scroll = QScrollArea(self)
        self.cat_scroll.setFixedHeight(48)
        self.cat_scroll.setWidgetResizable(True)
        self.cat_widget = QWidget()
        self.cat_layout = QHBoxLayout(self.cat_widget)
        self.cat_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_layout.setSpacing(8)
        self.cat_scroll.setWidget(self.cat_widget)
        layout.addWidget(self.cat_scroll)

        # Highlights Grid
        self.cards_scroll = QScrollArea(self)
        self.cards_scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setSpacing(16)
        self.cards_scroll.setWidget(self.cards_container)
        layout.addWidget(self.cards_scroll, stretch=1)

    def refresh_highlights(self):
        self.highlights_data = self.api_client.get_highlights()
        self._populate_category_chips()
        self._render_cards()

    def _populate_category_chips(self):
        while self.cat_layout.count() > 0:
            item = self.cat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.cat_group = QButtonGroup(self)
        self.cat_group.setExclusive(True)

        all_btn = QPushButton("All Highlights", self.cat_widget)
        all_btn.setCheckable(True)
        all_btn.setChecked(True)
        all_btn.setProperty("class", "chip")
        all_btn.setCursor(Qt.PointingHandCursor)
        self.cat_group.addButton(all_btn)
        self.cat_layout.addWidget(all_btn)
        all_btn.clicked.connect(lambda: self._on_cat_changed("All"))

        cats = self.highlights_data.get("cats", [])
        for c in cats:
            title = c.get("title", "")
            btn = QPushButton(title, self.cat_widget)
            btn.setCheckable(True)
            btn.setProperty("class", "chip")
            btn.setCursor(Qt.PointingHandCursor)
            self.cat_group.addButton(btn)
            self.cat_layout.addWidget(btn)
            btn.clicked.connect(lambda checked=False, t=title: self._on_cat_changed(t))

        self.cat_layout.addStretch()

    def _on_cat_changed(self, cat: str):
        self.active_cat = cat
        self._render_cards()

    def _render_cards(self):
        while self.cards_grid.count() > 0:
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        channels = self.highlights_data.get("channels", [])
        filtered = [
            c for c in channels
            if self.active_cat == "All" or c.get("category", "") == self.active_cat
        ]

        if not filtered:
            empty = QLabel("No highlight videos found in this category.", self.cards_container)
            empty.setStyleSheet("color: #777777; font-size: 14px; margin: 30px;")
            empty.setAlignment(Qt.AlignCenter)
            self.cards_grid.addWidget(empty, 0, 0, 1, 2)
            return

        row, col = 0, 0
        for ch in filtered:
            card = self._create_card(ch)
            self.cards_grid.addWidget(card, row, col)
            col += 1
            if col >= 2:
                col = 0
                row += 1

    def _create_card(self, channel: Dict[str, Any]) -> QFrame:
        card = QFrame(self.cards_container)
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        title = channel.get("title", "Match Highlights")
        category = channel.get("category", "Highlights")
        ev_info = channel.get("eventInfo", {})
        competition = ev_info.get("eventName", category)
        formats = channel.get("formats", [])

        # Header
        top_layout = QHBoxLayout()
        comp_lbl = QLabel(f" {competition}", card)
        comp_lbl.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 13px;")
        top_layout.addWidget(comp_lbl)
        top_layout.addStretch()

        badge = QLabel("HD REPLAY", card)
        badge.setStyleSheet("background-color: #2D2D2D; color: #00FF88; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;")
        top_layout.addWidget(badge)
        card_layout.addLayout(top_layout)

        # Title
        title_lbl = QLabel(title, card)
        title_lbl.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: 600;")
        title_lbl.setWordWrap(True)
        card_layout.addWidget(title_lbl)

        # Play Button
        if formats:
            btn_play = QPushButton("▶ Watch Highlights", card)
            btn_play.setProperty("class", "primary-btn")
            btn_play.setCursor(Qt.PointingHandCursor)
            btn_play.clicked.connect(lambda checked=False, t=title, f_list=formats: self.stream_selected.emit(t, f_list))
            card_layout.addWidget(btn_play)

        return card
