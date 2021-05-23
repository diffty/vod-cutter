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
from ui.filepicker_widget import FilePicker
from playlist import Playlist

from PySide2.QtWidgets import QApplication, QMainWindow
from PySide2.QtWidgets import QWidget, QLabel, QLineEdit, QListWidget, QPushButton
from PySide2.QtWidgets import QListWidgetItem
from PySide2.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout
from PySide2.QtWidgets import QFileDialog

from PySide2.QtCore import Signal

from streamlink.stream.http import HTTPStream
from streamlink.stream.ffmpegmux import MuxedStream


# SNIPPETS
# Drag & drop
# https://stackoverflow.com/questions/25603134/pyside-drag-and-drop-files-into-qlistwidget

# TODO:
# [--] Bouton radio pour définir la vidéo de référence
# [--] Définir automatiquement la vidéo de ref en fonction du type (prendre la première vidéo twitch type "archive" ou le cas échéant la première vidéo)
# [--] Drag & Drop
# [--] Titre de la vidéo dans playlist


class InputVideo:
    video_url = ""
    metadatas = {}
    is_local = False


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

        self.corrected_time = None

        self.main_layout = QVBoxLayout()

        self.launch_vlc_btn = QPushButton("Launch VLC")

        self.open_playlist_btn = QPushButton("Open Playlist")
        
        self.playlist_list = QListWidget()

        self.decks_layout = QHBoxLayout()

        self.match_btn = QPushButton(text="MATCH")

        
        self.main_layout.addWidget(self.launch_vlc_btn)
        self.main_layout.addWidget(self.open_playlist_btn)
        self.main_layout.addWidget(self.playlist_list)
        self.main_layout.addLayout(self.decks_layout)
        self.main_layout.addWidget(self.match_btn)


        match_infos_layout = QGridLayout()

        timecode_source_label = QLabel("Timecode Video Source")
        timecode_target_label = QLabel("Timecode Video Target")
        target_start_time_label = QLabel("Resulting VOD Start Time")
        
        self.timecode_source_field = QLineEdit()
        self.timecode_target_field = QLineEdit()
        self.target_start_time_field = QLineEdit()

        self.timecode_source_field.setEnabled(False)
        self.timecode_target_field.setEnabled(False)
        self.target_start_time_field.setEnabled(False)

        match_infos_layout.addWidget(timecode_source_label, 0, 0)
        match_infos_layout.addWidget(timecode_target_label, 1, 0)
        match_infos_layout.addWidget(target_start_time_label, 2, 0)

        match_infos_layout.addWidget(self.timecode_source_field, 0, 1)
        match_infos_layout.addWidget(self.timecode_target_field, 1, 1)
        match_infos_layout.addWidget(self.target_start_time_field, 2, 1)


        self.main_layout.addLayout(match_infos_layout)


        self.export_btn = QPushButton(text="EXPORT")
        self.main_layout.addWidget(self.export_btn)


        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)


        self.setCentralWidget(self.main_widget)

        self.playlist_list.itemDoubleClicked.connect(self.on_playlist_list_doubleclick)

        self.match_btn.clicked.connect(self.match)
        self.export_btn.clicked.connect(self.export_metadatas)
        self.launch_vlc_btn.clicked.connect(self.on_launch_vlc)
        self.open_playlist_btn.clicked.connect(self.open_playlist)

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
    
    def open_playlist(self):
        filename = QFileDialog.getOpenFileName(self, "Select a playlist")
        if filename[0]:
            self.load_playlist(filename[0])
    
    def load_playlist(self, playlist_filepath):
        p = Playlist.load_from_file(playlist_filepath)
        playlist_item_widget_list = [PlaylistItemWidget(playlist_item) for playlist_item in p.playlist_content]
        for playlist_item in playlist_item_widget_list:
            self.playlist_list.addItem(playlist_item)
    
    def load_playlist_item(self, playlist_item_widget):
        for i, media_url in enumerate(playlist_item_widget.playlist_item.media_list):
            if i >= len(self.video_decks):
                print("<!> Not enough decks to load all the playlist item videos!")
                break
            
            self.video_decks[i].load_video_url(media_url)

    def export_metadatas(self, fixed_created_at):
        time_offset = abs(self.video_decks[0].vlc_instance.get_current_time() - self.video_decks[1].vlc_instance.get_current_time())

        created_at = self.video_decks[0].loaded_video.metadatas.get("created_at")
        
        corrected_time = created_at + datetime.timedelta(seconds=time_offset)

        fixed_metadatas = dict(self.video_decks[0].loaded_video.metadatas)
        fixed_metadatas["created_at"] = corrected_time.isoformat()
        fixed_metadatas["permanent_id"] = {
            "service": self.video_decks[1].loaded_video.metadatas["service"],
            "id": self.video_decks[1].loaded_video.metadatas["id"]
        }
        print(fixed_metadatas)

    def match(self):
        if len(self.video_decks) < 2:
            raise Exception(f"Not enough decks opened ({len(self.video_decks)})")

        time_offset = abs(self.video_decks[0].vlc_instance.get_current_time() - self.video_decks[1].vlc_instance.get_current_time())

        created_at = self.video_decks[0].loaded_video.metadatas.get("created_at")
        
        self.corrected_time = created_at + datetime.timedelta(seconds=time_offset)

        self.timecode_source_field.setText(str(self.video_decks[0].vlc_instance.get_current_time()))
        self.timecode_target_field.setText(str(self.video_decks[1].vlc_instance.get_current_time()))
        self.target_start_time_field.setText(str(self.corrected_time))

        print(created_at)
        print(time_offset)
        print(self.corrected_time)

    def on_launch_vlc(self):
        for deck in self.video_decks:
            deck.vlc_instance.launch()

    def on_playlist_list_doubleclick(self, playlist_item):
        self.load_playlist_item(playlist_item)


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
    
    def load_video_url(self, url=None):
        self.file_picker_field.file_path_field.setText("" if url is None else url)
        
        if url:
            self.loaded_video = InputVideo()

            if re.search(r"^(?:/|[a-z]:[\\/])", url, re.I):
                video_url = "file://" + url
                self.loaded_video.is_local = True
            else:
                video_url = url

            def find_suitable_stream(streams):
                best_stream = streams.get("best", None)

                if best_stream:
                    if type(best_stream) is MuxedStream:
                        return best_stream.substreams[0].url
                    else:
                        return best_stream.url
                else:
                    raise Exception(f"<!!> Can't find best stream")

            if not self.loaded_video.is_local:
                try:
                    streams = streamlink.streams(video_url)
                except streamlink.exceptions.PluginError as e:
                    print(f"<!!> Error while loading video {video_url} : {e}")
                    return

                if streams:
                    self.loaded_video.video_url = find_suitable_stream(streams) #streams["best"]
                else:
                    self.loaded_video.video_url = video_url
            else:
                self.loaded_video.video_url = video_url
            
            if "twitch.tv" in video_url:
                try:
                    self.loaded_video.metadatas["service"] = "twitch"
                    self.update_twitch_metadatas()
                except requests.exceptions.ConnectionError:
                    print("<!!> Can't connect to Twitch API.")
            elif "youtube.com" in video_url:
                try:
                    self.loaded_video.metadatas["service"] = "youtube"
                    self.update_youtube_metadatas()
                except requests.exceptions.ConnectionError:
                    print("<!!> Can't connect to Youtube API.")
            
            try:
                self.vlc_instance.open_url(self.loaded_video.video_url)
            except requests.exceptions.ConnectionError:
                print("<!!> Can't connect to local VLC instance.")
    
    def get_service_metadatas(self):
        pass

    def get_youtube_id_from_url(self):
        url = self.file_picker_field.file_path_field.text()

        # Ressource pour plus tard : https://webapps.stackexchange.com/questions/54443/format-for-id-of-youtube-video
        parsed_url = re.search("v=([0-9A-Za-z_-]+)", url, re.I)

        if parsed_url:
            video_id = parsed_url.group(1)
            return video_id
        else:
            raise Exception(f"<!!> Can't find video Youtube id in video url ({url})")

    def get_twitch_id_from_url(self):
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
    
    def update_youtube_metadatas(self):
        self.loaded_video.metadatas["id"] = self.get_youtube_id_from_url()

        self.id_twitch_field.setText(self.loaded_video.metadatas["id"])

    def update_twitch_metadatas(self):
        twitch_video_id = self.get_twitch_id_from_url()
        metadatas = self.topLevelWidget().twitch_interface.get_twitch_metadatas(twitch_video_id)

        self.loaded_video.metadatas = metadatas

        duration = parse_duration(metadatas["duration"])

        self.id_twitch_field.setText(metadatas["id"])
        self.created_at_field.setText(str(metadatas["created_at"]))
        self.duration_field.setText(format_time(duration.seconds))
        self.title_field.setText(metadatas["title"])
        self.streamer_field.setText(metadatas["user_login"])
    
    def on_video_url_changed(self):
        self.load_video_url(self.file_picker_field.file_path_field.text())


class PlaylistItemWidget(QListWidgetItem):
    def __init__(self, playlist_item) -> None:
        super().__init__()
        self.playlist_item = None
        self.set_playlist_item(playlist_item)
    
    def set_playlist_item(self, new_playlist_item):
        self.playlist_item = new_playlist_item
        self.setText(", ".join(self.playlist_item.media_list))
        print(", ".join(self.playlist_item.media_list))


if __name__ == "__main__":
    qapp = QApplication()

    w = VODSync()
    w.show()

    #w.load_playlist("playlist_test.json")

    qapp.exec_()
