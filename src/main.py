import shutil
import sys
import re
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .widgets.download_console import Console

__version__ = "1.2.7"


PROGRESS_RE = re.compile(r"^\[download]\s+([\d.]+).+$")
DOWNLOAD_RE = re.compile(r"^\[info]\s+(\S+)")
PLAYLIST_RE = re.compile(r"\[download]\sDownloading\sitem\s(\d+)\sof\s(\d+)")
SUPPORTED_BROWSERS = [
    "none",
    "brave",
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "opera",
    "vivaldi",
    "safari"
]
SUPPORTED_BROWSERS.sort()  # sort alphabetically
SUPPORTED_BROWSERS = list(
    sorted(
        SUPPORTED_BROWSERS,
        key=lambda entry: (shutil.which(entry) is not None) + list(reversed(SUPPORTED_BROWSERS)).index(entry),
        reverse=True
    )
)  # show browsers that are installed first

ALLOWED_AUDIO_FORMATS = [
    "default",
    "aac",
    "flac",
    "mp3",
    "m4a",
    "opus",
    "vorbis",
    "wav"
]

ALLOWED_VIDEO_FORMATS = [
    "default",
    "bestvideo",
    "worstvideo",
    "best",
    "worst",
    "mp4",
    "flv",
    "webm",
    "mkv"
]


