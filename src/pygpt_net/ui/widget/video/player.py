#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.18 10:00:00                  #
# ================================================== #

import os
import shutil

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout,
                               QFileDialog, QSlider, QLabel, QStyle, QSizePolicy, QMenu, QMessageBox)

class VideoPlayerWidget(QWidget):
    def __init__(self, window=None):
        super().__init__(window)
        self.window = window
        self.mediaPlayer = QMediaPlayer(window)
        self.mediaPlayer.setLoops(QMediaPlayer.Loops.Infinite)
        self.loaded = False
        self.path = None
        self.stopped = False

        self.audioOutput = QAudioOutput(window)

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(200)
        self.update_timer.timeout.connect(self.update_ui)

        self.autoplay_timer = QTimer(self)
        self.autoplay_timer.setInterval(1000)
        self.autoplay_timer.setSingleShot(True)
        self.autoplay_timer.timeout.connect(self.after_loaded)

        self.videoWidget = QVideoWidget(window)
        self.videoWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.videoWidget.setMinimumSize(640, 480)

        self.playPauseButton = QPushButton()
        self.playPauseButton.setEnabled(False)
        self.update_play_pause_icon()

        self.stopButton = QPushButton()
        self.stopButton.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stopButton.setEnabled(False)

        self.openButton = QPushButton("Open Video...")

        self.labelDuration = QLabel()
        self.labelCurrentTime = QLabel()

        self.labelPath = QLabel()

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setToolTip('Adjust volume')

        self.mute_button = QPushButton()
        self.mute_button.setIcon(QIcon(':/icons/mute.svg'))
        self.mute_button.setCheckable(True)

        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(self.mute_button)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.labelPath)
        bottom_layout.addStretch()
        bottom_layout.addLayout(volume_layout)

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
        layout.addLayout(bottom_layout)
        self.setLayout(layout)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        self.bind_signals()

    def bind_signals(self):
        """Bind signals"""
        self.openButton.clicked.connect(self.open_file)
        self.playPauseButton.clicked.connect(self.toggle_play_pause)
        self.stopButton.clicked.connect(self.stop_video)
        self.slider.sliderMoved.connect(self.set_position)
        self.videoWidget.mousePressEvent = self.video_widget_clicked

        # connect signals
        self.mediaPlayer.positionChanged.connect(self.position_changed)
        self.mediaPlayer.durationChanged.connect(self.duration_changed)
        self.mediaPlayer.playbackStateChanged.connect(self.on_playback_state_changed)
        self.mediaPlayer.mediaStatusChanged.connect(self.media_status_changed)

        self.mediaPlayer.setAudioOutput(self.audioOutput)
        self.mediaPlayer.setVideoOutput(self.videoWidget)

        self.volume_slider.valueChanged.connect(self.adjust_volume)
        self.mute_button.toggled.connect(self.audioOutput.setMuted)

    def open_file(self):
        """Open file"""
        path, _ = QFileDialog.getOpenFileName(self, "Open Video")
        if path:
            self.open(path)

    def open(self, path: str):
        """
        Open video

        :param path: video path
        """
        self.loaded = False
        self.stopped = False
        self.reset()
        self.path = path
        self.update_label_path()
        self.mediaPlayer.setSource(QUrl.fromLocalFile(path))
        self.playPauseButton.setEnabled(True)
        self.stopButton.setEnabled(True)
        self.autoplay_timer.start()
        self.update()

    def play_video(self):
        """Play video"""
        self.mediaPlayer.play()
        self.on_playback_state_changed()

    def reset(self):
        """Reset player to default state"""
        if self.mediaPlayer.source():
            self.mediaPlayer.stop()
            self.mediaPlayer.setSource(QUrl())
        self.update_play_pause_icon()
        self.slider.setValue(0)

    def reset_player(self):
        if self.mediaPlayer is not None:
            if self.mediaPlayer.playbackState() == QMediaPlayer.PlayingState:
                self.mediaPlayer.stop()
            self.mediaPlayer.setSource(QUrl())

    def on_context_menu(self, point):
        context_menu = QMenu(self)
        save_as_action = QAction('Save as...', self)
        save_as_action.triggered.connect(self.save_as_action_triggered)
        # full_screen_action = QAction('Fullscreen', self)
        # full_screen_action.triggered.connect(self.toggle_fullscreen)
        context_menu.addAction(save_as_action)
        # context_menu.addAction(full_screen_action)
        context_menu.exec(self.mapToGlobal(point))

    def adjust_volume(self, value):
        volume = value / 100.0
        self.audioOutput.setVolume(volume)

    def on_close(self):
        """Stop video"""
        self.reset()

    def save_as_action_triggered(self):
        """Save as action triggered"""
        if not self.path:
            QMessageBox.warning(self, "Save Error", "No video loaded.")
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Save video As", self.path, "Video Files (*.mp4 *.avi *.mkv)")
        if save_path and save_path != self.path:
            try:
                shutil.copy2(self.path, save_path)
                QMessageBox.information(self, "Save Successful", f"Video successfully to: {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"An error occurred while saving the video: {e}")
    def toggle_fullscreen(self):
        """Toggle fullscreen"""
        # TODO: implement fullscreen
        if self.window.ui.dialog['video_player'].isFullScreen():
            self.window.ui.dialog['video_player'].showNormal()
        else:
            self.window.ui.dialog['video_player'].showFullScreen()

    def update_label_path(self):
        """Update label path"""
        if self.path:
            self.labelPath.setText(os.path.basename(self.path))
        else:
            self.labelPath.setText("")

    def media_status_changed(self, status):
        """
        Media status changed

        :param status: status
        """
        if status == QMediaPlayer.LoadedMedia:
            self.force_resize()
        if status == QMediaPlayer.LoadedMedia:
            self.loaded = True
        elif status == QMediaPlayer.InvalidMedia:
            print("Failed to load video.")

    def toggle_play_pause(self):
        """Toggle play/pause"""
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
        else:
            if self.stopped and self.path:
                self.stopped = False
                self.open(self.path)
            else:
                self.mediaPlayer.play()
        self.on_playback_state_changed()

    def stop_video(self):
        """Stop video"""
        if self.mediaPlayer.source():
            self.mediaPlayer.stop()

        self.stopped = True
        self.slider.setValue(0)
        self.labelCurrentTime.setText(self.format_time(0))
        self.playPauseButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.update_timer.stop()

    def after_loaded(self):
        """Start playback after loaded"""
        if self.mediaPlayer.mediaStatus() == QMediaPlayer.LoadedMedia:
            if self.mediaPlayer.playbackState() != QMediaPlayer.PlayingState:
                self.toggle_play_pause()

    def force_resize(self):
        """Force resize fix"""
        # fix for video not showing after re-opening the dialog
        self.videoWidget.hide()
        self.videoWidget.show()
        self.videoWidget.update()
        current_size = self.window.ui.dialog['video_player'].size()
        self.window.ui.dialog['video_player'].resize(current_size.width() + 10, current_size.height() + 10)
        self.window.ui.dialog['video_player'].resize(current_size)
        self.window.ui.dialog['video_player'].repaint()
        w = self.videoWidget.width() - 1
        h = self.videoWidget.height() - 1
        self.videoWidget.resize(w, h)

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
        if event.button() == Qt.LeftButton:
            if self.loaded:
                self.toggle_play_pause()
        elif event.button() == Qt.RightButton:
            pass

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
        # convert ms to H:M:S format
        seconds = (ms // 1000) % 60
        minutes = (ms // 60000) % 60
        hours = (ms // 3600000)
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)