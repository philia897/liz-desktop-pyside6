from PySide6.QtCore import QObject, Signal

class SignalBus(QObject):
    aboutToHide = Signal()
    fetchAll = Signal()

# Create a global instance
global_signal_bus = SignalBus()