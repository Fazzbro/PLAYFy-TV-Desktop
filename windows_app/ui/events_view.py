"""
PLAYFy TV Live Sports & Events Screen (kd.x, kd.u, kd.a0)
Implements clean-room reverse-engineered match state machine (p.q3 / gd.m),
time filters (od.s.k), category filtering, real-time 1s countdown/elapsed timers,
pinned match prioritization, ErrorLyBinding retry handling, and
DialogMultiStreamBinding multi-stream selection.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QButtonGroup, QGridLayout, QSizePolicy,
    QDialog, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QTimer


def parse_match_time(time_str: str) -> Optional[datetime]:
    """
    Parses 'yyyy/MM/dd HH:mm:ss Z' (e.g. '2026/10/21 03:00:00 +0000') into UTC datetime.
    Evidence: gd.m and SimpleDateFormat in p.q3.
    """
    if not time_str or not isinstance(time_str, str):
        return None
    try:
        # Match standard APK format: 2026/10/21 03:00:00 +0000
        clean_str = time_str.strip()
        return datetime.strptime(clean_str, "%Y/%m/%d %H:%M:%S %z").astimezone(timezone.utc)
    except Exception:
        pass
    try:
        # Fallback ISO formats
        return datetime.fromisoformat(time_str.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def format_duration(seconds: int) -> str:
    """
    Matches p.q3.b duration formatter:
    If seconds >= 3600: HH:MM:SS, else MM:SS.
    """
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def calculate_match_status(start_dt: Optional[datetime], end_dt: Optional[datetime], now_dt: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Evaluates real-time match state machine recovered from gd.m and p.q3:
    1. LIVE: start_dt <= now < end_dt
    2. STARTING_SOON: 0 < start_dt - now <= 2 hours (7200s)
    3. UPCOMING: start_dt - now > 2 hours
    4. ENDED: now >= end_dt
    """
    if now_dt is None:
        now_dt = datetime.now(timezone.utc)

    if not start_dt:
        return {
            "state": "UPCOMING",
            "badge_text": " Scheduled",
            "badge_color": "#0078D4",
            "timer_active": False,
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
            "badge_text": f" LIVE {format_duration(elapsed)}",
            "badge_color": "#E81123",
            "timer_active": True,
            "seconds_left": int(end_ts - now_ts),
            "elapsed_seconds": elapsed
        }

    diff_start = start_ts - now_ts

    # 2. STARTING SOON (within 2 hours)
    if 0 < diff_start <= 7200:
        return {
            "state": "STARTING_SOON",
            "badge_text": f"⏳ Starts in {format_duration(int(diff_start))}",
            "badge_color": "#D83B01",
            "timer_active": True,
            "seconds_left": int(diff_start),
            "elapsed_seconds": 0
        }

    # 3. UPCOMING (more than 2 hours away)
    if diff_start > 7200:
        kickoff_str = start_dt.strftime("%d/%m %H:%M UTC")
        return {
            "state": "UPCOMING",
            "badge_text": f" {kickoff_str}",
            "badge_color": "#0078D4",
            "timer_active": False,
            "seconds_left": int(diff_start),
            "elapsed_seconds": 0
        }

    # 4. ENDED
    return {
        "state": "ENDED",
        "badge_text": " Full Time",
        "badge_color": "#555555",
        "timer_active": False,
        "seconds_left": 0,
        "elapsed_seconds": 0
    }


def classify_format_quality(format_title: str) -> str:
    """
    Extracts quality badge string (FHD, HD, SD) from format string.
    Recovered from gd.p.j server badge rendering.
    """
    ft_upper = (format_title or "").upper()
    if "FHD" in ft_upper or "1080" in ft_upper or "4K" in ft_upper:
        return "FHD"
    elif "HD" in ft_upper or "720" in ft_upper:
        return "HD"
    return "SD"


