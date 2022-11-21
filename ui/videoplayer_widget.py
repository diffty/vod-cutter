import re

import streamlink

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl


class MediaPlayer(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.is_seeking = False

        self.video_output = QVideoWidget()
        self.audio_output = QAudioOutput()

        self.player_layout = QVBoxLayout()
        self.player_layout.addWidget(self.video_output)

        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_output)
        self.media_player.setAudioOutput(self.audio_output)

        def _onError(err):
            print(err)

        self.media_player.errorOccurred.connect(_onError)
        #self.video_output.setAutoFillBackground(False)
        
        self.setLayout(self.player_layout)
    
    def set_media(self, file_url, local=False):
        if re.search(r"^(?:/|[a-z]:[\\/])", file_url, re.I):
            url = QUrl.fromLocalFile(file_url)
        else:
            streams = streamlink.streams(file_url)
            if streams:
                url = QUrl(streams["best"].url)
            else:
                url = QUrl(file_url)
        
        print(url)

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


if __name__ == "__main__":
    import os
    os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation'

    from PySide6.QtWidgets import QApplication

    app = QApplication()

    video_output = QVideoWidget()
    audio_output = QAudioOutput()

    media_player = QMediaPlayer()
    media_player.setVideoOutput(video_output)
    media_player.setAudioOutput(audio_output)

    

    video_output.show()
    media_player.setSource(QUrl.fromLocalFile("C:/Users/DiFFtY/Desktop/lezgongue_anaglyph.mp4"))
    #media_player.setSource(QUrl.fromLocalFile("C:/Users/DiFFtY/Desktop/Cap.mp4"))


    #media_player.play()

    def _bufferProgress(progress):
        print(f"Buffering: {progress}%")

    def _mediaStatus(state):
        print(f"Media status changed: {state}")
        print(f"Video tracks : {[t.keys() for t in media_player.videoTracks()]}")
        media_player.play()
        print(media_player.errorString())
        
    def _metadataChanged():
        from PySide6.QtMultimedia import QMediaMetaData
        print(f"Metadatas changed")
        print(media_player.metaData().keys())
        print(media_player.metaData().stringValue(media_player.metaData().VideoCodec))

    media_player.bufferProgressChanged.connect(_bufferProgress)
    media_player.mediaStatusChanged.connect(_mediaStatus)
    media_player.metaDataChanged.connect(_metadataChanged)


    app.exec()