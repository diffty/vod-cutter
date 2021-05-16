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

from PySide2.QtWidgets import QApplication, QMainWindow
from PySide2.QtWidgets import QWidget, QLabel, QLineEdit, QListWidget, QPushButton
from PySide2.QtWidgets import QListWidgetItem
from PySide2.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout
from PySide2.QtWidgets import QFileDialog

from PySide2.QtCore import Signal


class InputVideo:
    filepath = ""
    metadatas = {}
    is_local = False


class FilePicker(QWidget):
    changed = Signal()

    def __init__(self) -> None:
        QWidget.__init__(self)

        self.file_picker_layout = QHBoxLayout()

        self.file_path_field = QLineEdit()
        self.file_browser_btn = QPushButton(text="...")

        self.file_picker_layout.addWidget(self.file_path_field)
        self.file_picker_layout.addWidget(self.file_browser_btn)

        self.setLayout(self.file_picker_layout)

        self.file_path_field.returnPressed.connect(self.on_video_url_changed)
        self.file_browser_btn.clicked.connect(self.on_filebrowse_btn_click)

    def on_filebrowse_btn_click(self):
        filename = QFileDialog.getOpenFileName(self, "Select a video file")
        if filename[0]:
            self.file_path_field.setText(filename[0])
            self.on_video_url_changed()
    
    def on_video_url_changed(self, *args):
        self.changed.emit()


class VideoDeck(QWidget):
    def __init__(self, vlc_instance=None):
        QWidget.__init__(self)
        self.layout = QHBoxLayout()

        self.loaded_video = None
        self.vlc_instance = vlc_instance

        self.file_picker_field = FilePicker()

        self.info_layout = QGridLayout()

        vod_filepath_label = QLabel("VOD Filepath")
        id_twitch_label = QLabel("ID Twitch")
        created_at_label = QLabel("Created at")
        duration_label = QLabel("Duration")
        title_label = QLabel("Title")
        streamer_label = QLabel("Streamer")
        
        self.id_twitch_field = QLineEdit()
        self.created_at_field = QLineEdit()
        self.duration_field = QLineEdit()
        self.title_field = QLineEdit()
        self.streamer_field = QLineEdit()

        self.id_twitch_field.setEnabled(False)
        self.created_at_field.setEnabled(False)
        self.duration_field.setEnabled(False)
        self.title_field.setEnabled(False)
        self.streamer_field.setEnabled(False)

        self.info_layout.addWidget(vod_filepath_label, 0, 0)
        self.info_layout.addWidget(id_twitch_label, 1, 0)
        self.info_layout.addWidget(created_at_label, 2, 0)
        self.info_layout.addWidget(duration_label, 3, 0)
        self.info_layout.addWidget(title_label, 4, 0)
        self.info_layout.addWidget(streamer_label, 5, 0)

        self.info_layout.addWidget(self.file_picker_field, 0, 1)
        self.info_layout.addWidget(self.id_twitch_field, 1, 1)
        self.info_layout.addWidget(self.created_at_field, 2, 1)
        self.info_layout.addWidget(self.duration_field, 3, 1)
        self.info_layout.addWidget(self.title_field, 4, 1)
        self.info_layout.addWidget(self.streamer_field, 5, 1)

        self.layout.addLayout(self.info_layout)
        self.file_picker_field.changed.connect(self.on_video_url_changed)

        self.setLayout(self.layout)
    
    def set_video_file(self, filepath=None):
        self.file_picker_field.file_path_field.setText("" if filepath is None else filepath)
        
        if filepath:
            self.loaded_video = InputVideo()

            if re.search(r"^(?:/|[a-z]:[\\/])", filepath, re.I):
                file_url = "file://" + filepath
                self.loaded_video.is_local = True
            else:
                file_url = filepath

            if not self.loaded_video.is_local:
                streams = streamlink.streams(file_url)
                if streams:
                    self.loaded_video.filepath = streams["best"].url
                else:
                    self.loaded_video.filepath = file_url
            else:
                self.loaded_video.filepath = file_url
            
            try:
                self.update_twitch_metadatas()
            except requests.exceptions.ConnectionError:
                print("<!!> Can't connect to Twitch API.")
            
            try:
                self.vlc_instance.open_url(self.loaded_video.filepath)
            except requests.exceptions.ConnectionError:
                print("<!!> Can't connect to local VLC instance.")
    
    def get_twitch_id_from_filepath(self):
        filename = self.file_picker_field.file_path_field.text()

        parsed_filename = re.search("([0-9]+)\.mp4$", filename, re.I)

        if parsed_filename:
            video_id = parsed_filename.group(1)
            return int(video_id)
        else:
            parsed_url = re.search("videos/([0-9]+)", filename, re.I)
            if parsed_url:
                video_id = parsed_url.group(1)
                return int(video_id)
            else:
                raise Exception(f"<!!> Can't find video Twitch id in video filename ({filename})")
    
    def update_twitch_metadatas(self):
        twitch_video_id = self.get_twitch_id_from_filepath()
        metadatas = self.topLevelWidget().twitch_interface.get_twitch_metadatas(twitch_video_id)

        self.loaded_video.metadatas = metadatas

        duration = parse_duration(metadatas["duration"])

        self.id_twitch_field.setText(metadatas["id"])
        self.created_at_field.setText(str(metadatas["created_at"]))
        self.duration_field.setText(format_time(duration.seconds))
        self.title_field.setText(metadatas["title"])
        self.streamer_field.setText(metadatas["user_login"])
    
    def on_video_url_changed(self):
        self.set_video_file(self.file_picker_field.file_path_field.text())


