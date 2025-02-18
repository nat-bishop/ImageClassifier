import time

from PySide2 import QtWidgets, QtCore, QtGui

class WorkerThread(QtCore.QThread):
    progress_changed = QtCore.Signal(int)

    def run(self) -> None:
        for i in range(10):
            time.sleep(1)
            self.progress_changed.emit(10*(i+1))


class ProcessWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setTextVisible(False)

        layout.addWidget(self.progress_bar)

        button = QtWidgets.QPushButton('Start')
        button.clicked.connect(self.start)
        layout.addWidget(button)

        def start(self) -> None:
            worker_thread = WorkerThread()
            worker_thread.progress_changed.connect(self.progress_bar.setValue)
            worker_thread.start()
