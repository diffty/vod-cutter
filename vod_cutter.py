import os
import re
import sys
import json
import math
import datetime
import subprocess

import xml.etree.ElementTree as ET

import requests

from PySide2.QtWidgets import QApplication, QMainWindow
from PySide2.QtWidgets import QWidget, QLabel, QLineEdit, QListWidget, QPushButton
from PySide2.QtWidgets import QListWidgetItem
from PySide2.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout
from PySide2.QtWidgets import QFileDialog

from twitch import TwitchHelix

import config

import vod_thumbnails


def format_time(seconds):
    return f"{str(math.floor(seconds / 3600)).zfill(2)}:{str(math.floor(seconds / 60 % 60)).zfill(2)}:{str(math.floor(seconds % 60)).zfill(2)}"


def parse_duration(d):
    print(d)
    duration_regex = re.search("(?:([0-9]+)h)?(?:([0-9]+)m)?([0-9]+)s", d, re.I)
    if duration_regex:
        hours = duration_regex.group(1)
        mins = duration_regex.group(2)
        secs = duration_regex.group(3)
        return datetime.timedelta(seconds=(int(secs) if secs else 0), minutes=(int(mins) if mins else 0), hours=(int(hours) if hours else 0))
    else:
        return None


class SPLIT_MODE:
    RELATIVE = 0
    ABSOLUTE = 1
    RATIO = 2


class VLCInterface:
    def __init__(self, path):
        self.path = path
        self.process = None
    
    def launch(self):
        self.process = subprocess.Popen([self.path, "--extraintf=http", "--http-password", "test"])

    def get_status(self):
        r = requests.get("http://127.0.0.1:8080/requests/status.xml", auth=('', 'test'))
        return ET.fromstring(r.text)
    
    def get_current_time(self):
        xml_status = self.get_status()
        position = float(xml_status.find("position").text)
        length = int(xml_status.find("length").text)
        return length * position

    def get_duration(self):
        xml_status = self.get_status()
        length = int(xml_status.find("length").text)
        return length



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
        self.set_segment(new_segment_obj)
    
    def set_segment(self, new_segment_obj):
        self.segment_obj = new_segment_obj
        self.on_update()
    
    def split(self, *args, **kwargs):
        new_segment = self.segment_obj.split(*args, **kwargs)
        self.on_update()
        return new_segment

    def on_update(self):
        self.setText(f"{format_time(self.segment_obj.start_time)} -> {format_time(self.segment_obj.end_time)}: {self.segment_obj.name}")


class InputVideo:
    filepath = ""
    metadatas = {}