class VODSync(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.twitch_client_id = config.TWITCH_API_CLIENT_ID
        self.twitch_oauth_token = config.TWITCH_API_OAUTH_TOKEN

        self.twitch_interface = TwitchInterface(
            api_client_id=config.TWITCH_API_CLIENT_ID,
            api_oauth_token=config.TWITCH_API_OAUTH_TOKEN,
            browser_client_id=config.TWITCH_BROWSER_OAUTH_TOKEN,
            browser_oauth_token=config.TWITCH_BROWSER_OAUTH_TOKEN
        )

        self.loaded_videos = []
        self.video_decks = []

        self.main_layout = QVBoxLayout()

        self.launch_vlc_btn = QPushButton("Launch VLC")

        self.playlist_list = QListWidget()

        self.decks_layout = QHBoxLayout()

        self.match_btn = QPushButton(text="MATCH")
        
        self.main_layout.addWidget(self.launch_vlc_btn)
        self.main_layout.addWidget(self.playlist_list)
        self.main_layout.addLayout(self.decks_layout)
        self.main_layout.addWidget(self.match_btn)

        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)


        self.setCentralWidget(self.main_widget)

        self.playlist_list.itemDoubleClicked.connect(self.on_playlist_list_doubleclick)

        self.match_btn.clicked.connect(self.match)
        self.launch_vlc_btn.clicked.connect(self.on_launch_vlc)


        self.add_video_deck(8080)
        self.add_video_deck(8081)

    def get_loaded_video(self, idx):
        if idx < 0 or idx >= len(self.loaded_videos):
            raise IndexError(f"<!!> Unknown loaded video index: {idx}")
        return self.loaded_videos[idx]

    def get_vlc_instance(self, idx):
        if idx < 0 or idx >= len(self.vlc_instances):
            raise IndexError(f"<!!> Unknown loaded video index: {idx}")
        return self.vlc_instances[idx]
    
    def add_video_deck(self, vlc_port=8080):
        new_deck = VideoDeck(VLCInterface(config.VLC_PATH, port=vlc_port))
        self.video_decks.append(new_deck)
        self.decks_layout.addWidget(new_deck)

    def match(self):
        for deck in self.video_decks:
            print(deck.vlc_instance.get_current_time())

    def on_launch_vlc(self):
        for deck in self.video_decks:
            deck.vlc_instance.launch()

    def on_playlist_list_doubleclick(self, item):
        current_segment = item.get_segment()
        if current_segment:
            self.get_vlc_instance(0).set_current_time(int(current_segment.start_time))
    

qapp = QApplication()

w = VODSync()
w.show()

qapp.exec_()
