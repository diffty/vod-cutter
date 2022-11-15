import os
import re
import sys
import json
import math
import datetime
import subprocess
import urllib.parse
import urllib3
import xml.etree.ElementTree as ET

import requests
import streamlink

import config
from utils.time import format_time, parse_duration
from interface.vlc import VLCInterface
from interface.twitch import TwitchInterface

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication, QMainWindow
from PySide2.QtWidgets import QWidget, QPushButton, QSlider
from PySide2.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout
from PySide2.QtMultimediaWidgets import QVideoWidget
from PySide2.QtMultimedia import QMediaPlayer, QMediaPlaylist
from PySide2.QtCore import QUrl
from PySide2.QtGui import QIcon

import streamlink


class VideoPlayer(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.is_seeking = False

        self.main_layout = QVBoxLayout()

        self.video_output_widget = QVideoWidget()

        self.player_control_layout = QHBoxLayout()

        self.play_pause_button = QPushButton(self.style().standardIcon(self.style().SP_MediaPlay), "")
        self.stop_button = QPushButton(self.style().standardIcon(self.style().SP_MediaStop), "")

        def _on_play_pause_btn_click():
            if self.media_player.state() in [QMediaPlayer.State.PausedState,
                                            QMediaPlayer.State.StoppedState]:
                self.play()
            else:
                self.pause()

        self.play_pause_button.clicked.connect(_on_play_pause_btn_click)
        self.stop_button.clicked.connect(self.stop)

        self.position_slider_widget = QSlider()
        self.position_slider_widget.setOrientation(Qt.Horizontal)

        self.player_control_layout.addWidget(self.play_pause_button)
        self.player_control_layout.addWidget(self.stop_button)
        self.player_control_layout.addWidget(self.position_slider_widget)

        self.player_layout = QVBoxLayout()

        self.player_layout.addWidget(self.video_output_widget)
        self.player_layout.addLayout(self.player_control_layout)

        self.media_playlist = QMediaPlaylist()

        self.media_player = QMediaPlayer()
        self.media_player.setPlaylist(self.media_playlist)

        def _on_media_position_changed(new_position: int):
            if not self.is_seeking:
                self.position_slider_widget.setValue(new_position)

        def _on_media_duration_changed(new_duration: int):
            self.position_slider_widget.setRange(0, new_duration)

        self.media_player.positionChanged.connect(_on_media_position_changed)
        self.media_player.durationChanged.connect(_on_media_duration_changed)

        def _on_slider_pressed():
            self.is_seeking = True

        def _on_slider_released():
            new_position = self.position_slider_widget.value()
            self.media_player.setPosition(new_position)
            self.is_seeking = False

        self.position_slider_widget.sliderPressed.connect(_on_slider_pressed)
        self.position_slider_widget.sliderReleased.connect(_on_slider_released)

        self.media_player.setVideoOutput(self.video_output_widget)

        def _on_update_play_pause_btn_icon():
            if self.media_player.state() in [QMediaPlayer.State.PausedState,
                                            QMediaPlayer.State.StoppedState]:
                self.play_pause_button.setIcon(self.style().standardIcon(self.style().SP_MediaPlay))
            else:
                self.play_pause_button.setIcon(self.style().standardIcon(self.style().SP_MediaPause))
        
        self.media_player.stateChanged.connect(_on_update_play_pause_btn_icon)

        self.setLayout(self.player_layout)
    
    def set_media(self, file_url, local=False):
        self.media_playlist = QMediaPlaylist()

        self.media_player.stop()

        if re.search(r"^(?:/|[a-z]:[\\/])", file_url, re.I):
            url = QUrl.fromLocalFile(file_url)
        else:
            streams = streamlink.streams(file_url)
            if streams:
                url = QUrl(streams["best"].url)
            else:
                url = QUrl(file_url)

        self.media_playlist.addMedia(url)
        self.media_playlist.setCurrentIndex(1)

        self.media_player.setPlaylist(self.media_playlist)
        self.play()

    def play(self):
        self.media_player.play()

    def stop(self):
        self.media_player.stop()

    def pause(self):
        self.media_player.pause()
