import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QSystemTrayIcon, QMenu, QVBoxLayout
from PySide6.QtGui import QIcon, QKeySequence, QAction
from PySide6.QtCore import QTimer, QMetaObject, Qt
from windows.main_window import MainWindow
from windows.config_window import ConfigWindow
from windows.cmd_manager_window import ShortcutManager
from windows.signals import global_signal_bus
from bluebird import Flute, LizCommand

from pynput import keyboard
import threading

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent
    
    return str(base_path / relative_path)

class LizDesktop(QMainWindow):
    def __init__(self, flute:Flute, icon_file:str):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.flute: Flute = flute

        # Desired size
        width = 700
        height = 600

        self.set_geometry(width, height)

        self.load_theme()
        
        # Setup tray icon
        self.setup_tray(icon_file)

        # Track window focus
        self.installEventFilter(self)
        
        # Initialize pages
        self.main_window = MainWindow(self)
        self.config_window = None
        self.shortcut_manager_window = None

        self.setCentralWidget(self.main_window)

        # self.open_config()

    def set_geometry(self, width, height):
        # Get screen geometry
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # Calculate center position
        x = (screen_geometry.width() - width) // 2
        y = (screen_geometry.height() - height) // 2

        # Set window geometry
        self.setGeometry(x, y, width, height)

    def open_config(self):
        if self.config_window is None:
            self.config_window = ConfigWindow(self, self.flute,
                            on_close_callback=self.on_config_closed)
            self.config_window.show()
            self.config_window.raise_()
            self.config_window.activateWindow()

    def on_config_closed(self):
        self.config_window = None

    def open_shortcut_manager(self):
        if self.shortcut_manager_window is None:
            self.shortcut_manager_window = ShortcutManager(self,
                on_close_callback=self.on_shortcut_manager_closed)
            self.shortcut_manager_window.show()
            self.shortcut_manager_window.raise_()
            self.shortcut_manager_window.activateWindow()

    def on_shortcut_manager_closed(self):
        self.shortcut_manager_window = None

    def load_theme(self):
        """Toggle between light/dark mode based on system preference"""
        if self.is_dark_mode():
            self.apply_theme("dark")
        else:
            self.apply_theme("light")
            
    def is_dark_mode(self):
        """Detect system dark mode (simplified)"""
        return True  # Implement proper detection for your OS
            
    def apply_theme(self, mode):
        with open(resource_path(f"theme/{mode}.qss"), "r") as f:
            self.setStyleSheet(f.read())
        
    def setup_tray(self, icon_file):
        # Create tray icon
        self.tray = QSystemTrayIcon(QIcon(icon_file), self)
        self.tray.setToolTip("Liz Shortcut Helper")
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Show action
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_main)
        tray_menu.addAction(show_action)
        
        # Shortcut manager action
        shortcut_manager_action = QAction("Manage", self)
        shortcut_manager_action.triggered.connect(self.open_shortcut_manager)
        tray_menu.addAction(shortcut_manager_action)

        # Config action
        config_action = QAction("Config", self)
        config_action.triggered.connect(self.open_config)
        tray_menu.addAction(config_action)

        # Quit action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray.setContextMenu(tray_menu)
        self.tray.show()

    def show_main(self):
        self.show()
        self.activateWindow()
        self.raise_()

    def quit_app(self):
        cmd = LizCommand("persist", [])
        self.flute.play(cmd)
        self.tray.hide()
        QApplication.quit()

    def hide(self):
        global_signal_bus.aboutToHide.emit()
        super().hide()

    # Override close to hide instead of quit
    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()

    def eventFilter(self, obj, event):
        # Hide when window loses focus
        if obj is self and event.type() == event.Type.WindowDeactivate:
            QTimer.singleShot(100, self._try_hide_on_blur)
        return super().eventFilter(obj, event)
    
    def _try_hide_on_blur(self):
        if not self.tray.contextMenu().isVisible(): # Don't hide if clicking tray menu
            self.hide()

# Global shortcut handler using pynput
def listen_for_shortcut(app_window):
    COMBO = keyboard.HotKey.parse('<ctrl>+<alt>+l')

    def on_activate():
        print("Hotkey triggered")

        # Safely invoke show from the Qt event loop
        QMetaObject.invokeMethod(
            window,
            "show_main",  # this should be a slot or method
            Qt.QueuedConnection
        )

    hotkey = keyboard.HotKey(
        COMBO,
        on_activate)

    def for_canonical(f):
        return lambda k: f(listener.canonical(k))

    with keyboard.Listener(on_press=for_canonical(hotkey.press), on_release=for_canonical(hotkey.release)) as listener:
        listener.join()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) 

    icon_file = resource_path("resources/icon_1024.png")
    app.setWindowIcon(QIcon(icon_file))

    flute = Flute.create_flute(None)

    window = LizDesktop(flute, icon_file)
    window.show()

    # Launch the global shortcut listener in a separate thread
    listener_thread = threading.Thread(target=listen_for_shortcut, args=(window,), daemon=True)
    listener_thread.start()

    sys.exit(app.exec())