class MultiStreamDialog(QDialog):
    """
    Modal multi-stream selection dialog recovered from DialogMultiStreamBinding (gd.p.j).
    Displays when a live sports event has 2 or more streaming sources.
    """
    def __init__(self, parent: QWidget, match_title: str, league: str, formats: List[Dict[str, Any]], on_select_format):
        super().__init__(parent)
        self.match_title = match_title
        self.league = league
        self.formats = formats
        self.on_select_format = on_select_format

        self.setWindowTitle(f"Select Stream - {match_title}")
        self.setFixedWidth(460)
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1A1A;
                border: 1px solid #333333;
                border-radius: 10px;
            }
            QLabel { color: #FFFFFF; font-family: 'Segoe UI', sans-serif; }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header Title
        title_lbl = QLabel(self.match_title, self)
        title_lbl.setStyleSheet("font-size: 17px; font-weight: bold; color: #FFFFFF;")
        title_lbl.setWordWrap(True)
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)

        league_lbl = QLabel(f" {self.league}", self)
        league_lbl.setStyleSheet("font-size: 13px; color: #0078D4; font-weight: 600;")
        league_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(league_lbl)

        sub_desc = QLabel(f"Available Broadcast Servers ({len(self.formats)} Options):", self)
        sub_desc.setStyleSheet("font-size: 12px; color: #AAAAAA; margin-top: 4px;")
        layout.addWidget(sub_desc)

        # Server List Scroll Area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setFixedHeight(220)

        container = QWidget()
        list_layout = QVBoxLayout(container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(10)

        for i, fmt in enumerate(self.formats):
            fmt_dict = fmt if isinstance(fmt, dict) else {"title": str(fmt), "link": str(fmt)}
            raw_title = fmt_dict.get("title") or f"Server {i+1}"
            quality = classify_format_quality(raw_title)

            # Button frame
            btn_frame = QFrame(container)
            btn_frame.setStyleSheet("""
                QFrame {
                    background-color: #242424;
                    border: 1px solid #3A3A3A;
                    border-radius: 8px;
                    padding: 4px;
                }
                QFrame:hover {
                    background-color: #2E2E2E;
                    border: 1px solid #0078D4;
                }
            """)
            btn_layout = QHBoxLayout(btn_frame)
            btn_layout.setContentsMargins(12, 10, 12, 10)

            # Quality Pill
            pill_color = "#0078D4" if quality == "FHD" else ("#107C41" if quality == "HD" else "#555555")
            badge = QLabel(quality, btn_frame)
            badge.setStyleSheet(f"""
                background-color: {pill_color}; color: #FFFFFF; font-weight: bold;
                font-size: 10px; border-radius: 4px; padding: 3px 7px;
            """)
            btn_layout.addWidget(badge)

            # Title
            name_lbl = QLabel(raw_title, btn_frame)
            name_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")
            btn_layout.addWidget(name_lbl, stretch=1)

            # Play Icon Button
            play_btn = QPushButton("▶ Watch", btn_frame)
            play_btn.setCursor(Qt.PointingHandCursor)
            play_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078D4; color: white; border: none;
                    padding: 6px 14px; border-radius: 5px; font-weight: bold; font-size: 12px;
                }
                QPushButton:hover { background-color: #106EBE; }
            """)
            play_btn.clicked.connect(lambda checked=False, idx=i: self._select_server(idx))
            btn_layout.addWidget(play_btn)

            list_layout.addWidget(btn_frame)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Cancel / Close
        btn_close = QPushButton("Cancel", self)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #333333; color: #CCCCCC; border: 1px solid #444444;
                padding: 8px 16px; border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background-color: #444444; color: #FFFFFF; }
        """)
        btn_close.clicked.connect(self.reject)
        layout.addWidget(btn_close)

    def _select_server(self, index: int):
        # Prioritize selected format first, keeping remaining formats for fallback
        selected = self.formats[index]
        reordered = [selected] + [f for i, f in enumerate(self.formats) if i != index]
        self.on_select_format(self.match_title, reordered)
        self.accept()


