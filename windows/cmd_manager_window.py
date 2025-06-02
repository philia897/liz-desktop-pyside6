import json
from typing import List, Dict, Set, Optional
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QTableView, QTableWidgetItem, QLineEdit, QLabel, QMenu, QDialog, 
                              QMessageBox, QInputDialog, QFileDialog, QHeaderView)
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QSortFilterProxyModel, Signal, QPoint
from PySide6.QtGui import QAction
from bluebird import *
from windows.base import Shortcut

class EditDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Shortcut")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Application
        self.app_label = QLabel("Application:")
        self.app_input = QLineEdit()
        layout.addWidget(self.app_label)
        layout.addWidget(self.app_input)
        
        # Description
        self.desc_label = QLabel("Description:")
        self.desc_input = QLineEdit()
        layout.addWidget(self.desc_label)
        layout.addWidget(self.desc_input)
        
        # Command
        self.command_label = QLabel("Shortcut:")
        self.command_input = QLineEdit()
        layout.addWidget(self.command_label)
        layout.addWidget(self.command_input)
        
        # Comment
        self.comment_label = QLabel("Comment:")
        self.comment_input = QLineEdit()
        layout.addWidget(self.comment_label)
        layout.addWidget(self.comment_input)
        
        # Hit Count
        self.hit_label = QLabel("Hit Count:")
        self.hit_input = QLineEdit()
        self.hit_input.setText("0")
        layout.addWidget(self.hit_label)
        layout.addWidget(self.hit_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Connections
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

class AppTableModel(QAbstractTableModel):
    def __init__(self, data: List[Shortcut]):
        super().__init__()
        self.headers = ["Application", "Description", "Shortcut", "Hits"]
        self._data: List[Shortcut] = data  # List of lists or dicts

    def add_item(self, item):
        self.beginInsertRows(self.index(len(self._data), 0).parent(), len(self._data), len(self._data))
        self._data.append(item)
        self.endInsertRows()

    def modify_row(self, row, new_data):
        if 0 <= row < len(self._data):
            self._data[row] = new_data
            top_left = self.index(row, 0)
            bottom_right = self.index(row, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole])

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        item = self._data[row]

        if role == Qt.DisplayRole:
            if col == 0:
                return item.application
            elif col == 1:
                return item.description
            elif col == 2:
                return item.shortcut
            elif col == 3:
                return item.hit_number
            else:
                return "Invalid col " + col
        if role == Qt.UserRole:
            return item

        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def reset_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

class AppFilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._filter = ""

    def setFilterString(self, text: str):
        self._filter = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        for column in range(self.sourceModel().columnCount()):
            index = self.sourceModel().index(row, column)
            if self._filter.lower() in str(self.sourceModel().data(index, Qt.DisplayRole)).lower():
                return True
        return False

