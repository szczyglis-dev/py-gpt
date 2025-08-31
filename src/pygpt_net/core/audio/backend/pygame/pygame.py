#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 04:00:00                  #
# ================================================== #

import time
import wave
import numpy as np
from typing import List, Tuple
from collections import deque
from threading import Lock

from PySide6.QtCore import QTimer

from ..shared import f32_to_s16le, build_rt_input_delta_event

class PygameBackend:
    MIN_FRAMES = 25  # minimum frames to start transcription

    def __init__(self, window=None):
        """
        Audio input capture core using pygame's SDL2 audio capture backend.
        Captured devices are stored as device name strings.

        :param window: Window instance
        """
        self.window = window
        self.path = None
        self.frames = []      # List to store captured audio chunks (bytes)
        self.loop = False
        self.stop_callback = None
        self.start_time = 0
        self.playback_sound = None

        # Configuration: use values from the window (if available) or defaults.
        if self.window is not None and hasattr(self.window, "core"):
            self.channels = int(self.window.core.config.get('audio.input.channels', 2))
            self.rate = int(self.window.core.config.get('audio.input.rate', 44100))
        else:
            self.channels = 2
            self.rate = 44100

        self.format = None
        self.chunksize = 512
        self.allowed_changes = None

        # Audio source (an instance of AudioDevice)
        self.audio_source = None

        # QTimer to periodically update the audio level.
        self.timer = None

        # Store available device names (strings)
        self.devices = []
        self.selected_device = None
        self.initialized = False
        self.mode = "input"  # input|control

        # --- REALTIME INPUT (mic -> dispatcher) ---
        self._rt_signals = None           # set with set_rt_signals()
        self._rt_queue = deque()          # queue of raw float32 chunks from SDL audio thread
        self._rt_lock = Lock()            # protects _rt_queue
        self._is_recording = False        # suppress updates after stop

    def init(self):
        """Initialize the pygame audio system if not already initialized."""
        if not self.initialized:
            import pygame
            from pygame._sdl2 import (
                AUDIO_F32,
                AUDIO_ALLOW_FORMAT_CHANGE,
            )
            self.format = AUDIO_F32
            self.chunksize = 512
            self.allowed_changes = AUDIO_ALLOW_FORMAT_CHANGE

            # Initialize pygame (required to use its SDL2 audio capture)
            pygame.mixer.pre_init(self.rate, 32, self.channels, 512)
            pygame.init()
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
        Set a callback to be called on loop recording.

        :param callback: Function to call when loop recording is triggered.
        """
        if callable(callback):
            self.stop_callback = callback
        else:
            raise ValueError("Callback must be a callable function")

    def set_loop(self, loop: bool):
        """
        Enable or disable loop recording.

        :param loop: True to enable loop recording, False to disable.
        """
        self.loop = loop

    def set_path(self, path: str):
        """
        Set a file path where the recorded audio will be saved.

        :param path: Path to save the audio file.
        """
        self.path = path

    def set_rt_signals(self, signals) -> None:
        """
        Set signals object for realtime events.

        :param signals: Signals object
        """
        self._rt_signals = signals

    def start(self):
        """
        Start audio recording using pygame’s SDL2 audio capture.
        Returns True if started successfully.

        :return: True if started
        """
        self.init()
        # Clear previously recorded frames.
        self.frames = []

        # Prepare the selected device (based on config or default).
        self.prepare_device()
        if not self.selected_device:
            print("No audio input device selected")
            return False
        if self.audio_source is not None:
            return False

        # Set up the audio input device and start capturing.
        self.setup_audio_input()
        self.start_time = time.time()

        # Set up a QTimer to update the audio level based on the latest chunk.
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_level)
        self.timer.start(50)  # update every 50ms

        # mark recording as active after setup
        self._is_recording = True
        return True

    def stop(self):
        """
        Stop audio recording.
        Returns True if stopped and audio data was saved (if path is set).

        :return: True if stopped and saved
        """
        self.init()
        result = False

        # immediately mark as not recording
        self._is_recording = False

        if self.audio_source is not None:
            if self.timer is not None:
                self.timer.stop()
                self.timer = None

            # Pause audio capture.
            self.audio_source.pause(1)
            self.audio_source = None

            # Emit final input chunk marker for realtime consumers
            try:
                self._emit_rt_input_delta(b"", final=True)
            except Exception:
                pass

            if self.frames:
                if self.path:
                    self.save_audio_file(self.path)
                    result = True
                else:
                    print("File path is not set.")
            else:
                print("No audio data recorded")

        # reset level indicator
        try:
            self.reset_audio_level()
        except Exception:
            pass

        return result

    def has_source(self) -> bool:
        """
        Check if the audio source is available.

        :return: True if audio source is available
        """
        return self.audio_source is not None

    def has_frames(self) -> bool:
        """
        Check if any audio frames have been recorded.

        :return: True if any frames recorded
        """
        return bool(self.frames)

    def has_min_frames(self) -> bool:
        """
        Check if at least MIN_FRAMES audio frames have been recorded.

        :return: True if at least MIN_FRAMES recorded
        """
        return len(self.frames) >= self.MIN_FRAMES

    def reset_audio_level(self):
        """Reset the audio level bar (if available)."""
        self.window.controller.audio.ui.on_input_volume_change(0, self.mode)

    def check_audio_input(self) -> bool:
        """
        Check if a default audio input device is available using pygame.

        :return: True if an audio input device is available
        """
        from pygame._sdl2 import (
            get_audio_device_names,
        )
        self.init()
        try:
            names = get_audio_device_names(True)
            return bool(names)
        except Exception as e:
            return False

    def check_audio_devices(self):
        """
        Retrieve available audio input devices using pygame's SDL2 audio capture.
        Devices are stored as a list of device name strings.
        """
        from pygame._sdl2 import (
            get_audio_device_names,
        )
        try:
            self.devices = get_audio_device_names(True)
        except Exception as e:
            print("Failed to get audio devices:", e)
            self.devices = []

        if not self.devices:
            self.selected_device = None
            print("No audio input devices found.")
        else:
            # Select the first available device by default.
            self.selected_device = self.devices[0]

    def device_changed(self, index: int):
        """
        Change the selected audio input device by its index in the devices list.

        :param index: Index of the device in the devices list.
        """
        self.init()
        if 0 <= index < len(self.devices):
            self.selected_device = self.devices[index]
        else:
            self.selected_device = None

    def prepare_device(self):
        """Set the current audio input device based on configuration."""
        self.init()
        if self.window is not None and hasattr(self.window, "core"):
            device_index = int(self.window.core.config.get('audio.input.device', 0))
            self.device_changed(device_index)
        else:
            if self.devices:
                self.selected_device = self.devices[0]
            else:
                self.selected_device = None

    def _audio_callback(self, audiodevice, audiomemoryview):
        """
        Callback function called in the audio thread.
        It receives a memoryview of audio data which is converted to bytes and appended.

        :param audiodevice: The audio device instance (not used here).
        :param audiomemoryview: MemoryView of the captured audio data.
        """
        if not self._is_recording:
            return

        # Append captured audio bytes to the frames list.
        chunk = bytes(audiomemoryview)
        self.frames.append(chunk)

        # Enqueue chunk for realtime emission (processed on the Qt thread).
        try:
            with self._rt_lock:
                self._rt_queue.append(chunk)
        except Exception:
            pass

    def setup_audio_input(self):
        """Create an AudioDevice with the selected device name and start recording."""
        self.init()
        from pygame._sdl2 import (
            AudioDevice,
        )
        if not self.selected_device:
            print("No audio input device selected")
            return

        try:
            self.audio_source = AudioDevice(
                devicename=self.selected_device,
                iscapture=True,
                frequency=self.rate,
                audioformat=self.format,
                numchannels=self.channels,
                chunksize=self.chunksize,
                allowed_changes=self.allowed_changes,
                callback=self._audio_callback,
            )
            self.audio_source.pause(0)
        except Exception as e:
            print(f"Failed to open audio stream: {e}")
            self.audio_source = None
            return

    def _update_level(self):
        """
        Periodically called (via QTimer) to compute RMS from the last captured audio chunk
        and update the audio level bar.
        """
        # Drain realtime queue first to keep latency low.
        self._drain_rt_queue()

        if not self.frames:
            return

        # Use the last captured chunk.
        last_chunk = self.frames[-1]
        try:
            # Interpret the bytes as float32 samples.
            samples = np.frombuffer(last_chunk, dtype=np.float32)
        except Exception:
            return
        if samples.size == 0:
            return

        # Compute RMS
        rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))

        # For float32 audio, the range is approximately -1.0 to 1.0.
        level = min(max(rms, 0.0), 1.0)
        level_percent = int(level * 100)

        QTimer.singleShot(0, lambda: self.window.controller.audio.ui.on_input_volume_change(level_percent, self.mode))

        # Handle loop recording if enabled.
        if self.loop and self.stop_callback is not None:
            stop_interval = (int(self.window.core.config.get('audio.input.stop_interval', 10))
                             if (self.window and hasattr(self.window, "core")) else 10)
            current_time = time.time()
            if current_time - self.start_time >= stop_interval:
                self.start_time = current_time
                QTimer.singleShot(0, self.stop_callback)

    def save_audio_file(self, filename: str):
        """
        Save the captured audio frames to a WAV file.
        Since we're capturing in AUDIO_F32 format, this method converts the float32 data
        to int16 PCM before saving.

        :param filename: The path to the output WAV file.
        """
        full_data = b"".join(self.frames)
        try:
            data_array = np.frombuffer(full_data, dtype=np.float32)
        except Exception as e:
            print("Error converting audio data:", e)
            return
        # Convert float32 values in the range -1.0 ... 1.0 to PCM int16.
        int_data = (np.clip(data_array, -1.0, 1.0) * 32767.0).astype(np.int16)
        new_data = int_data.tobytes()
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # int16 is 2 bytes
            wf.setframerate(self.rate)
            wf.writeframes(new_data)

    def play(
            self,
            audio_file: str,
            event_name: str,
            stopped: callable,
            signals=None
    ):
        """
        Play an audio file using pygame.mixer.

        :param audio_file: audio file path
        :param event_name: event name to emit when playback starts (via signals.playback)
        :param stopped: callable that returns True if playback should stop
        :param signals: signals
        """
        import io
        import wave
        import numpy as np
        from pydub import AudioSegment
        import pygame

        # Emit a playback signal.
        if signals is not None:
            signals.playback.emit(event_name)

        # Load audio and force its format to match mixer pre_init.
        audio = AudioSegment.from_file(audio_file)
        # Force sample rate, channel count, and sample width to match:
        audio = (audio.set_frame_rate(44100)
                 .set_channels(2)
                 .set_sample_width(2))  # 16-bit PCM => sample_width 2 bytes

        # Export the audio to a BytesIO buffer in WAV format.
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        wav_data = wav_io.read()

        # Create a pygame Sound object from the WAV data and start playback.
        pygame.mixer.pre_init(44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()

        self.playback_sound = pygame.mixer.Sound(buffer=wav_data)
        self.playback_sound.play()

        # Prepare to read WAV data for volume analysis:
        wav_io.seek(0)
        wf = wave.open(wav_io, "rb")

        # Determine numpy dtype based on sample width.
        sample_width = wf.getsampwidth()
        if sample_width == 1:
            dtype = np.uint8
            max_value = 2 ** 7 - 1  # 127 (usually 8-bit PCM stored as unsigned)
            offset = 0
        elif sample_width == 2:
            dtype = np.int16
            max_value = 2 ** 15 - 1  # 32767
            offset = 0
        elif sample_width == 4:
            dtype = np.int32
            max_value = 2 ** 31 - 1
            offset = 0
        else:
            raise ValueError(f"Unsupported sample width: {sample_width} bytes")

        # Process the WAV file in chunks for volume level updates.
        chunk_size = 512  # frames per chunk
        framerate = wf.getframerate()
        # Compute delay per chunk in milliseconds.
        delay_ms = int(1000 * chunk_size / framerate)

        data = wf.readframes(chunk_size)
        while data != b"" and not stopped():
            # Convert bytes to numpy array.
            audio_data = np.frombuffer(data, dtype=dtype)
            if dtype == np.uint8:
                audio_data = audio_data.astype(np.int16) - offset

            audio_data = audio_data.astype(np.float32)
            if audio_data.size > 0:
                rms = np.sqrt(np.mean(audio_data ** 2))
                # Convert RMS to decibels (0 dB corresponds to max_value)
                if rms > 0:
                    db = 20 * np.log10(rms / max_value)
                    # Clamp dB value between -60 dB and 0 dB.
                    db = max(min(db, 0), -60)
                    volume_percentage = ((db + 60) / 60) * 100
                else:
                    volume_percentage = 0
            else:
                volume_percentage = 0

            if signals is not None:
                signals.volume_changed.emit(volume_percentage)

            pygame.time.delay(delay_ms)
            data = wf.readframes(chunk_size)

        wf.close()
        if signals is not None:
            signals.volume_changed.emit(0)

    def stop_playback(self, signals=None):
        """
        Stop audio playback if it is currently playing.

        :param signals: signals object with:
        """
        if hasattr(self, 'playback_sound') and self.playback_sound is not None:
            self.playback_sound.stop()
            self.playback_sound = None

    def get_input_devices(self) -> List[Tuple[int, str]]:
        """
        Get input devices

        :return devices list: [(id, name)]
        """
        from bs4 import UnicodeDammit
        self.init()
        devices_list = []
        for index, device in enumerate(self.devices):
            dammit = UnicodeDammit(device)
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

        :return: (index, name)
        """
        return 0, "Default Input Device"

    def get_default_output_device(self) -> tuple:
        """
        Retrieve the default output device using PyAudio.

        :return: (index, name)
        """
        return 0, "Default Output Device"

    # --------------------
    # REALTIME INPUT HELPERS
    # --------------------
    def _emit_rt_input_delta(self, data: bytes, final: bool) -> None:
        """
        Emit RT_INPUT_AUDIO_DELTA with a provider-agnostic payload.
        Standardizes to PCM16, little-endian, and includes rate/channels.

        :param data: PCM16LE audio bytes
        :param final: True if this is the final chunk
        """
        if not self._rt_signals:
            return
        try:
            event = build_rt_input_delta_event(
                rate=int(self.rate),
                channels=int(self.channels),
                data=data or b"",
                final=bool(final),
            )
            # Ensure emission on the Qt thread
            QTimer.singleShot(0, lambda: self._rt_signals.response.emit(event))
        except Exception:
            pass

    def _drain_rt_queue(self) -> None:
        """
        Drain queued float32 chunks from the audio thread, convert to PCM16,
        and emit a single realtime delta event.
        """
        if not self._rt_signals:
            # nothing to emit
            with self._rt_lock:
                self._rt_queue.clear()
            return

        with self._rt_lock:
            if not self._rt_queue:
                return
            raw = b"".join(self._rt_queue)
            self._rt_queue.clear()

        s16 = f32_to_s16le(raw)
        if s16:
            self._emit_rt_input_delta(s16, final=False)