class LiveEventCard(QFrame):
    """
    Card UI matching gd.m layout:
    - Tournament banner + isPinned golden badge
    - Team A (name & icon) vs Team B (name & icon)
    - Dynamic countdown / live elapsed badge
    - Single or Multi-stream launch button
    """
    def __init__(self, channel: Dict[str, Any], on_stream_req, on_multi_stream_req, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.channel = channel
        self.on_stream_req = on_stream_req
        self.on_multi_stream_req = on_multi_stream_req

        self.ev_info = channel.get("eventInfo", {})
        self.start_dt = parse_match_time(self.ev_info.get("startTime", ""))
        self.end_dt = parse_match_time(self.ev_info.get("endTime", ""))

        self.setProperty("class", "card")
        self._setup_ui()
        self.update_live_timer()

    def _setup_ui(self):
        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        league = self.ev_info.get("eventName") or self.channel.get("category", "Live Match")
        team_a = self.ev_info.get("teamA") or self.channel.get("title", "Team A")
        team_b = self.ev_info.get("teamB") or "Team B"
        is_pinned = int(self.ev_info.get("isPinned", 0)) == 1

        # Header Row: League + Pinned Badge
        header_layout = QHBoxLayout()
        league_lbl = QLabel(f" {league}", self)
        league_lbl.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 13px;")
        header_layout.addWidget(league_lbl)
        header_layout.addStretch()

        if is_pinned:
            pinned_lbl = QLabel(" PINNED", self)
            pinned_lbl.setStyleSheet("""
                background-color: #FFB900; color: #000000; font-weight: 900;
                font-size: 10px; border-radius: 4px; padding: 2px 6px;
            """)
            header_layout.addWidget(pinned_lbl)

        card_layout.addLayout(header_layout)

        # Match Title & Teams Matchup Row
        matchup_layout = QHBoxLayout()
        matchup_layout.setSpacing(12)

        # Team A
        team_a_layout = QVBoxLayout()
        team_a_layout.setAlignment(Qt.AlignCenter)
        icon_a = QLabel("️", self)
        icon_a.setStyleSheet("font-size: 24px;")
        icon_a.setAlignment(Qt.AlignCenter)
        name_a = QLabel(team_a, self)
        name_a.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 15px;")
        name_a.setAlignment(Qt.AlignCenter)
        name_a.setWordWrap(True)
        team_a_layout.addWidget(icon_a)
        team_a_layout.addWidget(name_a)
        matchup_layout.addLayout(team_a_layout, stretch=1)

        # Center Status & VS
        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignCenter)
        self.badge_lbl = QLabel(" LIVE", self)
        self.badge_lbl.setAlignment(Qt.AlignCenter)
        self.badge_lbl.setStyleSheet("""
            background-color: #E81123; color: white; font-weight: bold;
            font-size: 11px; border-radius: 4px; padding: 4px 8px;
        """)
        vs_lbl = QLabel("VS", self)
        vs_lbl.setStyleSheet("color: #777777; font-size: 13px; font-weight: 900; margin-top: 4px;")
        vs_lbl.setAlignment(Qt.AlignCenter)
        center_layout.addWidget(self.badge_lbl)
        center_layout.addWidget(vs_lbl)
        matchup_layout.addLayout(center_layout)

        # Team B
        team_b_layout = QVBoxLayout()
        team_b_layout.setAlignment(Qt.AlignCenter)
        icon_b = QLabel("️", self)
        icon_b.setStyleSheet("font-size: 24px;")
        icon_b.setAlignment(Qt.AlignCenter)
        name_b = QLabel(team_b, self)
        name_b.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 15px;")
        name_b.setAlignment(Qt.AlignCenter)
        name_b.setWordWrap(True)
        team_b_layout.addWidget(icon_b)
        team_b_layout.addWidget(name_b)
        matchup_layout.addLayout(team_b_layout, stretch=1)

        card_layout.addLayout(matchup_layout)

        # Stream Action Button Row
        formats = self.channel.get("formats", [])
        action_layout = QHBoxLayout()
        match_title_full = f"{team_a} vs {team_b}"

        if not formats:
            lbl_no_fmt = QLabel("Stream starting soon", self)
            lbl_no_fmt.setStyleSheet("color: #888888; font-style: italic; font-size: 12px;")
            action_layout.addWidget(lbl_no_fmt)
        else:
            btn_label = f"▶ Watch Match ({len(formats)} Streams)" if len(formats) > 1 else "▶ Watch Live Stream"
            btn_play = QPushButton(btn_label, self)
            btn_play.setProperty("class", "primary-btn")
            btn_play.setCursor(Qt.PointingHandCursor)
            btn_play.clicked.connect(lambda: self.on_stream_req(self.channel, match_title_full, league))
            action_layout.addWidget(btn_play, stretch=1)

        card_layout.addLayout(action_layout)

    def update_live_timer(self):
        """
        Updates dynamic countdown or elapsed timer every 1 second.
        """
        status_info = calculate_match_status(self.start_dt, self.end_dt)
        self.badge_lbl.setText(status_info["badge_text"])
        self.badge_lbl.setStyleSheet(f"""
            background-color: {status_info['badge_color']}; color: white; font-weight: bold;
            font-size: 11px; border-radius: 4px; padding: 4px 8px;
        """)
        return status_info["timer_active"]


