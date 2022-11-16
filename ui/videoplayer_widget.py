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

from utils.time import format_time, parse_duration
from interface.vlc import VLCInterface
from interface.twitch import TwitchInterface

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWidgets import QWidget, QPushButton, QSlider
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon

import streamlink


class MediaPlayer(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.is_seeking = False

        self.video_output_widget = QVideoWidget()

        self.player_layout = QVBoxLayout()
        self.player_layout.addWidget(self.video_output_widget)

        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_output_widget)
        self.video_output_widget.setAutoFillBackground(False)
        
        self.setLayout(self.player_layout)
    
    def set_media(self, file_url, local=False):
        self.media_player.stop()

        if re.search(r"^(?:/|[a-z]:[\\/])", file_url, re.I):
            url = QUrl.fromLocalFile(file_url)
        else:
            streams = streamlink.streams(file_url)
            if streams:
                url = QUrl(streams["best"].url)
            else:
                url = QUrl(file_url)

        self.media_player.setSource(url)
    
    def set_current_time(self, new_time):
        self.media_player.setPosition(new_time)

    def get_current_time(self):
        return self.media_player.position()
    
    def get_duration(self):
        return self.media_player.duration()

    def play(self):
        self.media_player.play()

    def stop(self):
        self.media_player.stop()

    def pause(self):
        self.media_player.pause()
