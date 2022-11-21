import sys

import vlc

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWidgets import QWidget, QFrame
from PySide6.QtCore import Signal


class VlcPlayer(QFrame):
    positionChanged = Signal(int)
    durationChanged = Signal(int)
    mediaStateChanged = Signal()

    def __init__(self):
        QFrame.__init__(self)

        self.is_seeking = False

        self.vlc_instance = vlc.Instance()
        self.media_player: vlc.MediaPlayer = self.vlc_instance.media_player_new()
        self.event_manager: vlc.EventManager = self.vlc_instance.vlm_get_event_manager()

        def _on_position_changed(event: vlc.Event):
            self.positionChanged.emit(self.time)

        def _on_duration_changed(event: vlc.Event):
            self.durationChanged.emit(self.duration)
        
        self.media_player.event_manager().event_attach(vlc.EventType.MediaPlayerPositionChanged, _on_position_changed)
        self.media_player.event_manager().event_attach(vlc.EventType.MediaPlayerLengthChanged, _on_duration_changed)

        if sys.platform.startswith("linux"):  # for Linux using the X Server
            self.media_player.set_xwindow(self.winId())
        elif sys.platform == "win32":  # for Windows
            self.media_player.set_hwnd(self.winId())
        elif sys.platform == "darwin":  # for MacOS
            self.media_player.set_nsobject(self.winId())
        else:
            raise Exception(f"Unknown platform {sys.platform}!")
    
    @property
    def is_playing(self):
        return self.media_player.is_playing()
    
    @property
    def duration(self):
        return self.media_player.get_length()
    
    @property
    def time(self):
        return self.media_player.get_time()
    
    @property
    def media_state(self) -> vlc.State:
        return self.media_player.get_state()
    
    @time.setter
    def time(self, new_position):
        return self.media_player.set_time(new_position)
    
    def set_media(self, media_url):
        media: vlc.Media = self.vlc_instance.media_new(media_url)

        def _on_media_state_changed(event: vlc.Event):
            print(self.media_state)
            self.mediaStateChanged.emit()

        def _on_media_freed(event: vlc.Event):
            print("Media freed")
            media.event_manager().event_detach(vlc.EventType.MediaStateChanged)
            media.event_manager().event_detach(vlc.EventType.MediaFreed)

        media.event_manager().event_attach(vlc.EventType.MediaStateChanged, _on_media_state_changed)
        media.event_manager().event_attach(vlc.EventType.MediaFreed, _on_media_freed)

        self.media_player.set_media(media)

    def play(self):
        self.media_player.play()
        
    def pause(self):
        self.media_player.pause()
        
    def stop(self):
        self.media_player.stop()
    
        

if __name__ == "__main__":
    app = QApplication()

    w = VlcPlayer()
    w.show()
    #w.set_media("C:/Users/DiFFtY/Desktop/Cap.mp4")
    w.set_media("https://dgeft87wbj63p.cloudfront.net/6172637ead13c0cbadd8_gydias_40075579912_1668513840/720p60/index-dvr.m3u8")
    w.play()

    app.exec()
