from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, 
                              QLineEdit, QListView, QApplication,
                              QStyledItemDelegate, QStyleOptionViewItem, QStyle)
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QSortFilterProxyModel, QTimer, QPoint, QRect, QEvent
from PySide6.QtGui import QPainter, QFont, QTextOption, QPainterPath
from notifypy import Notify
from rapidfuzz.fuzz import partial_ratio
from bluebird import *

import json
from dataclasses import dataclass, field
from typing import List
from windows.base import Shortcut


class AppItemDelegate(QStyledItemDelegate):
    def __init__(self):
        super().__init__()
        self.text_option_left = QTextOption(Qt.AlignLeft | Qt.AlignVCenter)
        self.text_option_left.setWrapMode(QTextOption.WordWrap)
        self.text_option_right = QTextOption(Qt.AlignRight | Qt.AlignVCenter)
        self.text_option_right.setWrapMode(QTextOption.WordWrap)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        item = index.model().data(index, Qt.UserRole)
        if item is None:
            return super().paint(painter, option, index)

        painter.save()

        # Draw selection background
        # if option.state & QStyle.State_MouseOver :
        #     path = QPainterPath()
        #     path.addRoundedRect(option.rect, 8, 8)
        #     painter.setRenderHint(QPainter.Antialiasing)
        #     painter.fillPath(path, option.palette.highlight())
        if option.state & QStyle.State_Selected:
            path = QPainterPath()
            path.addRoundedRect(option.rect.adjusted(2, 2, -2, -2), 8, 8)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillPath(path, option.palette.highlight())

        rect = option.rect.adjusted(5, 5, -5, -5)

        left_rect = QRect(rect.left(), rect.top(), rect.width() * 0.8, rect.height())
        painter.setPen(option.palette.text().color())
        painter.drawText(left_rect, f"{item.application}> {item.description}", self.text_option_left)

        right_rect = QRect(left_rect.right(), rect.top(), rect.width() * 0.2, rect.height())
        painter.setPen(Qt.darkGray)
        painter.drawText(right_rect, item.shortcut, self.text_option_right)

        painter.restore()


class AppListModel(QAbstractListModel):
    def __init__(self, items: List[Shortcut] = None):
        super().__init__()
        self._items = items or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        item = self._items[index.row()]
        if role == Qt.DisplayRole:
            return f"{item.description} | {item.shortcut} ({item.hit_number})"
        if role == Qt.UserRole:
            return item

        return None

class AppFilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._filter = ""

    def setFilterString(self, text: str):
        self._filter = text.lower()
        self.invalidateFilter()
        self.sort(0)

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._filter:
            return True

        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        item = model.data(index, Qt.UserRole)
        if not item:
            return False

        # Fuzzy matching score
        score = partial_ratio(self._filter, item.searchable_text.lower())
        return score > 80  # You can adjust this threshold

    def lessThan(self, left_index, right_index):
        model = self.sourceModel()
        left_item = model.data(left_index, Qt.UserRole)
        right_item = model.data(right_index, Qt.UserRole)

        if not left_item or not right_item:
            return False

        # Sort descending by hit count
        return left_item.hit_number > right_item.hit_number


class MainWindow(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent  # Reference to main window
        self.setup_ui()
        
    def fetch_data(self) -> List[Shortcut]:
        cmd = LizCommand(action="get_shortcut_details", args=[])
        resp: BlueBirdResponse = self.parent.flute.play(cmd)
        if (resp.code != StateCode.OK):
            self.show_notification("Liz Error", f"{resp.code}: {resp.results}")
            return []
        return [
            Shortcut(**json.loads(item)) for item in resp.results
        ]

    def setup_sc_items_view(self):
        items = self.fetch_data()
        self.model = AppListModel(items)
        self.proxy = AppFilterProxy()
        self.proxy.setSourceModel(self.model)
        self.proxy.setDynamicSortFilter(True)

        self.view = QListView()
        self.view.setModel(self.proxy)
        self.view.setItemDelegate(AppItemDelegate())
        self.view.setMouseTracking(True)
        self.view.clicked.connect(self.on_item_clicked)

        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy().ScrollBarAlwaysOff)
        self.view.setResizeMode(QListView.Adjust)  # Object inside to adjust to view's size
        self.view.setSelectionMode(QListView.SingleSelection)
        self.view.setSelectionBehavior(QListView.SelectRows)
        self.view.setFocusPolicy(Qt.StrongFocus)  # Enables keyboard focus

        # Select the first item
        if self.model.rowCount() > 0:
            first_index = self.proxy.index(0, 0)
            self.view.setCurrentIndex(first_index)
        

    def setup_ui(self):
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        self.setup_sc_items_view()

        # Search bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setObjectName("searchbar")
        self.search_bar.setPlaceholderText("Typing to search...")
        self.search_bar.textChanged.connect(self.proxy.setFilterString)
        self.search_bar.installEventFilter(self)
        layout.addWidget(self.search_bar)
        
        # Application list
        layout.addWidget(self.view)
        
    def on_item_clicked(self, proxy_index):
        source_index = self.proxy.mapToSource(proxy_index)
        item = self.model.data(source_index, Qt.UserRole)

        def play_command(proxy, item):
            cmd = LizCommand(action="execute", args=[item.id])
            resp: BlueBirdResponse = self.parent.flute.play(cmd)
            if resp.code != StateCode.OK:
                show_notification("Failed to Execute", resp.results)
                return
            item.hit_number = Shortcut(**json.loads(resp.results[0])).hit_number

            proxy.invalidate()  # Reapply filter and sorting
            proxy.sort(0)

        if item:
            self.parent.hide()
            self.search_bar.selectAll()
            QTimer.singleShot(0, lambda: play_command(self.proxy, item))

    def eventFilter(self, obj, event):
        if obj == self.search_bar and event.type() == QEvent.KeyPress:
            key = event.key()
            current = self.view.currentIndex()
            row = current.row()

            if key == Qt.Key_Down:
                row = min(row + 1, self.proxy.rowCount() - 1)
                self.view.setCurrentIndex(self.proxy.index(row, 0))
                return True

            elif key == Qt.Key_Up:
                row = max(row - 1, 0)
                self.view.setCurrentIndex(self.proxy.index(row, 0))
                return True

            elif key in (Qt.Key_Return, Qt.Key_Enter):
                # Optional: simulate click
                self.on_item_clicked(self.view.currentIndex())
                return True

        return super().eventFilter(obj, event)


    def show_notification(self, title, text):
        """System notification"""
        notification = Notify()
        notification.title = title
        notification.message = text
        notification.send()