# noinspection PyArgumentList,PyAttributeOutsideInit
class DownloaderThread(QObject):
    finished = pyqtSignal()
    percent = pyqtSignal(float)
    downloading = pyqtSignal(str)
    playlist_current = pyqtSignal(int)
    playlist_total = pyqtSignal(int)
    stdout = pyqtSignal(str)

    def __init__(self, args: list[str], parent):
        super().__init__(parent)
        self.args = args
        self.do_stop = False

    def run(self):
        self.process = subprocess.Popen(
            self.args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        for line in iter(self.process.stdout.readline, ''):  # read one byte at a time
            self.stdout.emit(line)
            match = PROGRESS_RE.match(line)
            if match:
                percent = float(match.group(1))
                self.percent.emit(percent)

            match = DOWNLOAD_RE.match(line)
            if match:
                self.downloading.emit(match.group(1)[:-1])

            match = PLAYLIST_RE.match(line)
            if match:
                self.playlist_current.emit(int(match.group(1)))
                self.playlist_total.emit(int(match.group(2)))

            if self.do_stop:
                self.process.stdout.close()
                self.process.wait()
                break
        else:
            self.process.stdout.close()
            self.process.wait()
        self.finished.emit()

    def terminate(self):
        self.do_stop = True


# noinspection PyAttributeOutsideInit
class MyApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.init_ui()
        self.output_dir = Path.home() / "Downloads"

    @staticmethod
    def get_args(
            url: str,
            output_dir: Path,
            output_fn: str,
            browser: str,
            audio_only: bool,
            audio_format: str,
            audio_quality: str,
            video_format: str,
    ):
        base = [
            "yt-dlp",
            # "--quiet",
            "--abort-on-error",
            "--no-colors",
            "--abort-on-unavailable-fragments",
            "--no-continue",
            "--newline",
            # "--progress"
        ]
        if browser:
            base += [
                "--cookies-from-browser",
                browser
            ]

        if audio_only:
            base += [
                "--no-video",
                "--extract-audio",
                "--audio-quality",
                audio_quality
            ]

        if audio_format != "default":
            base += [
                "--audio-format",
                audio_format
            ]

        if video_format != "default":
            base += [
                "--format",
                video_format
            ]

        base += [
            "--output",
            str(output_dir / output_fn),
            url
        ]
        return base

    # noinspection PyUnresolvedReferences,PyArgumentList
    def init_ui(self):
        layout = QGridLayout()
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText('Enter URL')
        self.url_input.setToolTip('Enter URL')
        layout.addWidget(self.url_input, 0, 0, 1, 2)

        self.download_button = QPushButton('Download', self)
        self.download_button.setToolTip('Download')
        self.download_button.clicked.connect(self.download)
        layout.addWidget(self.download_button, 0, 2, 1, 2)

        # On the row below, ask for the browser the user wants to extract cookies from using a dropdown
        self.browser_label = QLabel("Browser:", self)
        self.browser_label.setToolTip("Browser to extract cookies from")
        layout.addWidget(self.browser_label, 1, 0, 1, 1)
        self.browser_dropdown = QComboBox(self)
        self.browser_dropdown.setToolTip("Browser to extract cookies from")
        self.browser_dropdown.addItems(SUPPORTED_BROWSERS)
        # default to none
        self.browser_dropdown.setCurrentIndex(self.browser_dropdown.findText("none"))
        layout.addWidget(self.browser_dropdown, 1, 1, 1, 1)

        # And ask if the user wants to extract audio
        self.audio_only_checkbox = QCheckBox("Audio Only", self)
        self.audio_only_checkbox.setToolTip("Audio Only")
        layout.addWidget(self.audio_only_checkbox, 1, 2, 1, 1)

        # And then, on the row below, ask for both a video and audio format
        self.video_format_label = QLabel("Video Format:", self)
        self.video_format_label.setToolTip("Video Format")
        layout.addWidget(self.video_format_label, 2, 0, 1, 1)
        self.video_format_dropdown = QComboBox(self)
        self.video_format_dropdown.setToolTip("Video Format")
        self.video_format_dropdown.addItems(ALLOWED_VIDEO_FORMATS)
        # default to 'default'
        self.video_format_dropdown.setCurrentIndex(self.video_format_dropdown.findText("default"))
        layout.addWidget(self.video_format_dropdown, 2, 1, 1, 1)

        self.audio_format_label = QLabel("Audio Format:", self)
        self.audio_format_label.setToolTip("Audio Format")
        layout.addWidget(self.audio_format_label, 2, 2, 1, 1)
        self.audio_format_dropdown = QComboBox(self)
        self.audio_format_dropdown.setToolTip("Audio Format")
        self.audio_format_dropdown.addItems(ALLOWED_AUDIO_FORMATS)
        # default to 'default'
        self.audio_format_dropdown.setCurrentIndex(self.audio_format_dropdown.findText("default"))
        layout.addWidget(self.audio_format_dropdown, 2, 3, 1, 1)

        # On the row below, ask for the directory to save the file to using QFileDialog
        self.output_dir_label = QLabel("Output Directory:", self)
        self.output_dir_label.setToolTip("Output Directory")
        layout.addWidget(self.output_dir_label, 3, 2, 1, 1)
        self.output_dir_button = QPushButton("Select", self)
        self.output_dir_button.setToolTip("Output Directory")
        self.output_dir_button.clicked.connect(self.select_output_dir)
        layout.addWidget(self.output_dir_button, 3, 3, 1, 1)

        # and now ask for the output filename format:
        self.output_fn_label = QLabel("Output Filename Format:", self)
        self.output_fn_label.setToolTip("Output Filename Format")
        layout.addWidget(self.output_fn_label, 4, 0, 1, 1)
        self.output_fn_input = QLineEdit(self)
        self.output_fn_input.setPlaceholderText('Enter Filename Format')
        self.output_fn_input.setToolTip('Enter Filename Format')
        self.output_fn_input.setText("%(title)s.%(ext)s")
        layout.addWidget(self.output_fn_input, 4, 1, 1, 3)

        # simulate download, checkbox
        self.simulate_download_checkbox = QCheckBox("Simulate Download", self)
        self.simulate_download_checkbox.setToolTip("Simulate Download")
        layout.addWidget(self.simulate_download_checkbox, 5, 0, 1, 1)

        self.setLayout(layout)
        if Path("assets/icon.png").exists():
            self.setWindowIcon(QIcon('assets/icon.png'))
        self.setWindowTitle('YTDLP Downloader')
        self.setGeometry(300, 300, 500, 200)
        self.show()

    def select_output_dir(self):
        # noinspection PyTypeChecker
        output_dir = QFileDialog.getExistingDirectory(self, "Select Directory")
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir_label.setText(f"Output Directory: {self.output_dir}")

    # noinspection PyUnresolvedReferences
    def download(self):
        url = self.url_input.text()
        if not url:
            return

        browser = self.browser_dropdown.currentText()
        if browser == "none":
            browser = None

        audio_only = self.audio_only_checkbox.isChecked()

        video_format = self.video_format_dropdown.currentText()
        audio_format = self.audio_format_dropdown.currentText()

        args = self.get_args(
            url=url,
            output_dir=self.output_dir,
            output_fn=self.output_fn_input.text() or "%(title)s.%(ext)s",
            browser=browser,
            audio_only=audio_only,
            audio_format=audio_format,
            audio_quality="0",
            video_format=video_format,
        )

        self.console = Console()
        self.console.show()
        self.console.output.write(" ".join(args))
        self.console.output.write("")

        if self.simulate_download_checkbox.isChecked():
            args.insert(1, "--simulate")

        class _Thread(QThread):
            def __init__(self, parent):
                super().__init__(parent)
                self.worker = None

            def terminate(self):
                self.worker.terminate()
                super().terminate()

        self.thread = _Thread(self)
        self.console.thread = self.thread
        self.worker = DownloaderThread(args, None)
        self.worker.moveToThread(self.thread)
        self.thread.worker = self.worker
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.stdout.connect(self.console.output.overwrite_line)
        self.worker.percent.connect(self.console.progress_bar.set_value)
        self.worker.downloading.connect(self.console.progress_bar.setDownloading)

        self.worker.playlist_total.connect(self.console.set_playlist_max)
        self.worker.playlist_current.connect(self.console.set_playlist_progress)

        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self.console.output.write("Done."))
        self.thread.start()


def main():
    app = QApplication(sys.argv)
    if not shutil.which("yt-dlp"):
        print("yt-dlp not found in $PATH. Unable to continue.", file=sys.stderr)
        QMessageBox.critical(None, "Error", "yt-dlp not found in $PATH. Unable to continue.")
    ex = MyApp()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
