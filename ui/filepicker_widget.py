from PySide2.QtCore import Signal

from PySide2.QtWidgets import QWidget, QLineEdit, QPushButton
from PySide2.QtWidgets import QHBoxLayout
from PySide2.QtWidgets import QFileDialog


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