class VODCutter(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        self.twitch_client_id = config.TWITCH_API_CLIENT_ID
        self.twitch_oauth_token = config.TWITCH_API_OAUTH_TOKEN

        self.twitch_client = TwitchHelix(
            client_id=self.twitch_client_id,
            oauth_token=self.twitch_oauth_token
        )

        self.vlc_interface = VLCInterface(config.VLC_PATH)

        self.loaded_video = None

        self.main_layout = QVBoxLayout()

        self.launch_vlc_btn = QPushButton("Launch VLC")

        self.info_layout = QGridLayout()

        self.file_picker_layout = QHBoxLayout()

        self.file_path_field = QLineEdit()
        self.file_browser_btn = QPushButton(text="...")

        self.file_picker_layout.addWidget(self.file_path_field)
        self.file_picker_layout.addWidget(self.file_browser_btn)

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

        self.info_layout.addLayout(self.file_picker_layout, 0, 1)
        self.info_layout.addWidget(self.id_twitch_field, 1, 1)
        self.info_layout.addWidget(self.created_at_field, 2, 1)
        self.info_layout.addWidget(self.duration_field, 3, 1)
        self.info_layout.addWidget(self.title_field, 4, 1)
        self.info_layout.addWidget(self.streamer_field, 5, 1)
        

        self.segments_create_btn = QPushButton("Import Chapters")
        self.download_thumbnails_btn = QPushButton("Download Thumbnails")

        self.segments_list = QListWidget()

        self.segments_add_btn = QPushButton(text="+")
        self.segments_delete_btn = QPushButton(text="-")
        
        self.jump_start_btn = QPushButton(text="Jump To Start")
        self.jump_end_btn = QPushButton(text="Jump To End")
        
        self.set_start_btn = QPushButton(text="Set Start")
        self.set_end_btn = QPushButton(text="Set End")

        self.split_btn = QPushButton(text="Split")
        
        self.process_selected_btn = QPushButton(text="Process Selected Segment")
        self.process_all_btn = QPushButton(text="Process All Segments")


        self.jump_layout = QHBoxLayout()

        self.jump_layout.addWidget(self.jump_start_btn)
        self.jump_layout.addWidget(self.jump_end_btn)

        self.set_layout = QHBoxLayout()

        self.set_layout.addWidget(self.set_start_btn)
        self.set_layout.addWidget(self.set_end_btn)


        self.main_layout.addWidget(self.launch_vlc_btn)
        self.main_layout.addLayout(self.file_picker_layout)
        self.main_layout.addLayout(self.info_layout)
        self.main_layout.addWidget(self.segments_create_btn)
        self.main_layout.addWidget(self.download_thumbnails_btn)
        self.main_layout.addWidget(self.segments_list)
        self.main_layout.addWidget(self.segments_add_btn)
        self.main_layout.addWidget(self.segments_delete_btn)
        self.main_layout.addLayout(self.jump_layout)
        self.main_layout.addLayout(self.set_layout)
        self.main_layout.addWidget(self.split_btn)
        self.main_layout.addWidget(self.process_selected_btn)
        self.main_layout.addWidget(self.process_all_btn)

        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)


        self.setCentralWidget(self.main_widget)

        self.download_thumbnails_btn.clicked.connect(self.download_thumbnails)
        self.segments_add_btn.clicked.connect(self.create_segment)
        self.split_btn.clicked.connect(self.split_selected_segment)
        self.launch_vlc_btn.clicked.connect(self.on_launch_vlc)
        self.file_browser_btn.clicked.connect(self.on_filebrowse_btn_click)
        self.process_selected_btn.clicked.connect(self.process_selected_segment)
        self.process_all_btn.clicked.connect(self.process_all_segments)

    def on_launch_vlc(self):
        self.vlc_interface.launch()

    def on_filebrowse_btn_click(self):
        filename = QFileDialog.getOpenFileName(self, "Select a video file")
        if filename[0]:
            self.set_video_file(filename[0])
    
    def set_video_file(self, filepath=None):
        self.file_path_field.setText("" if filepath is None else filepath)

        if filepath:
            self.loaded_video = InputVideo()
            self.loaded_video.filepath = filepath

            self.update_twitch_metadatas()
    
    def get_twitch_id_from_filepath(self):
        filename = self.file_path_field.text()

        parsed_filename = re.search("([0-9]+)\.mp4$", filename, re.I)

        if parsed_filename:
            video_id = parsed_filename.group(1)
            return int(video_id)
        else:
            raise Exception(f"<!!> Can't find video Twitch id in video filename ({filename})")
    
    def get_twitch_metadatas(self, twitch_video_id):
        twitch_videos = self.twitch_client.get_videos(video_ids=[twitch_video_id])

        if twitch_videos:
            twitch_video_infos = twitch_videos[0]
            return twitch_video_infos
        else:
            raise Exception(f"<!!> Can't find Twitch metadatasfor video file ({filename})")
    
    def get_video_games_list(self, twitch_video_id):
        r = requests.post(
            "https://gql.twitch.tv/gql",
            headers={
                'Client-Id': config.TWITCH_BROWSER_CLIENT_ID,
                f'Authentification': 'OAuth ' + config.TWITCH_BROWSER_OAUTH_TOKEN,
            },
            data=json.dumps([{
                "operationName": "VideoPlayer_ChapterSelectButtonVideo",
                "variables": {
                    "includePrivate": False,
                    "videoID": str(twitch_video_id)
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "8d2793384aac3773beab5e59bd5d6f585aedb923d292800119e03d40cd0f9b41"
                    }
                }
            }])
        )

        if r.status_code == 200:
            answer_data = r.json()
            moments_data = answer_data[0]["data"]["video"]["moments"]["edges"]

            moments = []

            for m in moments_data:
                moments.append(m["node"])

            return moments
        else:
            return None
    
    def create_segment_before(self, segment_obj):
        pass
    
    def create_segment_after(self, segment_obj):
        pass
    
    def update_twitch_metadatas(self):
        twitch_video_id = self.get_twitch_id_from_filepath()
        metadatas = self.get_twitch_metadatas(twitch_video_id)

        self.loaded_video.metadatas = metadatas

        duration = parse_duration(metadatas["duration"])

        self.id_twitch_field.setText(metadatas["id"])
        self.created_at_field.setText(str(metadatas["created_at"]))
        self.duration_field.setText(format_time(duration.seconds))
        self.title_field.setText(metadatas["title"])
        self.streamer_field.setText(metadatas["user_login"])

        for moment in self.get_video_games_list(metadatas["id"]):
            s = Segment()

            s.name = f"{moment['description']} ({moment['type']})"
            s.start_time = moment['positionMilliseconds'] / 1000
            s.end_time = (moment['positionMilliseconds'] + moment['durationMilliseconds']) / 1000

            self.segments_list.addItem(SegmentListItem(s))
    
    def create_segment(self):
        s = Segment()

        s.name = f"Segment {self.segments_list.count()}"
        s.start_time = 0
        s.end_time = self.vlc_interface.get_duration()

        self.segments_list.addItem(SegmentListItem(s))

    def split_selected_segment(self):
        current_time = self.vlc_interface.get_current_time()

        for segment_item in self.segments_list.selectedItems():
            new_segment = segment_item.split(current_time, name="Splitted " + segment_item.segment_obj.name, split_mode=SPLIT_MODE.ABSOLUTE)
            self.segments_list.addItem(SegmentListItem(new_segment))

    def process_selected_segment(self):
        for segment_item in self.segments_list.selectedItems():
            self.process_segment(segment_item.segment_obj)

    def process_all_segments(self):
        for idx in range(self.segments_list.count()):
            segment_item = self.segments_list.item(idx)
            self.process_segment(segment_item.segment_obj)

    def process_segment(self, segment_obj):
        if not self.loaded_video:
            raise Exception("<!!> No video loaded")

        video_id = self.loaded_video.metadatas.get("id", None)
        created_at = self.loaded_video.metadatas.get("created_at", None)
        user_login = self.loaded_video.metadatas.get("user_login", None)
        
        if not (video_id and created_at and user_login):
            raise Exception("<!!> Missing video metadatas")
        
        created_at_timestamp = int(datetime.datetime.timestamp(created_at))
        
        cmd = f'ffmpeg -i "{self.loaded_video.filepath}" -ss {segment_obj.start_time} -to {segment_obj.end_time} -c:v copy -c:a copy "{user_login}_{created_at_timestamp}_{video_id}.mp4"'
        os.system(cmd)
    
    def download_thumbnails(self):
        twitch_video_id_str = self.id_twitch_field.text()
        if twitch_video_id_str:
            thumbnails_manifest_url = vod_thumbnails.get_video_thumbnails_manifest_url(int(twitch_video_id_str))
            thumbnails_manifest, images_url_list = vod_thumbnails.get_thumbnails_url(thumbnails_manifest_url)

            for img in images_url_list:
                r = requests.get(images_url_list[img])
                fp = open(img, "wb")
                fp.write(r.content)
                fp.close()


qapp = QApplication()

w = VODCutter()
w.show()

qapp.exec_()