class EventsView(QWidget):
    stream_selected = Signal(str, list)  # title, formats

    def __init__(self, api_client, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.api_client = api_client
        self.events_data: Dict[str, Any] = {}
        self.active_timeline_filter = "All"
        self.active_cat_filter = "All"
        self.search_query = ""
        self.active_cards: List[LiveEventCard] = []

        self._setup_ui()

        # 1-second refresh timer for live countdown / match clocks (p.q3 / gd.m)
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self._on_tick)
        self.tick_timer.start()

        self.refresh_events()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Title Bar & Search
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_label = QLabel(" Live Sports & Football", self)
        title_label.setProperty("class", "heading")
        self.subtitle_label = QLabel("Real-time sports events with multi-server broadcasts", self)
        self.subtitle_label.setProperty("class", "subheading")
        title_box.addWidget(title_label)
        title_box.addWidget(self.subtitle_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Search Bar
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText(" Search teams or leagues...")
        self.search_input.setFixedWidth(220)
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input)

        # Refresh Button
        self.btn_refresh = QPushButton("⟳ Refresh", self)
        self.btn_refresh.setProperty("class", "primary-btn")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_events)
        header_layout.addWidget(self.btn_refresh)
        layout.addLayout(header_layout)

        # Sub-timeline Filter Bar (od.s.k: Tab 0=All, Tab 1=Live Now, Tab 2=Today, Tab 3=Upcoming, Tab 4=Finished)
        timeline_bar = QHBoxLayout()
        timeline_bar.setSpacing(8)
        self.timeline_group = QButtonGroup(self)
        self.timeline_group.setExclusive(True)

        for filter_name in ["All", " Live Now", " Today", "⏳ Upcoming", " Finished"]:
            btn = QPushButton(filter_name, self)
            btn.setCheckable(True)
            btn.setProperty("class", "chip")
            btn.setCursor(Qt.PointingHandCursor)
            if filter_name == "All":
                btn.setChecked(True)
            self.timeline_group.addButton(btn)
            timeline_bar.addWidget(btn)
            btn.clicked.connect(lambda checked=False, f=filter_name: self._on_timeline_changed(f))

        timeline_bar.addStretch()
        layout.addLayout(timeline_bar)

        # Category Filter Horizontal Scroll (cats)
        self.cat_scroll = QScrollArea(self)
        self.cat_scroll.setFixedHeight(48)
        self.cat_scroll.setWidgetResizable(True)
        self.cat_widget = QWidget()
        self.cat_layout = QHBoxLayout(self.cat_widget)
        self.cat_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_layout.setSpacing(8)
        self.cat_scroll.setWidget(self.cat_widget)
        layout.addWidget(self.cat_scroll)

        # Error / Retry Container (ErrorLyBinding)
        self.error_frame = QFrame(self)
        self.error_frame.setStyleSheet("background-color: #2D1A1A; border: 1px solid #772222; border-radius: 8px; padding: 20px;")
        error_layout = QVBoxLayout(self.error_frame)
        error_layout.setAlignment(Qt.AlignCenter)
        self.error_msg = QLabel("️ Unable to load live sports events. Please check your network connection.", self.error_frame)
        self.error_msg.setStyleSheet("color: #FF8888; font-size: 14px; font-weight: bold;")
        self.error_msg.setAlignment(Qt.AlignCenter)
        self.btn_retry = QPushButton("↻ Tap to Retry", self.error_frame)
        self.btn_retry.setProperty("class", "primary-btn")
        self.btn_retry.setCursor(Qt.PointingHandCursor)
        self.btn_retry.clicked.connect(self.refresh_events)
        error_layout.addWidget(self.error_msg)
        error_layout.addWidget(self.btn_retry, alignment=Qt.AlignCenter)
        self.error_frame.hide()
        layout.addWidget(self.error_frame)

        # Cards Scroll Area
        self.cards_scroll = QScrollArea(self)
        self.cards_scroll.setWidgetResizable(True)
        self.cards_container = QWidget()
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setSpacing(16)
        self.cards_scroll.setWidget(self.cards_container)
        layout.addWidget(self.cards_scroll, stretch=1)

    def refresh_events(self):
        """
        Triggers data fetch from API Client matching SwipeRefreshLayout & ErrorLyBinding retry.
        Strictly limits sports to Cricket and Football.
        """
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("Fetching...")

        data = self.api_client.get_live_events()
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("⟳ Refresh")

        raw_channels = data.get("channels", []) if isinstance(data, dict) else []
        if not raw_channels:
            self.error_frame.show()
            self.cards_scroll.hide()
            return

        # STRICT REQUIREMENT: Only retain Cricket and Football events (purge all other sports)
        ALLOWED_CATEGORIES = {"Football", "Cricket"}
        channels = [ch for ch in raw_channels if ch.get("category") in ALLOWED_CATEGORIES]
        data["channels"] = channels

        self.error_frame.hide()
        self.cards_scroll.show()
        self.events_data = data

        football_count = sum(1 for ch in channels if ch.get("category") == "Football")
        cricket_count = sum(1 for ch in channels if ch.get("category") == "Cricket")
        self.subtitle_label.setText(
            f"{len(channels)} Live Sports Events ({football_count} Football • {cricket_count} Cricket) • Live Multi-Server HLS Feeds"
        )

        self._populate_category_chips()
        self._render_event_cards()

    def _populate_category_chips(self):
        while self.cat_layout.count() > 0:
            item = self.cat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.cat_group = QButtonGroup(self)
        self.cat_group.setExclusive(True)

        channels = self.events_data.get("channels", [])
        football_count = sum(1 for ch in channels if ch.get("category") == "Football")
        cricket_count = sum(1 for ch in channels if ch.get("category") == "Cricket")
        total_count = len(channels)

        # 1. All (Football & Cricket)
        all_btn = QPushButton(f"All ({total_count})", self.cat_widget)
        all_btn.setCheckable(True)
        all_btn.setChecked(self.active_cat_filter == "All")
        all_btn.setProperty("class", "chip")
        all_btn.setCursor(Qt.PointingHandCursor)
        self.cat_group.addButton(all_btn)
        self.cat_layout.addWidget(all_btn)
        all_btn.clicked.connect(lambda: self._on_cat_changed("All"))

        # 2.  Football
        fb_btn = QPushButton(f" Football ({football_count})", self.cat_widget)
        fb_btn.setCheckable(True)
        fb_btn.setChecked(self.active_cat_filter == "Football")
        fb_btn.setProperty("class", "chip")
        fb_btn.setCursor(Qt.PointingHandCursor)
        self.cat_group.addButton(fb_btn)
        self.cat_layout.addWidget(fb_btn)
        fb_btn.clicked.connect(lambda: self._on_cat_changed("Football"))

        # 3.  Cricket
        cr_btn = QPushButton(f" Cricket ({cricket_count})", self.cat_widget)
        cr_btn.setCheckable(True)
        cr_btn.setChecked(self.active_cat_filter == "Cricket")
        cr_btn.setProperty("class", "chip")
        cr_btn.setCursor(Qt.PointingHandCursor)
        self.cat_group.addButton(cr_btn)
        self.cat_layout.addWidget(cr_btn)
        cr_btn.clicked.connect(lambda: self._on_cat_changed("Cricket"))

        self.cat_layout.addStretch()

    def _on_timeline_changed(self, timeline: str):
        self.active_timeline_filter = timeline
        self._render_event_cards()

    def _on_cat_changed(self, cat: str):
        self.active_cat_filter = cat
        self._render_event_cards()

    def _on_search_changed(self, query: str):
        self.search_query = query.strip().lower()
        self._render_event_cards()

    def _on_tick(self):
        """
        Periodic 1-second pulse: updates card countdowns and live elapsed clocks.
        """
        for card in self.active_cards:
            try:
                card.update_live_timer()
            except Exception:
                pass

    def _render_event_cards(self):
        # Clear existing cards
        self.active_cards.clear()
        while self.cards_grid.count() > 0:
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        channels = self.events_data.get("channels", [])
        now_dt = datetime.now(timezone.utc)
        today_date = now_dt.date()

        filtered = []
        for ch in channels:
            ev_info = ch.get("eventInfo", {})
            cat = ch.get("category", "")

            # Category Filter
            if self.active_cat_filter != "All" and cat != self.active_cat_filter:
                continue

            # Search Query
            if self.search_query:
                t_a = (ev_info.get("teamA") or "").lower()
                t_b = (ev_info.get("teamB") or "").lower()
                league = (ev_info.get("eventName") or "").lower()
                ch_title = (ch.get("title") or "").lower()
                if self.search_query not in t_a and self.search_query not in t_b and self.search_query not in league and self.search_query not in ch_title:
                    continue

            # Parse Match Times & Evaluate Match State
            start_dt = parse_match_time(ev_info.get("startTime", ""))
            end_dt = parse_match_time(ev_info.get("endTime", ""))
            status_info = calculate_match_status(start_dt, end_dt, now_dt)
            state = status_info["state"]

            # Timeline Sub-filters (od.s.k)
            if self.active_timeline_filter == " Live Now":
                if state != "LIVE":
                    continue
            elif self.active_timeline_filter == " Today":
                # Matches occurring on the current UTC date
                if not start_dt or start_dt.date() != today_date:
                    continue
            elif self.active_timeline_filter == "⏳ Upcoming":
                if state not in ("STARTING_SOON", "UPCOMING"):
                    continue
            elif self.active_timeline_filter == " Finished":
                if state != "ENDED":
                    continue

            # Match state priority from APK bytecode (od.e & od.g(0)):
            # 2 = LIVE (startTime <= now <= endTime) -> Top Priority
            # 1 = UPCOMING / STARTING_SOON (now < startTime) -> Middle
            # 0 = ENDED / FINISHED (now > endTime) -> Bottom
            state_priority = 2 if state == "LIVE" else (1 if state in ("STARTING_SOON", "UPCOMING") else 0)

            filtered.append((ch, ev_info, start_dt, state_priority))

        # APK 3-Level Priority Sort (Evidence: od.e, od.g(0), od.h(..., 1), od.h(..., 0))
        # 1. State Priority (Descending: LIVE=2 > UPCOMING=1 > ENDED=0)
        # 2. Pinned Priority (Descending: isPinned=1 > isPinned=0)
        # 3. Start Time Delta (Ascending: earlier kickoffs first)
        def apk_sort_key(item):
            ch, ev, sdt, state_prio = item
            pinned = int(ev.get("isPinned", 0))
            ts = sdt.timestamp() if sdt else float('inf')
            return (-state_prio, -pinned, ts)

        filtered.sort(key=apk_sort_key)

        if not filtered:
            empty_lbl = QLabel(f"No events currently matching '{self.active_timeline_filter}' / '{self.active_cat_filter}'.", self.cards_container)
            empty_lbl.setStyleSheet("color: #888888; font-size: 15px; margin: 40px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.cards_grid.addWidget(empty_lbl, 0, 0, 1, 2)
            return

        row, col = 0, 0
        for ch, _, _, _ in filtered:
            card = LiveEventCard(
                channel=ch,
                on_stream_req=self._on_card_watch_clicked,
                on_multi_stream_req=self._open_multi_stream_dialog,
                parent=self.cards_container
            )
            self.active_cards.append(card)
            self.cards_grid.addWidget(card, row, col)
            col += 1
            if col >= 2:  # 2-column responsive layout
                col = 0
                row += 1

    def _on_card_watch_clicked(self, channel: Dict[str, Any], match_title: str, league: str):
        """
        Dynamically extracts live stream backlinks from 'channels/{id}.json' matching od.c0 & PlayerActivity.f0.
        Prioritizes direct HLS feeds (.m3u8) for immediate video rendering.
        """
        ch_id = channel.get("id")
        # Extract live stream backlinks from channels/{ch_id}.json
        real_streams = self.api_client.get_channel_stream_links(ch_id)
        if not real_streams:
            real_streams = [f for f in channel.get("formats", []) if isinstance(f, dict) and f.get("link")]
        if not real_streams:
            raw_fmts = channel.get("formats", [])
            real_streams = [{"title": f.get("title") if isinstance(f, dict) else str(f), "link": ""} for f in raw_fmts]

        # Prioritize direct .m3u8 feeds without DASH encryption at the top
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

        if len(real_streams) > 1:
            self._open_multi_stream_dialog(match_title, league, real_streams)
        elif len(real_streams) == 1:
            self._on_direct_stream(match_title, real_streams)

    def _on_direct_stream(self, title: str, formats: List[Dict[str, Any]]):
        self.stream_selected.emit(title, formats)

    def _open_multi_stream_dialog(self, title: str, league: str, formats: List[Dict[str, Any]]):
        dlg = MultiStreamDialog(self, title, league, formats, on_select_format=self._on_direct_stream)
        dlg.exec()
