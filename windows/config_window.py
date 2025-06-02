from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QLineEdit
)
from PySide6.QtCore import Qt


class ConfigOptionWidget(QWidget):
    def __init__(self, name: str, value: str, hint: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.label = QLabel(name)
        self.edit = QLineEdit(value)
        self.edit.setToolTip(hint)
        self.label.setToolTip(hint)

        layout.addWidget(self.label)
        layout.addWidget(self.edit)

    def get_value(self):
        return self.edit.text()

    def set_value(self, val: str):
        self.edit.setText(val)

class ConfigWindow(QWidget):
    def __init__(self, on_close_callback=None):
        super().__init__()
        self.setWindowTitle("Config Window")
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
        self.options = [
            {"name": "Username", "value": "admin", "hint": "Enter your login name"},
            {"name": "Server URL", "value": "https://example.com", "hint": "The base API URL"},
            {"name": "Timeout", "value": "30", "hint": "In seconds"}
        ]

        self.list_widget = QListWidget()
        self.option_widgets = []

        for opt in self.options:
            item = QListWidgetItem()
            widget = ConfigOptionWidget(opt["name"], opt["value"], opt["hint"])
            self.option_widgets.append(widget)

            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

        layout.addWidget(self.list_widget)

        self.save_btn.clicked.connect(self.save)
        self.reset_btn.clicked.connect(self.reset)

    def save(self):
        values = {w.label.text(): w.get_value() for w in self.option_widgets}
        print("Saved config:", values)

    def reset(self):
        for i, opt in enumerate(self.options):
            self.option_widgets[i].set_value(opt["value"])

    def closeEvent(self, event):
        if self.on_close_callback:
            self.on_close_callback()
        return super().closeEvent(event)
