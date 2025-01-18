#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.17 02:00:00                  #
# ================================================== #

import time

import numpy as np
import wave

from PySide6.QtMultimedia import QAudioFormat, QMediaDevices, QAudioSource
from PySide6.QtCore import QTimer

class Capture:
    def __init__(self, window=None):
        """
        Audio input capture core

        :param window: Window instance
        """
        self.window = window
        self.audio_source = None
        self.audio_io_device = None
        self.frames = []
        self.actual_audio_format = None
        self.path = None
        self.disconnected = False
        self.loop = False
        self.stop_callback = None
        self.start_time = 0
        self.devices = []
        self.selected_device = None
        self.bar = None
        self.check_audio_devices()

    def set_path(self, path: str):
        """
        Set audio input file path

        :param path: file path
        """
        self.path = path

    def set_bar(self, bar):
        """
        Set audio level bar

        :param bar: audio level bar
        """
        self.bar = bar

    def check_audio_devices(self):
        """Check audio input devices"""
        self.devices = QMediaDevices.audioInputs()
        if not self.devices:
            # no devices found
            self.selected_device = None
            print("No audio input devices found.")
        else:
            # set the first device as default
            self.selected_device = self.devices[0]

    def device_changed(self, index: int):
        """
        Change audio input device

        :param index: device index
        """
        if 0 <= index < len(self.devices):
            self.selected_device = self.devices[index]
        else:
            self.selected_device = None

    def prepare_device(self):
        """Set the current audio input device"""
        device_id = int(self.window.core.config.get('audio.input.device', 0))
        self.device_changed(device_id)

    def start(self):
        """
        Start audio input recording

        :return: True if started
        """
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
        return True

    def stop(self):
        """
        Stop audio input recording

        :return: True if stopped
        """
        result = False
        if self.audio_source is not None:
            # Disconnect the readyRead signal
            self.audio_io_device.readyRead.disconnect(self.process_audio_input)
            self.audio_source.stop()
            self.audio_source = None
            self.audio_io_device = None

            # Save frames to file (if any)
            if self.frames:
                self.save_audio_file(self.path)
                result = True
            else:
                print("No audio data recorded")
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

    def get_frames(self) -> list:
        """
        Get recorded audio frames

        :return: list of frames
        """
        return self.frames

    def setup_audio_input(self):
        """Set up audio input device and start recording"""
        if not self.selected_device:
            print("No audio input device selected")
            return

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
        if self.bar is not None:
            self.bar.setLevel(level)

    def reset_audio_level(self):
        """Reset the audio level bar"""
        if self.bar is not None:
            self.bar.setLevel(0)

    def save_audio_file(self, filename: str):
        """
        Save the recorded audio frames to a WAV file

        :param filename: output file name
        """
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

    def check_audio_input(self) -> bool:
        """
        Check if default audio input device is working

        :return: True if working
        """
        import pyaudio
        p = pyaudio.PyAudio()
        try:
            rate = 44100
            channels = 1
            stream = p.open(format=pyaudio.paInt16,
                            channels=channels,
                            rate=rate,
                            input=True)
            stream.stop_stream()
            stream.close()
            p.terminate()
            return True
        except Exception as e:
            p.terminate()
            return False