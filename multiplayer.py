import datetime

from typing import List
from functools import partial, partialmethod

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QListWidget, QPushButton, QSlider
from PySide6.QtWidgets import QListWidgetItem, QStyle
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QDockWidget
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QMenuBar, QMenu, QToolBar
from PySide6.QtGui import QAction

import config

from medias import get_media_stream_url, parsers
from utils.time import format_time, parse_duration
from interface.twitch import TwitchInterface
from ui.mediadeck_widget import MediaDeck
from ui.segments_widget import SegmentsListWidget


class MultiPlayer(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.setWindowTitle("VOD Cutter")

        self.master_deck: MediaDeck = None
        self.deck_list: List[MediaDeck] = []

        self.main_widget = QWidget()
        self.grid_layout = QGridLayout()

        self.segments_widget = SegmentsListWidget()
        self.segments_dock = QDockWidget()
        self.segments_dock.setWidget(self.segments_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.segments_dock)

        self.main_widget.setLayout(self.grid_layout)
        self.setCentralWidget(self.main_widget)

        # Menu
        self.file_menu = self.menuBar().addMenu("&File")

        add_media_action = self.file_menu.addAction("Add &Media...")
        add_url_action = self.file_menu.addAction("Add &URLs...")
        self.file_menu.addSeparator()
        close_all_action = self.file_menu.addAction("Close All Decks")
        self.file_menu.addSeparator()
        render_submenu = self.file_menu.addMenu("&Render Segments")
        render_submenu.addAction("&Selected &Deck")
        render_submenu.addAction("&All Decks")
        self.file_menu.addSeparator()
        exit_action = self.file_menu.addAction("E&xit")

        self.help_menu = self.menuBar().addMenu("&Help")

        about_action = self.help_menu.addAction("&About...")

        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.addAction("Open")

        self.addToolBar(self.toolbar)
    
    def add_deck(self, media_url: str=None) -> MediaDeck:
        deck_widget = MediaDeck()

        deck_widget.sync_master_btn.clicked.connect(partial(self._on_master_changed, deck_widget))
        deck_widget.sync_enable_btn.clicked.connect(partial(self._on_sync_enabled, deck_widget))
        deck_widget.volume_mute_btn.clicked.connect(partial(self._on_deck_mute_changed, deck_widget))
        deck_widget.transport_slider.sliderReleased.connect(partial(self._on_deck_transport_moved, deck_widget))
        deck_widget.split_btn.clicked.connect(partial(self._on_deck_split, deck_widget))

        deck_widget.video_player.set_media(get_media_stream_url(media_url))
        deck_widget.video_player.is_mute = True

        self.deck_list.append(deck_widget)

        deck_num = len(self.deck_list) - 1

        self.grid_layout.addWidget(deck_widget, deck_num / 1, deck_num % 1)

        if self.master_deck is None:
            self.master_deck = deck_widget
        
        return deck_widget
    
    def sync_deck(self, deck: MediaDeck):
        if deck != self.master_deck:
            if type(self.master_deck.reference_start_time) != type(deck.reference_start_time):
                raise Exception(f"Can't sync deck {deck}: primary deck and synchronized deck doesn't have the same reference start time format.")

            if type(self.master_deck.reference_start_time) is datetime.datetime:
                master_deck_start_time = self.master_deck.reference_start_time.timestamp() 
            else:
                master_deck_start_time = self.master_deck.reference_start_time

            if type(deck.reference_start_time) is datetime.datetime:
                curr_deck_start_time = deck.reference_start_time.timestamp() 
            else:
                curr_deck_start_time = deck.reference_start_time

            new_time = self.master_deck.video_player.time + int(master_deck_start_time - curr_deck_start_time)*1000
            deck.video_player.time = new_time

    def _on_sync_enabled(self, deck: MediaDeck):
        if deck.sync_enabled:
            self.sync_deck(deck)

    def _on_master_changed(self, deck: MediaDeck):
        for d in self.deck_list:
            if d != deck:
                d.is_master = False

        self.master_deck = deck

    def _on_deck_mute_changed(self, deck: MediaDeck):
        for d in self.deck_list:
            if d != deck:
                d.video_player.is_mute = True

    def _on_deck_transport_moved(self, deck: MediaDeck):
        if deck.is_master:
            for d in self.deck_list:
                if d != deck and d.sync_enabled:
                    self.sync_deck(d)
        else:
            deck.sync_enabled = False
    
    def _on_deck_split(self, deck: MediaDeck):
        segments_items = self.segments_widget.get_segments_items(deck)
        if len(segments_items) == 0:
            segments_items.append(self.segments_widget.create_segment(deck))
        
        for s in segments_items:
            if deck.video_player.time > s.get_segment().start_time and deck.video_player.time < s.get_segment().end_time:
                self.segments_widget.split(deck.video_player.time, deck, [s])
    

if __name__ == "__main__":
    qapp = QApplication()

    p = MultiPlayer()

    vod_list = [
        "https://www.twitch.tv/videos/1659154638",
        "https://www.twitch.tv/videos/1659179257",
        #"https://www.twitch.tv/videos/1659102478",
        #"https://www.twitch.tv/videos/1659173811",
        #"https://www.twitch.tv/videos/1659103254",
    ]

    for vod_url in vod_list:
        new_deck = p.add_deck(vod_url)
        
        # TEMPORAIRE
        twitch_ifc = TwitchInterface(
            api_client_id=config.TWITCH_API_CLIENT_ID,
            api_oauth_token=config.TWITCH_API_OAUTH_TOKEN,
            browser_client_id=config.TWITCH_BROWSER_OAUTH_TOKEN,
            browser_oauth_token=config.TWITCH_BROWSER_OAUTH_TOKEN
        )
        vod_id = parsers.get_twitch_id_from_url(vod_url)
        metadatas = twitch_ifc.get_twitch_metadatas(vod_id)

        new_deck.reference_start_time = metadatas["created_at"]
        # /TEMPORAIRE

    p.show()

    qapp.exec()
