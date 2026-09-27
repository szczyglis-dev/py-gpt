"""Embedded image and audio/video viewers."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QWidget, QVBoxLayout,
                              QHBoxLayout, QPushButton, QSlider, QLabel)
from pygpt_net.utils import trans


class ImagePreview(QGraphicsView):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            raise ValueError(reader.errorString())
        scene = QGraphicsScene(self)
        scene.addPixmap(QPixmap.fromImage(image))
        self.setScene(scene)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.manual_zoom = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.manual_zoom:
            self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event):
        self.manual_zoom = True
        factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
        self.scale(factor, factor)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.manual_zoom = False
        self.fitInView(self.scene().itemsBoundingRect(), Qt.KeepAspectRatio)


class MediaPreview(QWidget):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PySide6.QtMultimediaWidgets import QVideoWidget
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        video = QVideoWidget(self)
        self.player.setVideoOutput(video)
        layout = QVBoxLayout(self)
        layout.addWidget(video, 1)
        self.error = QLabel()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        controls = QHBoxLayout()
        self.play = QPushButton('▶')
        self.play.setToolTip(trans('files.preview.play'))
        self.play.clicked.connect(self.toggle)
        self.player.playbackStateChanged.connect(lambda state: self.play.setText(
            '❚❚' if state == QMediaPlayer.PlayingState else '▶'))
        controls.addWidget(self.play)
        self.seek = QSlider(Qt.Horizontal)
        self.player.durationChanged.connect(lambda duration: self.seek.setRange(0, duration))
        self.player.positionChanged.connect(lambda pos: self.seek.setValue(pos) if not self.seek.isSliderDown() else None)
        self.seek.sliderMoved.connect(self.player.setPosition)
        controls.addWidget(self.seek, 1)
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(100)
        self.volume.setMaximumWidth(100)
        self.volume.setToolTip(trans('files.preview.volume'))
        self.volume.valueChanged.connect(lambda value: self.audio.setVolume(value / 100))
        controls.addWidget(self.volume)
        layout.addLayout(controls)
        self.player.errorOccurred.connect(lambda *_: self.error.setText(
            trans('files.preview.unsupported') + '\n' + self.player.errorString()))
        self.player.setSource(QUrl.fromLocalFile(path))

    def toggle(self):
        from PySide6.QtMultimedia import QMediaPlayer
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop(self):
        self.player.stop()
        self.player.setSource(QUrl())
