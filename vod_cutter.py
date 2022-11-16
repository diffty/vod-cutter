import os
import re
import sys
import json
import math
import datetime
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET

import requests
import streamlink

import config
from utils.time import format_time, parse_duration
from interface.vlc import VLCInterface
from interface.twitch import TwitchInterface
from ui.videoplayer_widget import MediaPlayer

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QListWidget, QPushButton, QSlider
from PySide6.QtWidgets import QListWidgetItem, QStyle
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QDockWidget
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget


### Snippets ###
# Download a segment of 1 minute starting @ 00:20:00
# streamlink --hls-start-offset 00:20:00 --hls-duration 00:01:00 --player-passthrough hls https://www.twitch.tv/videos/1019098497 best -o test

# Open a VLC with the seekable VOD or stream
# streamlink --player-passthrough hls https://www.twitch.tv/videos/1019098497 best

# Example of embedded VLC in PySide2 app
# https://github.com/charlesbrandt/medley/blob/master/player/player.py

# https://www.twitch.tv/videos/1019098497


class SPLIT_MODE:
    RELATIVE = 0
    ABSOLUTE = 1
    RATIO = 2


class Segment:
    name = ""
    start_time = 0
    end_time = 0

    def get_duration(self):
        return self.end_time - self.start_time

    def split(self, split_time, name=None, split_mode=SPLIT_MODE.RELATIVE):
        if name is None:
            name = ""
        
        new_segment = Segment()
        new_segment.name = name

        if split_mode == SPLIT_MODE.RATIO:
            if split_time < 0 or split_time > 1:
                raise Exception("<!!> split_time in ratio mode should be between 0 and 1")
            
            split_time = split_time * self.get_duration()
            split_mode = SPLIT_MODE.RELATIVE

        if split_mode == SPLIT_MODE.RELATIVE:
            if split_time < 0 or split_time > self.get_duration():
                raise Exception("<!!> start_time is out of bounds")

            new_segment.start_time = self.start_time + split_time
            new_segment.end_time = self.end_time
            self.end_time = new_segment.start_time

        elif split_mode == SPLIT_MODE.ABSOLUTE:
            if split_time < self.start_time or split_time > self.end_time:
                raise Exception("<!!> start_time is out of bounds")

            new_segment.start_time = split_time
            new_segment.end_time = self.end_time
            self.end_time = split_time
        
        else:
            raise Exception(f"<!!> Unknown split_mode ({split_mode})")
        
        return new_segment
    

class SegmentListItem(QListWidgetItem):
    def __init__(self, new_segment_obj):
        QListWidgetItem.__init__(self)
        self.segment_obj = None
        self.set_segment(new_segment_obj)
    
    def set_segment(self, new_segment_obj):
        self.segment_obj = new_segment_obj
        self.update()
    
    def get_segment(self):
        return self.segment_obj
    
    def split(self, *args, **kwargs):
        new_segment = self.segment_obj.split(*args, **kwargs)
        self.update()
        return new_segment

    def update(self):
        self.setText(f"{format_time(self.segment_obj.start_time)} -> {format_time(self.segment_obj.end_time)}: {self.segment_obj.name}")


class InputVideo:
    filepath = ""
    metadatas = {}
    is_local = False