class ShortcutManager(QWidget):
    def __init__(self, parent, on_close_callback=None):
        super().__init__()
        self.setWindowTitle("Shortcut Manager")
        self.resize(parent.width(), parent.height())
        self.parent = parent
        self.flute = parent.flute

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.on_close_callback = on_close_callback
        
        self.setup_ui()
        self.setup_connections()

    def closeEvent(self, event):
        if self.on_close_callback:
            self.on_close_callback()
        return super().closeEvent(event)

    def setup_table_view(self):
        data = self.fetch_shortcuts("")
        self.model = AppTableModel(data)
        self.proxy = AppFilterProxyModel()
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)        # "Application"
        header.setSectionResizeMode(1, QHeaderView.Stretch)      # "Description"
        header.setSectionResizeMode(2, QHeaderView.Stretch)      # "Shortcut"
        header.setSectionResizeMode(3, QHeaderView.Fixed)        # "Hits"

        # Set fixed widths for 1st and last column
        self.table.setColumnWidth(0, 150)  # Application
        self.table.setColumnWidth(3, 40)   # Hits

        self.table.setWordWrap(True)
        self.table.resizeRowsToContents()  # Adjust height for wrapped lines

    def setup_ui(self):
        
        main_layout = QVBoxLayout(self)
        
        # Top bar with menu and search
        top_bar = QHBoxLayout()
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search shortcuts...")
        top_bar.addWidget(self.search_box)
        
        # Counter
        self.counter_label = QLabel("0 / 0")
        top_bar.addWidget(self.counter_label)

        # Close button
        self.close_button = QPushButton("×")
        self.close_button.setFixedWidth(40)
        top_bar.addWidget(self.close_button)
        
        main_layout.addLayout(top_bar)
        
        # Table
        self.setup_table_view()
        main_layout.addWidget(self.table)
        
        # Edit dialog
        self.edit_dialog = EditDialog(self)
    
        # Context menu
        self.context_menu = QMenu(self)

        self.update_counter()
        
    def setup_connections(self):
        self.close_button.clicked.connect(self.close)
        # self.search_box.returnPressed.connect(self.on_search)
        self.search_box.textChanged.connect(self.proxy.setFilterString)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.selectionModel().selectionChanged.connect(self.update_counter)
    
    def update_counter(self):
        total_shortcuts = len(self.table.selectionModel().selectedRows())
        self.counter_label.setText(f"{total_shortcuts} / {self.model.rowCount()}")
    
    def make_default_if_none(self):
        # Get new ID from backend
        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='new_id',
            args=[]
        ))
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to get ID: {'; '.join(response.results)}")
            return
        
        new_id = response.results[0]
        
        # Create new shortcut
        shortcut = Shortcut(
            id=new_id,
            hit_number=0,
            shortcut="[STR]+ Liz and the Blue Bird",
            application="Welcome",
            description="Liz and the Blue Bird",
            comment="Welcome message from Liz (created when list is none)"
        )
        
        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='create_shortcuts',
            args=[json.dumps(shortcut.__dict__)]
        ))
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to create shortcut: {'; '.join(response.results)}")
            return

    def fetch_shortcuts(self, query: str) -> List[Shortcut]:
        # This would be replaced with actual backend calls in a real implementation
        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='get_shortcut_details',
            args=[query]
        ))
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to retrieve shortcuts because {'; '.join(response.results)}")
            return
        
        if len(response.results) == 0:
            self.make_default_if_none()
            return self.fetch_shortcuts("")

        shortcuts = [Shortcut(**json.loads(content)) for content in response.results]

        return shortcuts
    
    def show_context_menu(self, pos: QPoint):
        global_pos = self.table.viewport().mapToGlobal(pos)
        
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        
        # Create context menu
        menu = QMenu(self)
        
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self.open_edit_dialog(index))
        
        delete_action = QAction("Delete Selected", self)
        delete_action.triggered.connect(self.delete_selected_rows)
        
        new_action = QAction("New Item", self)
        new_action.triggered.connect(self.create_new_command)
        
        export_action = QAction("Export Selected", self)
        export_action.triggered.connect(self.export_selected_rows)
        
        import_action = QAction("Import Local", self)
        import_action.triggered.connect(self.import_from_file)
        
        menu.addAction(new_action)
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        menu.addAction(export_action)
        menu.addAction(import_action)
        
        menu.exec_(global_pos)

    def open_edit_dialog(self, idx):

        source_index = self.proxy.mapToSource(idx)
        shortcut: Shortcut = self.model._data[source_index.row()]
        
        self.edit_dialog.app_input.setText(shortcut.application)
        self.edit_dialog.desc_input.setText(shortcut.description)
        self.edit_dialog.command_input.setText(shortcut.shortcut)
        self.edit_dialog.comment_input.setText(shortcut.comment)
        self.edit_dialog.hit_input.setText(str(shortcut.hit_number))
        
        if self.edit_dialog.exec_() == QDialog.Accepted:
            self.save_edit(shortcut.id, source_index.row())
    
    def create_new_command(self):
        self.edit_dialog.app_input.clear()
        self.edit_dialog.desc_input.clear()
        self.edit_dialog.command_input.clear()
        self.edit_dialog.comment_input.clear()
        self.edit_dialog.hit_input.setText("0")
        
        if self.edit_dialog.exec_() == QDialog.Accepted:
            self.save_new_command()
    
    def save_edit(self, shortcut_id, row):
        app = self.edit_dialog.app_input.text()
        desc = self.edit_dialog.desc_input.text()
        command = self.edit_dialog.command_input.text()
        comment = self.edit_dialog.comment_input.text()
        hit_str = self.edit_dialog.hit_input.text()
        
        try:
            hit = int(hit_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Hit count must be a number")
            return
        
        shortcut = Shortcut(
            id=shortcut_id,
            hit_number=hit,
            shortcut=command,
            application=app,
            description=desc,
            comment=comment
        )
        
        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='update_shortcuts',
            args=[json.dumps(shortcut.__dict__)]
        ))
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to update shortcut: {'; '.join(response.results)}")
            return

        self.model.modify_row(row, shortcut)

    def save_new_command(self):
        app = self.edit_dialog.app_input.text()
        desc = self.edit_dialog.desc_input.text()
        command = self.edit_dialog.command_input.text()
        comment = self.edit_dialog.comment_input.text()
        hit_str = self.edit_dialog.hit_input.text()
        
        try:
            hit = int(hit_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Hit count must be a number")
            return
        
        # Get new ID from backend
        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='new_id',
            args=[]
        ))
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to get ID: {'; '.join(response.results)}")
            return
        
        new_id = response.results[0]
        
        # Create new shortcut
        shortcut = Shortcut(
            id=new_id,
            hit_number=hit,
            shortcut=command,
            application=app,
            description=desc,
            comment=comment
        )
        
        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='create_shortcuts',
            args=[json.dumps(shortcut.__dict__)]
        ))
        
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to create shortcut: {'; '.join(response.results)}")
            return
        
        self.model.add_item(shortcut)

    def get_ids_of_selected_rows(self):
        selected = self.table.selectionModel().selectedRows()
        ids = []
        if selected:
            for proxy_index in selected:
                # Remove from model using source index
                source_index = self.proxy.mapToSource(proxy_index)
                ids.append(self.model._data[source_index.row()].id)
        return ids

    def delete_selected_rows(self):

        selected = self.table.selectionModel().selectedRows()
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the selected {len(selected)} shortcuts?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return

        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='delete_shortcuts',
            args=self.get_ids_of_selected_rows()
        ))
        
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to delete shortcuts: {'; '.join(response.results)}")
            return
        
        if selected:
            for proxy_index in selected:
                # Remove from model using source index
                source_index = self.proxy.mapToSource(proxy_index)

                self.model.beginRemoveRows(source_index.parent(), source_index.row(), source_index.row())
                del self.model._data[source_index.row()]
                self.model.endRemoveRows()
    
    def export_selected_rows(self):
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Shortcuts",
            "",
            "JSON Files (*.json);;Text Files (*.txt)"
        )
        
        if not file_path:
            return

        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='export_shortcuts',
            args=[file_path] + self.get_ids_of_selected_rows()
        ))
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to export shortcuts: {'; '.join(response.results)}")
    
    def import_from_file(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Shortcuts",
            "",
            "JSON Files (*.json);;Text Files (*.txt)"
        )
        
        if not file_paths:
            return

        response:BlueBirdResponse = self.flute.play(LizCommand(
            action='import_shortcuts',
            args=file_paths
        ))
        
        if response.code != StateCode.OK:
            QMessageBox.critical(self, "Error", f"Failed to import shortcuts: {'; '.join(response.results)}")
        else:
            self.model.reset_data(self.fetch_shortcuts(""))