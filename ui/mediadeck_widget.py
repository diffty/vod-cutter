from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QWidget, QPushButton, QSlider
from PySide6.QtWidgets import QStyle
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from .vlcplayer_widget import VlcPlayer


class MediaDeck(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.layout = QVBoxLayout()

        # Video player widget
        self.video_player = VlcPlayer()
        self.layout.addWidget(self.video_player)

        # Transport slider
        self.transport_slider = QSlider()
        self.transport_slider.setOrientation(Qt.Horizontal)

        def _on_slider_pressed():
            self.video_player.is_seeking = True

        def _on_slider_released():
            new_position = self.transport_slider.value()
            self.video_player.time = new_position
            self.video_player.is_seeking = False

        self.transport_slider.sliderPressed.connect(_on_slider_pressed)
        self.transport_slider.sliderReleased.connect(_on_slider_released)

        def _on_media_position_changed(new_position: int):
            if not self.video_player.is_seeking:
                self.transport_slider.setValue(new_position)

        def _on_media_duration_changed(new_duration: int):
            self.transport_slider.setRange(0, new_duration)

        self.video_player.positionChanged.connect(_on_media_position_changed)
        self.video_player.durationChanged.connect(_on_media_duration_changed)

        self.layout.addWidget(self.transport_slider)

        # Video controls
        self.video_controls_layout = QHBoxLayout()
        
        self.play_pause_btn = QPushButton(self.style().standardIcon(QStyle.SP_MediaPlay), "")
        self.stop_btn = QPushButton(self.style().standardIcon(QStyle.SP_MediaStop), "")
        self.eject_btn = QPushButton(text="Eject")
        self.split_btn = QPushButton(text="S")
        self.jump_start_btn = QPushButton(text="JS")
        self.jump_end_btn = QPushButton(text="JE")
        self.set_start_btn = QPushButton(text="SS")
        self.set_end_btn = QPushButton(text="SE")
        self.sync_master_btn = QPushButton(text="Master")
        self.sync_enable_btn = QPushButton(text="Sync")
        self.cog_menu_btn = QPushButton(text="Cog")

        self.sync_master_btn.setCheckable(True)
        self.sync_enable_btn.setCheckable(True)

        def _on_play_pause_btn_click():
            if not self.video_player.is_playing:
                self.video_player.play()
            else:
                self.video_player.pause()

        def _on_update_play_pause_btn_icon():
            if not self.video_player.is_playing:
                self.play_pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            else:
                self.play_pause_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        
        self.play_pause_btn.clicked.connect(_on_play_pause_btn_click)
        self.stop_btn.clicked.connect(self.video_player.stop)

        self.video_player.mediaStateChanged.connect(_on_update_play_pause_btn_icon)

        self.video_controls_layout.addWidget(self.play_pause_btn)
        self.video_controls_layout.addWidget(self.stop_btn)
        self.video_controls_layout.addWidget(self.eject_btn)
        self.video_controls_layout.addWidget(self.jump_start_btn)
        self.video_controls_layout.addWidget(self.jump_end_btn)
        self.video_controls_layout.addWidget(self.set_start_btn)
        self.video_controls_layout.addWidget(self.split_btn)
        self.video_controls_layout.addWidget(self.set_end_btn)
        self.video_controls_layout.addWidget(self.sync_master_btn)
        self.video_controls_layout.addWidget(self.sync_enable_btn)
        self.video_controls_layout.addWidget(self.cog_menu_btn)
        
        self.layout.addLayout(self.video_controls_layout)

        self.setLayout(self.layout)
    
    def __repr__(self) -> str:
        media = self.video_player.media_player.get_media()
        if media:
            return f"<MediaDeck [Loaded]: {media.get_mrl()}>"
        else:
            return f"<MediaDeck [Unloaded]>"

    @property
    def is_master(self):
        return self.sync_master_btn.isChecked()

    @is_master.setter
    def is_master(self, value):
        self.sync_master_btn.setChecked(value)

    @property
    def sync_enabled(self):
        return self.sync_enable_btn.isChecked()

    @sync_enabled.setter
    def sync_enabled(self, value):
        self.sync_enable_btn.setChecked(value)



if __name__ == "__main__":
    from ..medias import get_media_stream_url

    app = QApplication()

    w = MediaDeck()
    w.show()

    w.video_player.set_media(get_media_stream_url("https://www.twitch.tv/videos/1653331592"))
    w.video_player.play()

    app.exec()