class VODCutter(QMainWindow):
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

        self.vlc_interface = VLCInterface(config.VLC_PATH)

        self.loaded_video = None

        self.main_layout = QVBoxLayout()

        self.video_player_widget = MediaPlayer()
        self.main_layout.addWidget(self.video_player_widget)

        # Transport slider
        self.position_slider_widget = QSlider()
        self.position_slider_widget.setOrientation(Qt.Horizontal)

        def _on_media_position_changed(new_position: int):
            if not self.video_player_widget.is_seeking:
                self.position_slider_widget.setValue(new_position)

        def _on_media_duration_changed(new_duration: int):
            self.position_slider_widget.setRange(0, new_duration)

        self.video_player_widget.media_player.positionChanged.connect(_on_media_position_changed)
        self.video_player_widget.media_player.durationChanged.connect(_on_media_duration_changed)

        def _on_slider_pressed():
            self.video_player_widget.is_seeking = True

        def _on_slider_released():
            new_position = self.position_slider_widget.value()
            self.video_player_widget.set_current_time(new_position)
            self.video_player_widget.is_seeking = False

        self.position_slider_widget.sliderPressed.connect(_on_slider_pressed)
        self.position_slider_widget.sliderReleased.connect(_on_slider_released)

        self.main_layout.addWidget(self.position_slider_widget)

        # Video controls
        self.video_controls_layout = QHBoxLayout()
        
        self.play_pause_button = QPushButton(self.style().standardIcon(QStyle.SP_MediaPlay), "")
        self.stop_button = QPushButton(self.style().standardIcon(QStyle.SP_MediaStop), "")
        self.split_btn = QPushButton(text="S")
        self.jump_start_btn = QPushButton(text="JS")
        self.jump_end_btn = QPushButton(text="JE")
        self.set_start_btn = QPushButton(text="SS")
        self.set_end_btn = QPushButton(text="SE")

        def _on_play_pause_btn_click():
            if self.video_player_widget.media_player.playbackState() in [QMediaPlayer.PlaybackState.PausedState,
                                                                         QMediaPlayer.PlaybackState.StoppedState]:
                self.video_player_widget.play()
            else:
                self.video_player_widget.pause()

        def _on_update_play_pause_btn_icon():
            if self.video_player_widget.media_player.playbackState() in [QMediaPlayer.PlaybackState.PausedState,
                                                                         QMediaPlayer.PlaybackState.StoppedState]:
                self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            else:
                self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        
        self.play_pause_button.clicked.connect(_on_play_pause_btn_click)
        self.stop_button.clicked.connect(self.video_player_widget.stop)

        self.video_player_widget.media_player.playbackStateChanged.connect(_on_update_play_pause_btn_icon)

        self.video_controls_layout.addWidget(self.play_pause_button)
        self.video_controls_layout.addWidget(self.stop_button)
        self.video_controls_layout.addWidget(self.jump_start_btn)
        self.video_controls_layout.addWidget(self.jump_end_btn)
        self.video_controls_layout.addWidget(self.set_start_btn)
        self.video_controls_layout.addWidget(self.split_btn)
        self.video_controls_layout.addWidget(self.set_end_btn)

        self.main_layout.addLayout(self.video_controls_layout)

        # Splits dock
        self.splits_dock = QDockWidget()

        self.splits_widget = QWidget()

        self.splits_layout = QHBoxLayout()
        self.splits_widget.setLayout(self.splits_layout)

        self.segments_list = QListWidget()
        self.splits_controls_layout = QVBoxLayout()

        self.segments_add_btn = QPushButton(text="+")
        self.segments_delete_btn = QPushButton(text="-")
        self.segments_import_btn = QPushButton(text="I")
        self.segments_process_btn = QPushButton(text="P")

        self.splits_controls_layout.addWidget(self.segments_add_btn)
        self.splits_controls_layout.addWidget(self.segments_delete_btn)
        self.splits_controls_layout.addWidget(self.segments_import_btn)
        self.splits_controls_layout.addWidget(self.segments_process_btn)
        self.splits_controls_layout.addStretch()

        self.splits_layout.addWidget(self.segments_list)
        self.splits_layout.addLayout(self.splits_controls_layout)

        self.splits_dock.setWidget(self.splits_widget)
        
        self.addDockWidget(Qt.RightDockWidgetArea, self.splits_dock)

        self.set_video_file("/Users/diffty/Movies/_Déchetterie/ChrisEvansDick-1304840174162116609.mp4")

        #self.launch_vlc_btn = QPushButton("Launch VLC")

        #self.info_layout = QGridLayout()

        #self.file_picker_layout = QHBoxLayout()

        #self.file_path_field = QLineEdit()
        #self.file_browser_btn = QPushButton(text="...")

        #self.file_picker_layout.addWidget(self.file_path_field)
        #self.file_picker_layout.addWidget(self.file_browser_btn)

        #vod_filepath_label = QLabel("VOD Filepath")
        #id_twitch_label = QLabel("ID Twitch")
        #created_at_label = QLabel("Created at")
        #duration_label = QLabel("Duration")
        #title_label = QLabel("Title")
        #streamer_label = QLabel("Streamer")
        
        #self.id_twitch_field = QLineEdit()
        #self.created_at_field = QLineEdit()
        #self.duration_field = QLineEdit()
        #self.title_field = QLineEdit()
        #self.streamer_field = QLineEdit()

        #self.id_twitch_field.setEnabled(False)
        #self.created_at_field.setEnabled(False)
        #self.duration_field.setEnabled(False)
        #self.title_field.setEnabled(False)
        #self.streamer_field.setEnabled(False)

        #self.info_layout.addWidget(vod_filepath_label, 0, 0)
        #self.info_layout.addWidget(id_twitch_label, 1, 0)
        #self.info_layout.addWidget(created_at_label, 2, 0)
        #self.info_layout.addWidget(duration_label, 3, 0)
        #self.info_layout.addWidget(title_label, 4, 0)
        #self.info_layout.addWidget(streamer_label, 5, 0)

        #self.info_layout.addLayout(self.file_picker_layout, 0, 1)
        #self.info_layout.addWidget(self.id_twitch_field, 1, 1)
        #self.info_layout.addWidget(self.created_at_field, 2, 1)
        #self.info_layout.addWidget(self.duration_field, 3, 1)
        #self.info_layout.addWidget(self.title_field, 4, 1)
        #self.info_layout.addWidget(self.streamer_field, 5, 1)
        

        #self.segments_create_btn = QPushButton("Import Chapters")
        #self.download_thumbnails_btn = QPushButton("Download Thumbnails")
        #self.download_chatlog_btn = QPushButton("Download Chat Log")

        #self.process_selected_btn = QPushButton(text="Process Selected Segment")
        #self.process_all_btn = QPushButton(text="Process All Segments")


        #self.jump_layout = QHBoxLayout()

        #self.jump_layout.addWidget(self.jump_start_btn)
        #self.jump_layout.addWidget(self.jump_end_btn)

        #self.set_layout = QHBoxLayout()

        #self.set_layout.addWidget(self.set_start_btn)
        #self.set_layout.addWidget(self.set_end_btn)


        #self.main_layout.addWidget(self.launch_vlc_btn)
        #self.main_layout.addLayout(self.file_picker_layout)
        #self.main_layout.addLayout(self.info_layout)
        #self.main_layout.addWidget(self.segments_create_btn)
        #self.main_layout.addWidget(self.download_thumbnails_btn)
        #self.main_layout.addWidget(self.download_chatlog_btn)
        #self.main_layout.addWidget(self.segments_list)
        #self.main_layout.addWidget(self.segments_add_btn)
        #self.main_layout.addWidget(self.segments_delete_btn)
        #self.main_layout.addLayout(self.jump_layout)
        #self.main_layout.addLayout(self.set_layout)
        #self.main_layout.addWidget(self.split_btn)
        #self.main_layout.addWidget(self.process_selected_btn)
        #self.main_layout.addWidget(self.process_all_btn)

        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)


        self.setCentralWidget(self.main_widget)

        self.segments_list.itemDoubleClicked.connect(self.on_segments_list_doubleclick)

        self.jump_start_btn.clicked.connect(self.jump_to_segment_start)
        self.jump_end_btn.clicked.connect(self.jump_to_segment_end)
        self.set_start_btn.clicked.connect(self.set_segment_start)
        self.set_end_btn.clicked.connect(self.set_segment_end)

        #self.download_thumbnails_btn.clicked.connect(self.download_thumbnails)
        self.segments_add_btn.clicked.connect(self.create_segment)
        self.segments_delete_btn.clicked.connect(self.delete_segment)
        self.segments_process_btn.clicked.connect(self.process_selected_segment)
        self.split_btn.clicked.connect(self.split_selected_segment)
        #self.launch_vlc_btn.clicked.connect(self.on_launch_vlc)
        #self.file_path_field.returnPressed.connect(self.on_video_url_changed)
        #self.file_browser_btn.clicked.connect(self.on_filebrowse_btn_click)
        #self.process_all_btn.clicked.connect(self.process_all_segments)

    def on_launch_vlc(self):
        self.vlc_interface.launch()

    def on_filebrowse_btn_click(self):
        filename = QFileDialog.getOpenFileName(self, "Select a video file")
        if filename[0]:
            self.set_video_file(filename[0])

    def on_video_url_changed(self):
        self.set_video_file(self.file_path_field.text())
        
    def on_segments_list_doubleclick(self, item):
        current_segment = item.get_segment()
        if current_segment:
            self.video_player_widget.set_current_time(int(current_segment.start_time))
    
    def set_video_file(self, filepath=None):
        #self.file_path_field.setText ("" if filepath is None else filepath)
        
        if filepath:
            self.loaded_video = InputVideo()

            if re.search(r"^(?:/|[a-z]:[\\/])", filepath, re.I):
                #file_url = "file://" + filepath  # c'est un truc à mettre dans VLCInterface ça si on le réimplémente un jour)
                file_url = filepath
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
            
            #stream_url = self.file_path_field.text()
            #try:
            #    self.update_twitch_metadatas(filepath)
            #except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            #    print(f"<!!> Can't connect to Twitch API : {e}")
            
            #try:
            self.video_player_widget.set_media(self.loaded_video.filepath)
            #except requests.exceptions.ConnectionError:
            #    print("<!!> Can't connect to local VLC instance.")
    
    def get_twitch_id_from_filepath(self, filename):
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
    
    def create_segment_before(self, segment_obj):
        pass
    
    def create_segment_after(self, segment_obj):
        pass
    
    def update_twitch_metadatas(self, stream_url):
        twitch_video_id = self.get_twitch_id_from_filepath(stream_url)
        metadatas = self.twitch_interface.get_twitch_metadatas(twitch_video_id)

        self.loaded_video.metadatas = metadatas

        duration = parse_duration(metadatas["duration"])

        self.id_twitch_field.setText(metadatas["id"])
        self.created_at_field.setText(str(metadatas["created_at"]))
        self.duration_field.setText(format_time(duration.seconds))
        self.title_field.setText(metadatas["title"])
        self.streamer_field.setText(metadatas["user_login"])

        video_games_list = self.twitch_interface.get_video_games_list(metadatas["id"])

        if video_games_list is None:
            print("<!> No video game chapter list found in stream")
            return

        for moment in self.twitch_interface.get_video_games_list(metadatas["id"]):
            s = Segment()

            s.name = f"{moment['description']} ({moment['type']})"
            s.start_time = moment['positionMilliseconds'] / 1000
            s.end_time = (moment['positionMilliseconds'] + moment['durationMilliseconds']) / 1000

            self.segments_list.addItem(SegmentListItem(s))
    
    def create_segment(self):
        s = Segment()

        s.name = f"Segment {self.segments_list.count()}"
        s.start_time = 0
        s.end_time = self.video_player_widget.get_duration()

        self.segments_list.addItem(SegmentListItem(s))
    
    def delete_segment(self):
        for item in self.segments_list.selectedItems():
            idx = self.segments_list.indexFromItem(item)
            item = self.segments_list.takeItem(idx.row())
            del item

    def split_selected_segment(self):
        current_time = self.video_player_widget.get_current_time()

        for segment_item in self.segments_list.selectedItems():
            current_segment = segment_item.get_segment()
            if current_segment:
                new_segment = segment_item.split(current_time, name="Splitted " + current_segment.name, split_mode=SPLIT_MODE.ABSOLUTE)
                self.segments_list.addItem(SegmentListItem(new_segment))
    
    def get_selected_segments(self):
        return list(map(lambda item: item.get_segment(), self.segments_list.selectedItems()))

    def jump_to_segment_start(self):
        selected_segments = self.get_selected_segments()
        if selected_segments:
            self.video_player_widget.set_current_time(math.floor(selected_segments[0].start_time))

    def jump_to_segment_end(self):
        selected_segments = self.get_selected_segments()
        if selected_segments:
            self.video_player_widget.set_current_time(math.floor(selected_segments[0].end_time))

    def set_segment_start(self):
        current_time = self.video_player_widget.get_current_time()
        selected_segments = self.segments_list.selectedItems()
        if selected_segments:
            selected_segments[0].get_segment().start_time = current_time
            selected_segments[0].update()

    def set_segment_end(self):
        current_time = self.video_player_widget.get_current_time()
        selected_segments = self.segments_list.selectedItems()
        if selected_segments:
            selected_segments[0].get_segment().end_time = current_time
            selected_segments[0].update()

    def process_selected_segment(self):
        for segment in self.get_selected_segments():
            self.process_segment(segment)

    def process_all_segments(self):
        for idx in range(self.segments_list.count()):
            segment_item = self.segments_list.item(idx)
            self.process_segment(segment_item.get_segment())

    def process_segment(self, segment_obj):
        if not self.loaded_video:
            raise Exception("<!!> No video loaded")

        video_id = self.loaded_video.metadatas.get("id", None)
        created_at = self.loaded_video.metadatas.get("created_at", None)
        user_login = self.loaded_video.metadatas.get("user_login", None)
        
        output_file_name = "output.mp4"

        if video_id and created_at and user_login:
            created_at_timestamp = int(datetime.datetime.timestamp(created_at))
            output_file_name = f"{user_login}_{created_at_timestamp}_{video_id}.mp4"
        else:
            print(f"<!> Missing video metadatas. Writing file to {output_file_name}")
        
        
        if self.loaded_video.is_local:
            cmd = f'ffmpeg -i "{self.loaded_video.filepath}" -ss {segment_obj.start_time} -to {segment_obj.end_time} -c:v copy -c:a copy {output_file_name}'
        else:
            cmd = f'streamlink -f --hls-start-offset {format_time(segment_obj.start_time)} --hls-duration {format_time(segment_obj.end_time - segment_obj.start_time)} --player-passthrough hls "{self.loaded_video.filepath}" best -o {output_file_name}'

        print(cmd)
        
        os.system(cmd)
    
    def download_thumbnails(self):
        twitch_video_id_str = self.id_twitch_field.text()
        if twitch_video_id_str:
            thumbnails_manifest_url = self.twitch_interface.get_video_thumbnails_manifest_url(int(twitch_video_id_str))
            thumbnails_manifest, images_url_list = self.twitch_interface.get_thumbnails_url_from_manifest(thumbnails_manifest_url)

            for img in images_url_list:
                r = requests.get(images_url_list[img])
                fp = open(img, "wb")
                fp.write(r.content)
                fp.close()


qapp = QApplication()

w = VODCutter()
w.show()

qapp.exec_()
