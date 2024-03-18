#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.18 03:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout,
                               QFileDialog, QSlider, QLabel, QStyle, QSizePolicy)

class VideoPlayerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mediaPlayer = QMediaPlayer()
        self.loaded = False

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(200)
        self.update_timer.timeout.connect(self.update_ui)

        self.videoWidget = QVideoWidget()
        self.videoWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.playPauseButton = QPushButton()
        self.playPauseButton.setEnabled(False)
        self.update_play_pause_icon()

        self.stopButton = QPushButton()
        self.stopButton.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stopButton.setEnabled(False)

        self.openButton = QPushButton("Open Video...")

        self.labelDuration = QLabel()
        self.labelCurrentTime = QLabel()

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)

        # layout
        controlLayout = QHBoxLayout()
        controlLayout.addWidget(self.openButton)
        controlLayout.addWidget(self.playPauseButton)
        controlLayout.addWidget(self.stopButton)

        sliderLayout = QHBoxLayout()
        sliderLayout.addWidget(self.labelCurrentTime)
        sliderLayout.addWidget(self.slider)
        sliderLayout.addWidget(self.labelDuration)

        layout = QVBoxLayout()
        layout.addWidget(self.videoWidget)
        layout.addLayout(sliderLayout)
        layout.addLayout(controlLayout)
        self.setLayout(layout)

        self.bind_signals()

    def bind_signals(self):
        """Bind signals"""
        self.openButton.clicked.connect(self.open_file)
        self.playPauseButton.clicked.connect(self.toggle_play_pause)
        self.stopButton.clicked.connect(self.stop_video)
        self.slider.sliderMoved.connect(self.set_position)
        # self.videoWidget.mousePressEvent = self.video_widget_clicked

        # connect signals
        self.mediaPlayer.positionChanged.connect(self.position_changed)
        self.mediaPlayer.durationChanged.connect(self.duration_changed)
        self.mediaPlayer.playbackStateChanged.connect(self.on_playback_state_changed)

        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.mediaStatusChanged.connect(self.media_status_changed)

    def media_status_changed(self, status):
        """
        Media status changed

        :param status: status
        """
        if status == QMediaPlayer.LoadedMedia and not self.loaded:
            self.loaded = True
            self.play_video()

    def open_file(self):
        """Open file"""
        self.loaded = False
        path, _ = QFileDialog.getOpenFileName(self, "Open Video")
        if path:
            self.open(path)

    def open(self, path: str):
        """
        Open video

        :param path: video path
        """
        self.reset()
        self.mediaPlayer.setSource(QUrl.fromLocalFile(path))
        self.playPauseButton.setEnabled(True)
        self.stopButton.setEnabled(True)

    def play_video(self):
        """Play video"""
        self.mediaPlayer.play()
        self.on_playback_state_changed()  # update icon when play/pause is toggled.

    def reset(self):
        """Reset"""
        self.loaded = False
        self.playPauseButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.update_timer.stop()
        self.mediaPlayer.stop()
        self.mediaPlayer.setSource(QUrl())
        self.slider.setValue(0)
        self.labelCurrentTime.setText(self.format_time(0))
        self.labelDuration.setText(self.format_time(0))

    def toggle_play_pause(self):
        """Toggle play/pause"""
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()
        self.on_playback_state_changed()  # update icon when play/pause is toggled.

    def stop_video(self):
        """Stop video"""
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlayingState or self.mediaPlayer.playbackState() == QMediaPlayer.PausedState:
            self.mediaPlayer.stop()

        self.slider.setValue(0)
        self.labelCurrentTime.setText(self.format_time(0))
        self.update_play_pause_icon()

    def on_playback_state_changed(self):
        """Playback state changed"""
        self.update_play_pause_icon()

    def update_play_pause_icon(self):
        """Update play/pause icon"""
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlayingState:
            self.playPauseButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.update_timer.start()
        else:
            self.playPauseButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.update_timer.stop()

    def video_widget_clicked(self, event):
        """
        Video widget clicked

        :param event: event
        """
        self.toggle_play_pause()

    def position_changed(self, position):
        """
        Position changed

        :param position: position
        """
        self.slider.setValue(position)
        self.labelCurrentTime.setText(self.format_time(position))

    def duration_changed(self, duration):
        """
        Duration changed

        :param duration: duration
        """
        self.slider.setRange(0, duration)
        self.labelDuration.setText(self.format_time(duration))

    def set_position(self, position):
        """
        Set position

        :param position: position
        """
        self.mediaPlayer.setPosition(position)

    def update_ui(self):
        """Update UI"""
        # sync slider with the video time
        self.position_changed(self.mediaPlayer.position())

    def format_time(self, ms):
        """
        Format time

        :param ms: milliseconds
        """
        # convert milliseconds to hours:minutes:seconds format
        seconds = (ms // 1000) % 60
        minutes = (ms // 60000) % 60
        hours = (ms // 3600000)
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)