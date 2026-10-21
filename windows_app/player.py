"""
PLAYFy TV Native Windows Video Player Engine
Uses Qt 6 QMediaPlayer, QAudioOutput, and QVideoWidget with native DirectShow / Media Foundation acceleration.
Features:
- Stream format switcher (kd.p0)
- Seekable scrub bar
- Volume & Mute control
- Fullscreen mode (F11 / Double-click)
- Status and buffer indicators
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel,
    QComboBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QUrl, QTime, Signal, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

class VideoPlayerWidget(QWidget):
    close_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.formats: List[Dict[str, Any]] = []
        self.current_format_idx: int = 0
        self.is_fullscreen_mode = False

        # 1. Media Player Setup
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)

        # 2. Video Surface
        self.video_widget = QVideoWidget(self)
        self.player.setVideoOutput(self.video_widget)

        # 3. UI Construction
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Top Bar (Title & Close)
        self.top_bar = QFrame(self)
        self.top_bar.setStyleSheet("background-color: rgba(20, 20, 20, 0.85); padding: 6px;")
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(12, 4, 12, 4)

        self.title_label = QLabel("PLAYFy TV Player", self.top_bar)
        self.title_label.setStyleSheet("color: #FFFFFF; font-size: 15px; font-weight: bold;")
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()

        self.btn_close = QPushButton(" Close", self.top_bar)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #E81123; color: white; border: none;
                padding: 6px 14px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #F1707A; }
        """)
        top_layout.addWidget(self.btn_close)
        self.main_layout.addWidget(self.top_bar)

        # Status / Error Banner (for fallback notifications matching PlayerActivity.D)
        self.status_banner = QLabel("", self)
        self.status_banner.setStyleSheet("""
            background-color: #D83B01; color: white; font-weight: bold;
            padding: 8px 16px; font-size: 13px; text-align: center;
        """)
        self.status_banner.setAlignment(Qt.AlignCenter)
        self.status_banner.hide()
        self.main_layout.addWidget(self.status_banner)

        # Video Output
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setStyleSheet("background-color: #000000;")
        self.main_layout.addWidget(self.video_widget, stretch=1)

        # Bottom Controls Bar
        self.control_bar = QFrame(self)
        self.control_bar.setStyleSheet("background-color: rgba(20, 20, 20, 0.95); padding: 8px;")
        control_layout = QVBoxLayout(self.control_bar)
        control_layout.setContentsMargins(12, 6, 12, 6)
        control_layout.setSpacing(6)

        # Seek Bar & Timers
        seek_layout = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00", self.control_bar)
        self.time_label.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        self.seek_slider = QSlider(Qt.Horizontal, self.control_bar)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #444; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #0078D4; border-radius: 2px; }
            QSlider::handle:horizontal { width: 12px; margin: -4px 0; background: #FFFFFF; border-radius: 6px; }
        """)
        seek_layout.addWidget(self.seek_slider, stretch=1)
        seek_layout.addWidget(self.time_label)
        control_layout.addLayout(seek_layout)

        # Action Buttons Row
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.btn_play_pause = QPushButton("▶ Play", self.control_bar)
        self.btn_play_pause.setFixedWidth(80)
        self.btn_play_pause.setCursor(Qt.PointingHandCursor)
        self.btn_play_pause.setStyleSheet("""
            QPushButton {
                background-color: #0078D4; color: white; border: none;
                padding: 6px 12px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #106EBE; }
        """)
        actions_layout.addWidget(self.btn_play_pause)

        # Stream Selector
        actions_layout.addWidget(QLabel("Source:", self.control_bar))
        self.combo_sources = QComboBox(self.control_bar)
        self.combo_sources.setMinimumWidth(180)
        self.combo_sources.setStyleSheet("""
            QComboBox {
                background-color: #2D2D2D; color: white; border: 1px solid #444;
                padding: 4px 8px; border-radius: 4px;
            }
            QComboBox QAbstractItemView { background-color: #252525; color: white; selection-background-color: #0078D4; }
        """)
        actions_layout.addWidget(self.combo_sources)

        actions_layout.addStretch()

        # Volume Slider
        actions_layout.addWidget(QLabel("", self.control_bar))
        self.volume_slider = QSlider(Qt.Horizontal, self.control_bar)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(85)
        self.volume_slider.setFixedWidth(90)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #444; border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #0078D4; border-radius: 2px; }
            QSlider::handle:horizontal { width: 10px; margin: -3px 0; background: #FFFFFF; border-radius: 5px; }
        """)
        actions_layout.addWidget(self.volume_slider)

        # Copy Stream URL
        self.btn_copy = QPushButton(" Copy URL", self.control_bar)
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D; color: #DDDDDD; border: 1px solid #444;
                padding: 6px 10px; border-radius: 4px; font-size: 11px;
            }
            QPushButton:hover { background-color: #383838; color: #FFFFFF; }
        """)
        actions_layout.addWidget(self.btn_copy)

        # External Player / Browser launcher
        self.btn_open_external = QPushButton(" Open External", self.control_bar)
        self.btn_open_external.setCursor(Qt.PointingHandCursor)
        self.btn_open_external.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D; color: #DDDDDD; border: 1px solid #444;
                padding: 6px 10px; border-radius: 4px; font-size: 11px;
            }
            QPushButton:hover { background-color: #383838; color: #FFFFFF; }
        """)
        actions_layout.addWidget(self.btn_open_external)

        # Fullscreen Toggle
        self.btn_fullscreen = QPushButton(" Fullscreen", self.control_bar)
        self.btn_fullscreen.setCursor(Qt.PointingHandCursor)
        self.btn_fullscreen.setStyleSheet("""
            QPushButton {
                background-color: #333333; color: white; border: 1px solid #555;
                padding: 6px 12px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #444444; }
        """)
        actions_layout.addWidget(self.btn_fullscreen)

        control_layout.addLayout(actions_layout)
        self.main_layout.addWidget(self.control_bar)

    def _connect_signals(self):
        self.btn_close.clicked.connect(self.close_player)
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        self.btn_copy.clicked.connect(self._copy_stream_url)
        self.btn_open_external.clicked.connect(self._open_external_player)
        self.combo_sources.currentIndexChanged.connect(self._on_source_changed)

        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.errorOccurred.connect(self._on_player_error)

        self.seek_slider.sliderMoved.connect(self.player.setPosition)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)

    def _copy_stream_url(self):
        if not self.formats or self.current_format_idx >= len(self.formats):
            return
        link = self.formats[self.current_format_idx].get("link", "")
        if link:
            from PySide6.QtGui import QGuiApplication
            QGuiApplication.clipboard().setText(link)
            self.status_banner.setText(" Stream backlink copied to clipboard!")
            self.status_banner.setStyleSheet("background-color: #107C41; color: white; font-weight: bold; padding: 8px 16px; font-size: 13px;")
            self.status_banner.show()
            QTimer.singleShot(3000, self.status_banner.hide)

    def _open_external_player(self):
        if not self.formats or self.current_format_idx >= len(self.formats):
            return
        link = self.formats[self.current_format_idx].get("link", "")
        if link:
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(link))

    def load_stream(self, title: str, formats: List[Dict[str, Any]], initial_idx: int = 0):
        self.title_label.setText(f"Playing: {title}")
        self.formats = formats or []
        self.current_format_idx = initial_idx if 0 <= initial_idx < len(self.formats) else 0
        self.tried_count = 0
        self.status_banner.hide()

        self.combo_sources.blockSignals(True)
        self.combo_sources.clear()
        if self.formats:
            for i, f in enumerate(self.formats):
                name = f.get("title") or f"Server {i+1}"
                self.combo_sources.addItem(name)
            self.combo_sources.setCurrentIndex(self.current_format_idx)
        else:
            self.combo_sources.addItem("Direct Link")
        self.combo_sources.blockSignals(False)

        if self.formats:
            self._play_current_format()

    def play_url(self, title: str, url: str):
        self.formats = [{"title": "Direct Link", "link": url}]
        self.load_stream(title, self.formats, 0)

    def _play_current_format(self):
        if not self.formats or self.current_format_idx >= len(self.formats):
            return
        fmt = self.formats[self.current_format_idx]
        link = fmt.get("link", "")
        if not link:
            return

        fmt_name = fmt.get("title", f"Server {self.current_format_idx + 1}")
        # Update source combobox without firing signals
        self.combo_sources.blockSignals(True)
        self.combo_sources.setCurrentIndex(self.current_format_idx)
        self.combo_sources.blockSignals(False)

        # Handle stream link
        url = QUrl(link)
        self.player.setSource(url)
        self.player.play()
        self.btn_play_pause.setText("⏸ Pause")

    def _on_source_changed(self, idx: int):
        if 0 <= idx < len(self.formats):
            self.current_format_idx = idx
            self.tried_count = 0
            self.status_banner.hide()
            self._play_current_format()

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play_pause.setText("▶ Play")
        else:
            self.player.play()
            self.btn_play_pause.setText("⏸ Pause")

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.btn_play_pause.setText("⏸ Pause")
            self.status_banner.hide()
        else:
            self.btn_play_pause.setText("▶ Play")

    def _on_position_changed(self, pos: int):
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(pos)
        self._update_time_label(pos, self.player.duration())

    def _on_duration_changed(self, dur: int):
        self.seek_slider.setRange(0, dur)
        self._update_time_label(self.player.position(), dur)

    def _update_time_label(self, pos: int, dur: int):
        pos_str = QTime(0, 0).addMSecs(pos).toString("mm:ss") if pos >= 0 else "00:00"
        dur_str = QTime(0, 0).addMSecs(dur).toString("mm:ss") if dur > 0 else "Live"
        self.time_label.setText(f"{pos_str} / {dur_str}")

    def _on_volume_changed(self, val: int):
        self.audio_output.setVolume(val / 100.0)

    def _on_player_error(self, error, error_string):
        print(f"Player error [{error}]: {error_string}")
        # Clean-room stream fallback sequence recovered from PlayerActivity.D:
        # Automatically cycle to next format (current_idx + 1) % formats.size()
        if not self.formats:
            self.status_banner.setText("️ Playback failed: No stream source available.")
            self.status_banner.show()
            return

        if len(self.formats) > 1 and self.tried_count < len(self.formats):
            self.tried_count += 1
            prev_idx = self.current_format_idx
            self.current_format_idx = (self.current_format_idx + 1) % len(self.formats)
            next_name = self.formats[self.current_format_idx].get("title", f"Server {self.current_format_idx + 1}")
            self.status_banner.setText(f"️ Server {prev_idx + 1} failed. Auto-switching to: {next_name}...")
            self.status_banner.show()
            self._play_current_format()
        else:
            self.status_banner.setText("️ All available stream servers failed to connect. Click another server or retry.")
            self.status_banner.show()

    def toggle_fullscreen(self):
        top_window = self.window()
        if not self.is_fullscreen_mode:
            top_window.showFullScreen()
            self.btn_fullscreen.setText(" Window")
            self.is_fullscreen_mode = True
        else:
            top_window.showNormal()
            self.btn_fullscreen.setText(" Fullscreen")
            self.is_fullscreen_mode = False

    def close_player(self):
        self.player.stop()
        if self.is_fullscreen_mode:
            self.window().showNormal()
            self.is_fullscreen_mode = False
        self.close_requested.emit()
