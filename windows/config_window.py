from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QLineEdit,
    QMessageBox
)
from PySide6.QtCore import Qt

from windows.base import RhythmItem
import json
from bluebird import *
from typing import List

class ConfigOptionWidget(QWidget):
    def __init__(self, name: str, value: str, hint: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.label = QLabel(name)
        self.edit = QLineEdit(str(value))
        self.edit.setToolTip(hint)
        self.label.setToolTip(hint)

        layout.addWidget(self.label)
        layout.addWidget(self.edit)

    def get_value(self):
        return self.edit.text()

    def set_value(self, val: str):
        self.edit.setText(str(val))

class ConfigWindow(QWidget):
    def __init__(self, parent, flute, on_close_callback=None):
        super().__init__()
        self.parent = parent
        self.flute: Flute = flute
        self.resize(parent.width(), parent.height())
        self.setWindowTitle("Rhythm Config Window")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.on_close_callback = on_close_callback

        layout = QVBoxLayout(self)

        # Top buttons
        top_bar = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.reset_btn = QPushButton("Reset")
        top_bar.addWidget(self.save_btn)
        top_bar.addWidget(self.reset_btn)
        layout.addLayout(top_bar)

        # Config options
        self.options = self.fetch_options()

        self.list_widget = QListWidget()
        self.option_widgets = []

        for opt in self.options:
            item = QListWidgetItem()
            widget = ConfigOptionWidget(opt.name, opt.value, opt.hint)
            self.option_widgets.append(widget)

            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

        layout.addWidget(self.list_widget)

        self.save_btn.clicked.connect(self.save)
        self.reset_btn.clicked.connect(self.reset)

    def save(self):
        for i, opt in enumerate(self.options):
            opt.value = self.option_widgets[i].get_value()
        
        # Convert to a list of {name: value} dictionaries
        json_data = {item.name: item.value for item in self.options}

        json_data["interval_ms"] = int(json_data["interval_ms"])

        json_str = json.dumps(json_data)
        # This would be replaced with actual backend calls in a real implementation
        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='update_rhythm',
            args=[json_str]
        ))
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to update rhythm because {'; '.join(response.results)}")
        return

    def reset(self):
        for i, opt in enumerate(self.options):
            self.option_widgets[i].set_value(opt.value)

    def closeEvent(self, event):
        if self.on_close_callback:
            self.on_close_callback()
        return super().closeEvent(event)

    def fetch_options(self) -> List[RhythmItem]:
        # This would be replaced with actual backend calls in a real implementation
        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='info',
            args=[]
        ))
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to retrieve rhythm info because {'; '.join(response.results)}")
            return
        
        if len(response.results) == 0:
            self.make_default_if_none()
            return self.fetch_shortcuts("")

        options = [RhythmItem(**json.loads(content)) for content in response.results]

        print(options)

        return options
