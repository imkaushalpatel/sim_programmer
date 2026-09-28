from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class CommandWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    @pyqtSlot()
    def run(self):
        try:
            self.finished.emit(self.fn())
        except Exception as exc:
            self.failed.emit(str(exc))
