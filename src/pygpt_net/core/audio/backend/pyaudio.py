#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.07 03:00:00                  #
# ================================================== #

import time
from typing import List, Tuple

import wave
from PySide6.QtCore import QTimer


class PyaudioBackend:

    MIN_FRAMES = 25  # minimum frames to start transcription

    def __init__(self, window=None):
        """
        Audio input capture core using PyAudio backend
        """
        self.window = window
        self.path = None
        self.frames = []
        self.bar = None
        self.loop = False
        self.stop_callback = None
        self.start_time = 0
        self.initialized = False
        self.pyaudio_instance = None
        self.pyaudio_instance_output = None
        self.stream = None
        self.stream_output = None

        # Get configuration values (use defaults if unavailable)
        if self.window is not None and hasattr(self.window, "core"):
            self.channels = int(self.window.core.config.get('audio.input.channels', 1))
            self.rate = int(self.window.core.config.get('audio.input.rate', 44100))
        else:
            self.channels = 1
            self.rate = 44100

        self.format = None
        self.devices = []
        self.selected_device = None

    def init(self):
        """
        Initialize audio input backend.
        """
        import pyaudio
        if not self.initialized:
            self.format = pyaudio.paInt16   # We use paInt16 as default format
            self.pyaudio_instance = pyaudio.PyAudio()
            self.check_audio_devices()
            self.initialized = True

    def set_repeat_callback(self, callback):
        """
        Set callback to be called on loop recording.

        :param callback: function to call on loop recording
        """
        if callable(callback):
            self.stop_callback = callback
        else:
            raise ValueError("Callback must be a callable function")

    def set_loop(self, loop: bool):
        """
        Set loop recording.

        :param loop: True to enable loop recording
        """
        self.loop = loop

    def set_path(self, path: str):
        """
        Set audio input file path.

        :param path: file path to save recorded audio
        """
        self.path = path

    def set_bar(self, bar):
        """
        Set audio level bar.

        :param bar: audio level bar widget to update with audio levels
        """
        self.bar = bar

    def start(self):
        """
        Start audio input recording using PyAudio.
        :return: True if started
        """
        self.init()

        # Clear previous frames
        self.frames = []

        # Prepare selected device from configuration
        self.prepare_device()
        if self.selected_device is None:
            print("No audio input device selected")
            return False

        # Prevent multiple recordings
        if self.stream is not None:
            return False

        # Set up audio input and start recording
        self.setup_audio_input()
        self.start_time = time.time()
        return True

    def stop(self) -> bool:
        """
        Stop audio input recording.
        :return: True if stopped (and file saved) or False otherwise.
        """
        result = False
        if self.stream is not None:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"Error stopping stream: {e}")
            self.stream = None

            if self.frames:
                if self.path:
                    self.save_audio_file(self.path)
                    result = True
                else:
                    print("File path is not set.")
            else:
                print("No audio data recorded")
        return result

    def has_source(self) -> bool:
        """
        Check if audio source is available.
        :return: True if available.
        """
        return self.stream is not None

    def has_frames(self) -> bool:
        """
        Check if audio frames are available.
        :return: True if available.
        """
        return bool(self.frames)

    def has_min_frames(self) -> bool:
        """
        Check if minimum required audio frames have been recorded.
        :return: True if min frames reached.
        """
        return len(self.frames) >= self.MIN_FRAMES

    def reset_audio_level(self):
        """
        Reset the audio level bar.
        """
        if self.bar is not None:
            self.bar.setLevel(0)

    def check_audio_input(self) -> bool:
        """
        Check if default audio input device is working using PyAudio.
        :return: True if working.
        """
        self.init()
        try:
            test_stream = self.pyaudio_instance.open(format=self.format,
                                                     channels=self.channels,
                                                     rate=self.rate,
                                                     input=True,
                                                     frames_per_buffer=1024)
            test_stream.stop_stream()
            test_stream.close()
            return True
        except Exception as e:
            return False

    def check_audio_devices(self):
        """
        Check audio input devices using PyAudio and populate self.devices.
        Each device is stored as a dict with keys 'index' and 'name'.
        """
        self.devices = []
        for i in range(self.pyaudio_instance.get_device_count()):
            try:
                info = self.pyaudio_instance.get_device_info_by_index(i)
                if info.get('maxInputChannels', 0) > 0:
                    self.devices.append({'index': i, 'name': info.get('name', f'Device {i}')})
            except Exception as e:
                continue

        if not self.devices:
            self.selected_device = None
            print("No audio input devices found.")
        else:
            # Set the first available device as default
            self.selected_device = self.devices[0]['index']

    def device_changed(self, index: int):
        """
        Change audio input device based on device list index.
        :param index: device list index.
        """
        self.init()
        if 0 <= index < len(self.devices):
            self.selected_device = self.devices[index]['index']
        else:
            self.selected_device = 0

    def prepare_device(self):
        """
        Set the current audio input device from configuration.
        """
        self.init()
        if self.window is not None and hasattr(self.window, "core"):
            device_id = int(self.window.core.config.get('audio.input.device', 0))
            self.device_changed(device_id)
        else:
            # Default to first available device
            if self.devices:
                print(self.devices)
                self.selected_device = self.devices[0]['index']
            else:
                self.selected_device = None

    def setup_audio_input(self):
        """
        Set up audio input device and start recording using PyAudio.
        """
        self.init()
        if self.selected_device is None:
            print("No audio input device selected")
            return

        print("Opening audio stream with device index:", self.selected_device)
        try:
            self.stream = self.pyaudio_instance.open(format=self.format,
                                                     channels=self.channels,
                                                     rate=self.rate,
                                                     input=True,
                                                     frames_per_buffer=1024,
                                                     stream_callback=self._audio_callback)
        except Exception as e:
            print(f"Failed to open audio stream: {e}")
            self.stream = None

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio callback to process incoming audio data.
        """
        import pyaudio
        import numpy as np

        # Append raw data to the frames list for saving
        self.frames.append(in_data)

        # Convert bytes data to a NumPy array using the correct data type
        dtype = self.get_dtype_from_format(self.format)
        samples = np.frombuffer(in_data, dtype=dtype)
        if samples.size == 0:
            return None, pyaudio.paContinue

        # Compute root mean square (RMS) for the audio samples
        rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
        normalization_factor = self.get_normalization_factor(self.format)
        level = rms / normalization_factor
        # Clamp level to 0.0 - 1.0 range
        level = min(max(level, 0.0), 1.0)
        level_percent = int(level * 100)

        # Update the audio level bar if available.
        if self.bar is not None:
            try:
                QTimer.singleShot(0, lambda: self.bar.setLevel(level_percent))
            except Exception:
                pass

        # Handle loop recording if enabled.
        if self.loop and self.stop_callback is not None:
            stop_interval = int(self.window.core.config.get('audio.input.stop_interval', 10)) \
                if self.window and hasattr(self.window, "core") else 10
            current_time = time.time()
            if current_time - self.start_time >= stop_interval:
                self.start_time = current_time
                QTimer.singleShot(0, self.stop_callback)

        return None, pyaudio.paContinue

    def update_audio_level(self, level: int):
        """
        Update the audio level bar.
        :param level: audio level (0-100).
        """
        if self.bar is not None:
            self.bar.setLevel(level)

    def save_audio_file(self, filename: str):
        """
        Save the recorded audio frames to a WAV file.
        :param filename: output file name.
        """
        sample_width = self.pyaudio_instance.get_sample_size(self.format)
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))

    def get_dtype_from_format(self, fmt):
        """
        Get the NumPy dtype corresponding to the PyAudio format.
        :param fmt: PyAudio format constant.
        """
        import pyaudio
        import numpy as np
        if fmt == pyaudio.paInt16:
            return np.int16
        elif fmt == pyaudio.paInt8:
            return np.int8
        elif fmt == pyaudio.paUInt8:
            return np.uint8
        elif fmt == pyaudio.paFloat32:
            return np.float32
        else:
            raise ValueError("Unsupported audio format")

    def get_normalization_factor(self, fmt):
        """
        Get the normalization factor for the given PyAudio format.
        :param fmt: PyAudio format constant.
        """
        import pyaudio
        if fmt == pyaudio.paInt16:
            return 32768.0
        elif fmt == pyaudio.paInt8:
            return 128.0
        elif fmt == pyaudio.paUInt8:
            return 255.0
        elif fmt == pyaudio.paFloat32:
            return 1.0
        else:
            raise ValueError("Unsupported audio format")

    def stop_audio(self) -> bool:
        """
        Stop audio input recording.
        :return: True if stopped.
        """
        if self.stream is not None:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                print(f"Error stopping stream: {e}")
            self.stream = None
            return True
        return False

    def play(
            self,
            audio_file: str,
            event_name: str,
            stopped: callable,
            signals=None
    ):
        """
        Play audio file using PyAudio

        :param audio_file: audio file path
        :param event_name: event name to emit when playback starts
        :param stopped: callable to check if playback should stop
        :param signals: signals object to emit playback events
        """
        import io
        import wave
        import pyaudio
        import numpy as np
        from pydub import AudioSegment

        num_device = int(self.window.core.config.get('audio.output.device', 0))
        signals.playback.emit(event_name)
        audio = AudioSegment.from_file(audio_file)
        audio = audio.set_frame_rate(44100)  # resample to 44.1 kHz
        wav_io = io.BytesIO()
        audio.export(wav_io, format='wav')
        wav_io.seek(0)
        wf = wave.open(wav_io, 'rb')
        self.pyaudio_instance_output = pyaudio.PyAudio()
        self.stream_output = self.pyaudio_instance_output.open(
            format=self.pyaudio_instance_output.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
            output_device_index=num_device
        )

        sample_width = wf.getsampwidth()
        format = self.pyaudio_instance_output.get_format_from_width(sample_width)

        if format == pyaudio.paInt8:
            dtype = np.int8
            max_value = 2 ** 7 - 1  # 127
            offset = 0
        elif format == pyaudio.paInt16:
            dtype = np.int16
            max_value = 2 ** 15 - 1  # 32767
            offset = 0
        elif format == pyaudio.paInt32:
            dtype = np.int32
            max_value = 2 ** 31 - 1  # 2147483647
            offset = 0
        elif format == pyaudio.paUInt8:
            dtype = np.uint8
            max_value = 2 ** 8 - 1  # 255
            offset = 128  # center unsigned data
        else:
            raise ValueError(f"Unsupported format: {format}")

        chunk_size = 512
        data = wf.readframes(chunk_size)

        while data != b'' and not stopped():
            self.stream_output.write(data)

            audio_data = np.frombuffer(data, dtype=dtype)
            if len(audio_data) > 0:
                audio_data = audio_data.astype(np.float32)
                if dtype == np.uint8:
                    audio_data -= offset

                # compute RMS
                rms = np.sqrt(np.mean(audio_data ** 2))

                if rms > 0:
                    # RMS to decibels
                    db = 20 * np.log10(rms / max_value)

                    # define minimum and maximum dB levels
                    min_db = -60  # adjust as needed
                    max_db = 0

                    # clamp the db value to the range [min_db, max_db]
                    if db < min_db:
                        db = min_db
                    elif db > max_db:
                        db = max_db

                    # map decibel value to volume percentage
                    volume_percentage = ((db - min_db) / (max_db - min_db)) * 100
                else:
                    volume_percentage = 0

                # emit volume signal
                signals.volume_changed.emit(volume_percentage)
            else:
                # if empty audio_data
                signals.volume_changed.emit(0)

            data = wf.readframes(chunk_size)

        # close the stream
        if self.stream_output is not None:
            if self.stream_output.is_active():
                self.stream_output.stop_stream()
            self.stream_output.close()
        if self.pyaudio_instance_output is not None:
            self.pyaudio_instance_output.terminate()

        wf.close()
        signals.volume_changed.emit(0)

    def stop_playback(self, signals=None):
        """
        Stop audio playback if it is currently playing.

        :param signals: signals object to emit stop event
        """
        pass

    def get_input_devices(self) -> List[Tuple[int, str]]:
        """
        Get input devices

        :return devices list: [(id, name)]
        """
        from bs4 import UnicodeDammit
        self.init()
        devices_list = []
        for item in self.devices:
            index = item['index']
            device_name = item['name']
            dammit = UnicodeDammit(device_name)
            devices_list.append((index, dammit.unicode_markup))
        return devices_list

    def get_output_devices(self) -> List[Tuple[int, str]]:
        """
        Get output devices using pyaudio

        :return: List of tuples with (device_id, device_name)
        """
        import pyaudio
        p = pyaudio.PyAudio()
        devices_list = []
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info.get('maxOutputChannels', 0) > 0:
                devices_list.append((i, device_info.get('name', 'Unknown')))
        p.terminate()
        return devices_list

    def get_default_input_device(self) -> tuple:
        """
        Retrieve the default input device using PyAudio.
        """
        import pyaudio
        p = pyaudio.PyAudio()
        try:
            default_info = p.get_default_input_device_info()
            device_id = default_info.get('index')
            device_name = default_info.get('name', 'Unknown')
        except IOError as e:
            print("Error getting default output device:", e)
            device_id, device_name = None, None
        p.terminate()
        return device_id, device_name

    def get_default_output_device(self) -> tuple:
        """
        Retrieve the default output device using PyAudio.
        """
        import pyaudio
        p = pyaudio.PyAudio()
        try:
            default_info = p.get_default_output_device_info()
            device_id = default_info.get('index')
            device_name = default_info.get('name', 'Unknown')
        except IOError as e:
            print("Error getting default output device:", e)
            device_id, device_name = None, None
        p.terminate()
        return device_id, device_name