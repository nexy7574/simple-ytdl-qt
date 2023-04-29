from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class ConsoleOutput(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setWordWrapMode(QTextOption.NoWrap)
        self.setAcceptRichText(False)
        self.setFont(QFont("Consolas", 10))
        self.setGeometry(0, 0, 800, 600)
        self.setMinimumHeight(400)
        self.setMinimumWidth(600)

    def write(self, text):
        self.append(text)

    def overwrite_line(self, text):
        self.moveCursor(QTextCursor.End)
        self.moveCursor(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
        self.insertPlainText(text)

    def flush(self):
        pass

    def clear(self):
        self.setPlainText("")

    def get_text(self):
        return self.toPlainText()

    def set_text(self, text):
        self.setPlainText(text)

    def append_text(self, text):
        self.append(text)


class ProgressBar(QProgressBar):
    def __init__(self, parent=None, _format: str = "%p%"):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setAlignment(Qt.AlignCenter)
        self.setFormat(_format)
        self.setToolTip("Downloading: ")

    def set_value(self, value):
        self.setValue(round(value))

    def setDownloading(self, text):
        self.setToolTip("Downloading: " + text)

    def get_value(self):
        return self.value()


class Console(QWidget):
    def __init__(self, parent=None, thread=None):
        super().__init__(parent)
        self.thread = thread
        self.init_ui()
        self.playlist_progress: ProgressBar

    def set_playlist_progress(self, progress):
        self.playlist_progress.set_value(progress)
        if not self.playlist_progress.isVisible():
            self.playlist_progress.setVisible(True)

    def set_playlist_max(self, _max):
        self.playlist_progress.setMaximum(_max)

    def close(self):
        self.setDisabled(True)
        if self.thread:
            try:
                if self.thread.isRunning():
                    print("Thread is running - terminating")
                    self.thread.terminate()
                    self.thread.wait()
                    print("Thread terminated.")
            except RuntimeError:
                print("Thread already terminated")
                pass
        self.setDisabled(False)
        super().close()

    def init_ui(self):
        self.setMinimumSize(400, 100)
        self.output = ConsoleOutput(self)

        # add a close button to the window
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.close)

        # add a clear button to the window
        self.clear_button = QPushButton("Clear", self)
        self.clear_button.clicked.connect(self.output.clear)

        # progress bar
        self.progress_bar = ProgressBar(self)

        self.playlist_progress = ProgressBar(self, "%p% (%v/%m)")
        self.playlist_progress.setMaximum(1)
        self.playlist_progress.setToolTip("Number of videos downloaded: ")
        self.playlist_progress.setVisible(False)

        def toggle_console():
            self.output.setVisible(not self.output.isVisible())
            self.window().adjustSize()

        self.toggle_console_output = QPushButton("Toggle Console Output", self)
        self.toggle_console_output.clicked.connect(
            toggle_console
        )

        # add to layout
        layout = QGridLayout()
        layout.addWidget(self.close_button, 0, 0, 1, 2)
        layout.addWidget(self.clear_button, 0, 2, 1, 2)
        layout.addWidget(self.playlist_progress, 1, 0, 1, 4)
        layout.addWidget(self.progress_bar, 2, 0, 1, 4)
        layout.addWidget(self.output, 3, 0, 1, 4)
        layout.addWidget(self.toggle_console_output, 4, 0, 1, 4)
        # align buttons to centre
        layout.setAlignment(Qt.AlignVCenter)
        self.setLayout(layout)

        # set window properties
        self.setWindowTitle("Console")
        # self.setWindowIcon(QIcon("assets/icon.png"))
        self.setWindowFlags(Qt.Window)
        self.resize(800, 600)
        self.show()
