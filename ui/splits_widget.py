from utils.time import format_time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QListWidget, QPushButton
from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout


class SPLIT_MODE:
    RELATIVE = 0
    ABSOLUTE = 1
    RATIO = 2


class Segment:
    name = ""
    start_time = 0
    end_time = 0
    deck = None

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
        self.setText(f"{format_time(self.segment_obj.start_time/1000)} -> {format_time(self.segment_obj.end_time/1000)}: {self.segment_obj.name}")


class SegmentsListWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        # UI build
        self.splits_layout = QHBoxLayout()

        self.segments_list = QListWidget()
        self.splits_controls_layout = QVBoxLayout()

        #self.segments_add_btn = QPushButton(text="+")
        self.segments_delete_btn = QPushButton(text="-")
        self.segments_import_btn = QPushButton(text="I")
        self.segments_process_btn = QPushButton(text="P")

        #self.splits_controls_layout.addWidget(self.segments_add_btn)
        self.splits_controls_layout.addWidget(self.segments_delete_btn)
        self.splits_controls_layout.addWidget(self.segments_import_btn)
        self.splits_controls_layout.addWidget(self.segments_process_btn)
        self.splits_controls_layout.addStretch()

        self.splits_layout.addWidget(self.segments_list)
        self.splits_layout.addLayout(self.splits_controls_layout)

        self.setLayout(self.splits_layout)

        # Events handling
        #self.segments_add_btn.clicked.connect(self.create_segment)
        self.segments_delete_btn.clicked.connect(self.delete_segment)
        self.segments_list.itemDoubleClicked.connect(self.on_segments_list_doubleclick)

    def on_segments_list_doubleclick(self, item):
        current_segment = item.get_segment()
        if current_segment:
            self.video_player_widget.time = int(current_segment.start_time)

    def create_segment_before(self, segment_obj):
        pass

    def create_segment_after(self, segment_obj):
        pass

    def create_segment(self, deck):
        s = Segment(deck)

        s.name = f"Segment {self.segments_list.count()}"
        s.start_time = 0
        s.end_time = self.video_player_widget.duration

        self.segments_list.addItem(SegmentListItem(s))
    
    def delete_segment(self):
        for item in self.segments_list.selectedItems():
            idx = self.segments_list.indexFromItem(item)
            item = self.segments_list.takeItem(idx.row())
            del item

    def split_selected_segment(self):
        current_time = self.video_player_widget.time

        for segment_item in self.segments_list.selectedItems():
            current_segment = segment_item.get_segment()
            if current_segment:
                new_segment = segment_item.split(current_time, name="Splitted " + current_segment.name, split_mode=SPLIT_MODE.ABSOLUTE)
                self.segments_list.addItem(SegmentListItem(new_segment))
    
    def get_selected_segments(self):
        return list(map(lambda item: item.get_segment(), self.segments_list.selectedItems()))
