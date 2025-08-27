#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.27 07:00:00                  #
# ================================================== #

import os
import time
from typing import List, Tuple

from PySide6.QtCore import QTimer, QObject
from pydub import AudioSegment


class NativeBackend(QObject):

    MIN_FRAMES = 25  # minimum frames to start transcription
    AUTO_CONVERT_TO_WAV = False  # automatically convert to WAV format

    def __init__(self, window=None):
        """
        Audio input capture core

        :param window: Window instance
        """
        super().__init__(window)
        self.window = window
        self.audio_source = None
        self.audio_io_device = None
        self.frames = []
        self.actual_audio_format = None
        self.path = None
        self.disconnected = False
        self.initialized = False
        self.start_time = 0
        self.devices = []
        self.selected_device = None
        self.loop = False
        self.stop_callback = None
        self.player = None
        self.playback_timer = None
        self.volume_timer = None
        self.audio_output = None
        self.envelope = []
        self.chunk_ms = 10
        self.mode = "input" # input|control

        # Get configuration values (use defaults if unavailable)
        if self.window is not None and hasattr(self.window, "core"):
            self.channels = int(self.window.core.config.get('audio.input.channels', 1))
            self.rate = int(self.window.core.config.get('audio.input.rate', 44100))
        else:
            self.channels = 1
            self.rate = 44100

        # --- Added: internal recording state flag to suppress volume updates after stop ---
        # This prevents late/queued readyRead events from updating the UI when recording is no longer active.
        self._is_recording = False

    def init(self):
        """
        Initialize audio input backend.
        """
        if not self.initialized:
            self.check_audio_devices()
            self.initialized = True

    def set_mode(self, mode: str):
        """
        Set input mode (input|control)

        :param mode: mode name
        """
        self.mode = mode

    def set_repeat_callback(self, callback):
        """
        Set callback to be called on loop recording

        :param callback: function to call on loop recording
        """
        if callable(callback):
            self.stop_callback = callback
        else:
            raise ValueError("Callback must be a callable function")

    def set_loop(self, loop: bool):
        """
        Set loop recording

        :param loop: True to enable loop recording
        """
        self.loop = loop

    def set_path(self, path: str):
        """
        Set audio input file path

        :param path: file path
        """
        self.path = path

    def start(self):
        """
        Start audio input recording

        :return: True if started
        """
        self.init()
        # Clear previous frames
        self.frames = []

        # Prepare selected device
        self.prepare_device()
        if not self.selected_device:
            print("No audio input device selected")
            return
        if self.disconnected:
            print("Audio source disconnected, please connect the audio source")
            return False

        # Prevent multiple recordings
        if self.audio_source is not None:
            return False

        # Set up audio input and start recording
        self.setup_audio_input()
        self.start_time = time.time()

        # --- Added: mark recording as active only after setup succeeded ---
        # This ensures process_audio_input() will start updating the UI.
        if self.audio_source is not None and self.audio_io_device is not None:
            self._is_recording = True
        return True

    def stop(self) -> bool:
        """
        Stop audio input recording

        :return: True if stopped
        """
        result = False

        # --- Added: immediately mark that we are no longer recording ---
        # This blocks any late UI updates coming from queued signals.
        self._is_recording = False

        if self.audio_source is not None:
            # Disconnect the readyRead signal
            try:
                if self.audio_io_device is not None:
                    self.audio_io_device.readyRead.disconnect(self.process_audio_input)
            except (TypeError, RuntimeError):
                # ignore if already disconnected or device gone ---
                pass

            self.audio_source.stop()
            self.audio_source = None
            self.audio_io_device = None

            # Save frames to file (if any)
            if self.frames:
                self.save_audio_file(self.path)
                result = True
            else:
                print("No audio data recorded")

        # reset input volume on stop to visually indicate end of recording ---
        self.reset_audio_level()

        return result

    def has_source(self) -> bool:
        """
        Check if audio source is available

        :return: True if available
        """
        if self.audio_source is not None:
            return True
        return False

    def has_frames(self) -> bool:
        """
        Check if audio frames are available

        :return: True if available
        """
        if self.frames:
            return True
        return False

    def has_min_frames(self) -> bool:
        """
        Check if min required audio frames

        :return: True if min frames
        """
        if self.frames:
            frames = self.get_frames()
            if len(frames) < self.MIN_FRAMES:
                return False
            else:
                return True
        return False

    def reset_audio_level(self):
        """Reset the audio level bar"""
        self.window.controller.audio.ui.on_input_volume_change(0, self.mode)

    def check_audio_input(self) -> bool:
        """
        Check if default audio input device is working using native PySide.

        :return: True if working
        """
        self.init()
        from PySide6.QtMultimedia import QMediaDevices, QAudioFormat, QAudioSource

        devices = QMediaDevices.audioInputs()
        if not devices:
            print("No audio input devices found.")
            return False

        device = self.selected_device if self.selected_device else devices[0]
        audio_format = QAudioFormat()
        audio_format.setSampleRate(self.rate)
        audio_format.setChannelCount(self.channels)
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        if not device.isFormatSupported(audio_format):
            print("Requested format not supported, using nearest format.")
            audio_format = device.preferredFormat()
        try:
            audio_source = QAudioSource(device, audio_format)
            io_device = audio_source.start()
            if io_device is None:
                print("Unable to access audio input device")
                return False
            audio_source.stop()
            return True
        except Exception as e:
            print(f"Error while checking audio input: {e}")
            return False

    def check_audio_devices(self):
        """Check audio input devices"""
        from PySide6.QtMultimedia import QMediaDevices
        self.devices = QMediaDevices.audioInputs()
        if not self.devices:
            # no devices found
            self.selected_device = None
            print("No audio input devices found.")
        else:
            current = int(self.window.core.config.get('audio.input.device', 0))
            if current < 0 or current >= len(self.devices):
                # if current device is not valid, set the first device as default
                print(f"Invalid audio input device index {current}, using the first device.")
                current = 0
            self.selected_device = self.devices[current]

    def device_changed(self, index: int):
        """
        Change audio input device

        :param index: device index
        """
        self.init()
        if 0 <= index < len(self.devices):
            self.selected_device = self.devices[index]
        else:
            self.selected_device = None

    def prepare_device(self):
        """Set the current audio input device"""
        self.init()
        device_id = int(self.window.core.config.get('audio.input.device', 0))
        self.device_changed(device_id)

    def get_frames(self) -> list:
        """
        Get recorded audio frames

        :return: list of frames
        """
        return self.frames

    def setup_audio_input(self):
        """Set up audio input device and start recording"""
        self.init()
        if not self.selected_device:
            print("No audio input device selected")
            return

        from PySide6.QtMultimedia import QAudioFormat, QAudioSource

        # Define audio format
        audio_format = QAudioFormat()
        audio_format.setSampleRate(int(self.window.core.config.get('audio.input.rate', 44100)))
        audio_format.setChannelCount(int(self.window.core.config.get('audio.input.channels', 1)))
        audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        # Select default audio input device
        audio_input_device = self.selected_device

        # Check if the format is supported
        if not audio_input_device.isFormatSupported(audio_format):
            print("Requested format not supported, using nearest format.")
            audio_format = audio_input_device.preferredFormat()
            if audio_format.channelCount() > 2:
                audio_format.setChannelCount(2)
            if audio_format.sampleRate() > 44100:
                audio_format.setSampleRate(44100)
            if audio_format.bytesPerSample() > 2:
                audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        # Store the actual format being used
        self.actual_audio_format = audio_format

        # Create QAudioSource object with the device and format
        try:
            self.audio_source = QAudioSource(audio_input_device, audio_format)
        except Exception as e:
            self.disconnected = True
            print(f"Failed to create audio source: {e}")

        # Start audio input and obtain the QIODevice
        try:
            self.audio_io_device = self.audio_source.start()
            if self.audio_io_device is None:
                raise Exception("Unable to access audio input device")
        except Exception as e:
            print(f"Failed to start audio input: {e}")
            self.disconnected = True
            self.audio_source = None
            self.audio_io_device = None
            return

        # Connect the readyRead signal to process incoming data
        self.audio_io_device.readyRead.connect(self.process_audio_input)

    def process_audio_input(self):
        """Process incoming audio data"""
        import numpy as np
        from PySide6.QtMultimedia import QAudioFormat

        # guard against late calls after stop or missing device ---
        if not self._is_recording or self.audio_io_device is None:
            return

        # add seconds to stop timer
        data = self.audio_io_device.readAll()
        if data.isEmpty():
            return

        # Convert QByteArray to bytes
        data_bytes = data.data()

        # Append raw data to frames list for saving
        self.frames.append(data_bytes)

        # Determine the correct dtype and normalization factor
        sample_format = self.actual_audio_format.sampleFormat()
        dtype = self.get_dtype_from_sample_format(sample_format)
        normalization_factor = self.get_normalization_factor(sample_format)

        # Convert bytes to NumPy array of the appropriate type
        samples = np.frombuffer(data_bytes, dtype=dtype)
        if samples.size == 0:
            return

        # For unsigned formats, center the data
        if sample_format == QAudioFormat.SampleFormat.UInt8:
            samples = samples.astype(np.int16)
            samples -= 128

        # Compute RMS of the audio samples as float64 for precision
        rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))

        # Normalize RMS value based on the sample format
        level = rms / normalization_factor

        # Ensure level is within 0.0 to 1.0
        level = min(max(level, 0.0), 1.0)

        # Scale to 0-100
        level_percent = level * 100

        # Update the level bar widget
        self.update_audio_level(level_percent)

        # Handle loop recording
        if self.loop and self.stop_callback is not None:
            stop_interval = int(self.window.core.config.get('audio.input.stop_interval', 10))
            current_time = time.time()
            time_elapsed = current_time - self.start_time
            if time_elapsed >= stop_interval:
                # stop recording here, save audio chunk to WAV file, run transcription, and start recording again
                self.start_time = current_time
                QTimer.singleShot(0, self.stop_callback)  # required QTimer to prevent crash!!!

    def update_audio_level(self, level: int):
        """
        Update the audio level bar

        :param level: audio level
        """
        # --- Added: do not update UI if recording already stopped ---
        if not self._is_recording:
            return
        self.window.controller.audio.ui.on_input_volume_change(int(level), self.mode)

    def save_audio_file(self, filename: str):
        """
        Save the recorded audio frames to a WAV file

        :param filename: output file name
        """
        import wave
        # Define the parameters for the WAV file
        channels = self.actual_audio_format.channelCount()
        sample_size = self.actual_audio_format.bytesPerSample()
        frame_rate = self.actual_audio_format.sampleRate()

        # Open the WAV file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(sample_size)
        wf.setframerate(frame_rate)

        # Write frames to the file
        wf.writeframes(b''.join(self.frames))
        wf.close()

    def get_dtype_from_sample_format(self, sample_format):
        """
        Get the NumPy dtype corresponding to the QAudioFormat sample format

        :param sample_format: QAudioFormat.SampleFormat
        """
        import numpy as np
        from PySide6.QtMultimedia import QAudioFormat

        if sample_format == QAudioFormat.SampleFormat.UInt8:
            return np.uint8
        elif sample_format == QAudioFormat.SampleFormat.Int16:
            return np.int16
        elif sample_format == QAudioFormat.SampleFormat.Int32:
            return np.int32
        elif sample_format == QAudioFormat.SampleFormat.Float:
            return np.float32
        else:
            raise ValueError("Unsupported sample format")

    def get_normalization_factor(self, sample_format):
        """
        Get the normalization factor for the QAudioFormat sample format

        :param sample_format: QAudioFormat.SampleFormat
        """
        from PySide6.QtMultimedia import QAudioFormat

        if sample_format == QAudioFormat.SampleFormat.UInt8:
            return 255.0
        elif sample_format == QAudioFormat.SampleFormat.Int16:
            return 32768.0
        elif sample_format == QAudioFormat.SampleFormat.Int32:
            return float(2 ** 31)
        elif sample_format == QAudioFormat.SampleFormat.Float:
            return 1.0
        else:
            raise ValueError("Unsupported sample format")

    def play_after(
            self,
            audio_file: str,
            event_name: str,
            stopped: callable,
            signals=None
    ):
        """
        Start audio playback using QtMultimedia

        :param audio_file: Path to audio file
        :param event_name: Event name to emit on playback
        :param stopped: Callback to call when playback is stopped
        :param signals: Signals to emit on playback
        :return: True if started
        """
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
        from PySide6.QtCore import QUrl, QTimer
        if signals is not None:
            signals.playback.emit(event_name)

        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(1.0)

        devices = QMediaDevices.audioOutputs()
        if devices:
            try:
                num_device = int(self.window.core.config.get('audio.output.device', 0))
            except Exception:
                num_device = 0
            selected_device = devices[num_device] if num_device < len(devices) else devices[0]
            self.audio_output.setDevice(selected_device)

        if self.AUTO_CONVERT_TO_WAV:
            if audio_file.lower().endswith('.mp3'):
                tmp_dir = self.window.core.audio.get_cache_dir()
                base_name = os.path.splitext(os.path.basename(audio_file))[0]
                dst_file = os.path.join(tmp_dir, "_" + base_name + ".wav")
                wav_file = self.window.core.audio.mp3_to_wav(audio_file, dst_file)
                if wav_file:
                    audio_file = wav_file

        def check_stop():
            if stopped():
                self.player.stop()
                self.stop_timers()
                signals.volume_changed.emit(0)
            else:
                if self.player:
                    if self.player.playbackState() == QMediaPlayer.StoppedState:
                        self.player.stop()
                        self.stop_timers()
                        signals.volume_changed.emit(0)

        self.envelope = self.calculate_envelope(audio_file, self.chunk_ms)
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(audio_file))
        self.player.play()

        self.playback_timer = QTimer()
        self.playback_timer.setInterval(100)
        self.playback_timer.timeout.connect(check_stop)
        self.volume_timer = QTimer(self)
        self.volume_timer.setInterval(10)  # every 100 ms
        self.volume_timer.timeout.connect(
            lambda: self.update_volume(signals)
        )

        self.playback_timer.start()
        self.volume_timer.start()
        signals.volume_changed.emit(0)

    def stop_timers(self):
        """
        Stop playback timers.
        """
        if self.playback_timer is not None:
            self.playback_timer.stop()
            self.playback_timer = None
        if self.volume_timer is not None:
            self.volume_timer.stop()
            self.volume_timer = None

    def play(
            self,
            audio_file: str,
            event_name: str,
            stopped: callable,
            signals=None
    ):
        """
        Start audio playback.

        :param audio_file: Path to audio file
        :param event_name: Event name to emit on playback
        :param stopped: Callback to call when playback is stopped
        :param signals: Signals object to emit playback events.
        :return: True if started successfully.
        """
        self.play_after(audio_file, event_name, stopped, signals)

    def stop_playback(self, signals=None) -> bool:
        """
        Stop audio playback.

        :param signals: Signals object to emit stop event.
        :return: True if stopped successfully.
        """
        if self.player is not None:
            self.player.stop()
        self.stop_timers()
        return False

    def calculate_envelope(
            self,
            audio_file: str,
            chunk_ms: int = 100
    ) -> list:
        """
        Calculate the volume envelope of an audio file.

        :param audio_file: Path to the audio file
        :param chunk_ms: Size of each chunk in milliseconds
        """
        import numpy as np
        audio = AudioSegment.from_file(audio_file)
        max_amplitude = 32767
        envelope = []

        for ms in range(0, len(audio), chunk_ms):
            chunk = audio[ms:ms + chunk_ms]
            rms = chunk.rms
            if rms > 0:
                db = 20 * np.log10(rms / max_amplitude)
            else:
                db = -60
            db = max(-60, min(0, db))
            volume = ((db + 60) / 60) * 100
            envelope.append(volume)

        return envelope

    def update_volume(self, signals=None):
        """
        Update the volume based on the current position in the audio file.

        :param signals: Signals object to emit volume changed event.
        """
        pos = self.player.position()
        index = int(pos / self.chunk_ms)
        if index < len(self.envelope):
            volume = self.envelope[index]
        else:
            volume = 0
        signals.volume_changed.emit(volume)

    def get_input_devices(self) -> List[Tuple[int, str]]:
        """
        Get input devices

        :return devices list: [(id, name)]
        """
        from bs4 import UnicodeDammit
        from PySide6.QtMultimedia import QMediaDevices
        devices = QMediaDevices.audioInputs()
        devices_list = []
        for index, device in enumerate(devices):
            dammit = UnicodeDammit(device.description())
            devices_list.append((index, dammit.unicode_markup))
        return devices_list

    def get_output_devices(self) -> List[Tuple[int, str]]:
        """
        Get output devices

        :return devices list: [(id, name)]
        """
        from bs4 import UnicodeDammit
        from PySide6.QtMultimedia import QMediaDevices
        devices = QMediaDevices.audioOutputs()
        devices_list = []
        for index, device in enumerate(devices):
            dammit = UnicodeDammit(device.description())
            devices_list.append((index, dammit.unicode_markup))
        return devices_list

    def get_default_input_device(self) -> tuple:
        """
        Retrieve the default input device using PyAudio.

        :return: (device_id, error_message) tuple
        """
        from PySide6.QtMultimedia import QMediaDevices
        default_device = QMediaDevices.defaultAudioInput()
        devices = QMediaDevices.audioInputs()
        try:
            index = devices.index(default_device)
        except ValueError:
            index = None
        return index, None

    def get_default_output_device(self):
        """
        Get the default audio output device ID using PySide6's QMediaDevices.

        :return: (device_id, None) if successful, (None, error_message) if failed
        """
        from PySide6.QtMultimedia import QMediaDevices
        default_device = QMediaDevices.defaultAudioOutput()
        devices = QMediaDevices.audioOutputs()
        try:
            index = devices.index(default_device)
        except ValueError:
            index = None
        return index, None