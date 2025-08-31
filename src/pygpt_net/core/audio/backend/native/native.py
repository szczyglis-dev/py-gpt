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

from typing import Optional
from typing import List, Tuple

from bs4 import UnicodeDammit

import time
import numpy as np
import wave

from PySide6.QtMultimedia import QMediaDevices, QAudioFormat, QAudioSource
from PySide6.QtCore import QTimer, QObject

from pygpt_net.core.events import RealtimeEvent

from .realtime import RealtimeSession
from ..shared import (
    qaudio_dtype,
    qaudio_norm_factor,
    qaudio_to_s16le,
    convert_s16_pcm,
    build_rt_input_delta_event,
    build_output_volume_event,
)
from .player import NativePlayer

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
            self.latency_ms = int(self.window.core.config.get('audio.input.latency_ms', 30))
        else:
            self.channels = 1
            self.rate = 44100
            self.latency_ms = 30

        # internal recording state flag to suppress volume updates after stop
        # This prevents late/queued readyRead events from updating the UI when recording is no longer active.
        self._is_recording = False

        self._dtype = None
        self._norm = None

        self._rt_session: Optional[RealtimeSession] = None
        self._rt_signals = None  # set by core.audio.output on initialize()

        # dedicated player wrapper (file playback + envelope metering)
        self._player = NativePlayer(window=self.window, chunk_ms=self.chunk_ms)

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

        # mark recording as active only after setup succeeded
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

        # immediately mark that we are no longer recording
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

            # Emit final input chunk marker for realtime consumers
            self._emit_rt_input_delta(b"", final=True)

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
        devices = QMediaDevices.audioInputs()
        if not devices:
            print("No audio input devices found.")
            return False

        device = self.selected_device if self.selected_device else devices[0]

        audio_format = device.preferredFormat()
        desired = QAudioFormat()
        desired.setSampleRate(self.rate)
        desired.setChannelCount(self.channels)
        desired.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if device.isFormatSupported(desired):
            audio_format = desired

        try:
            audio_source = QAudioSource(device, audio_format)
            bs = int(audio_format.sampleRate() * audio_format.channelCount() * audio_format.bytesPerSample() * (float(self.latency_ms) / 1000.0))
            if bs < 4096:
                bs = 4096
            audio_source.setBufferSize(bs)
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

        audio_input_device = self.selected_device

        audio_format = audio_input_device.preferredFormat()
        desired = QAudioFormat()
        desired.setSampleRate(int(self.window.core.config.get('audio.input.rate', 44100)))
        desired.setChannelCount(int(self.window.core.config.get('audio.input.channels', 1)))
        desired.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if audio_input_device.isFormatSupported(desired):
            audio_format = desired

        self.actual_audio_format = audio_format
        self._dtype = qaudio_dtype(self.actual_audio_format.sampleFormat())
        self._norm = qaudio_norm_factor(self.actual_audio_format.sampleFormat())

        try:
            self.audio_source = QAudioSource(audio_input_device, audio_format)
            bs = int(audio_format.sampleRate() * audio_format.channelCount() * audio_format.bytesPerSample() * (float(self.latency_ms) / 1000.0))
            if bs < 4096:
                bs = 4096
            self.audio_source.setBufferSize(bs)
        except Exception as e:
            self.disconnected = True
            print(f"Failed to create audio source: {e}")

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

        self.audio_io_device.readyRead.connect(self.process_audio_input)

    def process_audio_input(self):
        """Process incoming audio data"""
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
        dtype = self._dtype if self._dtype is not None else qaudio_dtype(sample_format)
        normalization_factor = self._norm if self._norm is not None else qaudio_norm_factor(sample_format)

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

        # --- emit realtime input delta (PCM16 LE) ---
        # Always standardize to Int16 for provider compatibility; do not resample here.
        try:
            s16 = qaudio_to_s16le(data_bytes, sample_format)
            self._emit_rt_input_delta(s16, final=False)
        except Exception:
            # avoid interrupting UI/recording on conversion issues
            self._emit_rt_input_delta(data_bytes, final=False)

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
        # do not update UI if recording already stopped
        if not self._is_recording:
            return
        self.window.controller.audio.ui.on_input_volume_change(int(level), self.mode)

    def save_audio_file(self, filename: str):
        """
        Save the recorded audio frames to a WAV file

        :param filename: output file name
        """
        # Define the parameters for the WAV file
        channels = self.actual_audio_format.channelCount()
        frame_rate = self.actual_audio_format.sampleRate()
        sample_format = self.actual_audio_format.sampleFormat()

        raw = b''.join(self.frames)

        if sample_format == QAudioFormat.SampleFormat.Int16:
            out_bytes = raw
            sample_size = 2
        elif sample_format == QAudioFormat.SampleFormat.UInt8:
            arr = np.frombuffer(raw, dtype=np.uint8).astype(np.int16)
            arr = (arr - 128) << 8
            out_bytes = arr.tobytes()
            sample_size = 2
        elif sample_format == QAudioFormat.SampleFormat.Int32:
            arr = np.frombuffer(raw, dtype=np.int32)
            arr = (arr >> 16).astype(np.int16)
            out_bytes = arr.tobytes()
            sample_size = 2
        elif sample_format == QAudioFormat.SampleFormat.Float:
            arr = np.frombuffer(raw, dtype=np.float32)
            arr = np.clip(arr, -1.0, 1.0)
            arr = (arr * 32767.0).astype(np.int16)
            out_bytes = arr.tobytes()
            sample_size = 2
        else:
            raise ValueError("Unsupported sample format")

        try:
            wf = wave.open(filename, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(sample_size)
            wf.setframerate(frame_rate)
            wf.writeframes(out_bytes)
            wf.close()
        except:
            pass

    def get_dtype_from_sample_format(self, sample_format):
        """
        Get the NumPy dtype corresponding to the QAudioFormat sample format

        :param sample_format: QAudioFormat.SampleFormat
        """
        return qaudio_dtype(sample_format)

    def get_normalization_factor(self, sample_format):
        """
        Get the normalization factor for the QAudioFormat sample format

        :param sample_format: QAudioFormat.SampleFormat
        """
        return qaudio_norm_factor(sample_format)

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
        # delegate to player wrapper to keep logic isolated
        self._player.play_after(
            audio_file=audio_file,
            event_name=event_name,
            stopped=stopped,
            signals=signals,
            auto_convert_to_wav=self.AUTO_CONVERT_TO_WAV,
            select_output_device=self._select_output_device,
        )

    def stop_timers(self):
        """Stop playback timers."""
        self._player.stop_timers()

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
        if self._rt_session:
            self._rt_session.stop()
        self._player.stop(signals=signals)
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
        :return: List of volume levels (0-100) for each chunk
        """
        from ..shared import compute_envelope_from_file
        return compute_envelope_from_file(audio_file, chunk_ms)

    def update_volume(self, signals=None):
        """
        Update the volume based on the current position in the audio file.

        :param signals: Signals object to emit volume changed event.
        """
        self._player.update_volume(signals)

    def get_input_devices(self) -> List[Tuple[int, str]]:
        """
        Get input devices

        :return devices list: [(id, name)]
        """
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
        default_device = QMediaDevices.defaultAudioOutput()
        devices = QMediaDevices.audioOutputs()
        try:
            index = devices.index(default_device)
        except ValueError:
            index = None
        return index, None

    # ---- REALTIME ----

    def _select_output_device(self):
        """
        Select the audio output device based on configuration.

        :return: QAudioDevice
        """
        devices = QMediaDevices.audioOutputs()
        if devices:
            try:
                num_device = int(self.window.core.config.get('audio.output.device', 0))
            except Exception:
                num_device = 0
            return devices[num_device] if 0 <= num_device < len(devices) else devices[0]
        return QMediaDevices.defaultAudioOutput()

    def _sample_format_from_mime(self, mime: Optional[str]) -> QAudioFormat.SampleFormat:
        """
        Determine sample format from MIME type.

        :param mime: MIME type string
        :return: QAudioFormat.SampleFormat
        """
        s = (mime or "audio/pcm").lower()
        if "float" in s or "f32" in s:
            return QAudioFormat.SampleFormat.Float
        if "pcm" in s:
            if "32" in s or "s32" in s or "int32" in s:
                return QAudioFormat.SampleFormat.Int32
            if "8" in s or "u8" in s:
                return QAudioFormat.SampleFormat.UInt8
            return QAudioFormat.SampleFormat.Int16
        if "l16" in s:
            return QAudioFormat.SampleFormat.Int16
        return QAudioFormat.SampleFormat.Int16

    def _make_format(
            self, 
            rate: int, 
            channels: int, 
            sample_format: QAudioFormat.SampleFormat
    ) -> QAudioFormat:
        """
        Create QAudioFormat from parameters.

        :param rate: Sample rate
        :param channels: Number of channels
        :param sample_format: Sample format
        :return: QAudioFormat
        """
        fmt = QAudioFormat()
        fmt.setSampleRate(int(rate))
        fmt.setChannelCount(int(channels))
        fmt.setSampleFormat(sample_format)
        return fmt

    def _emit_output_volume(self, value: int) -> None:
        """
        Emit output volume change event.

        :param value: Volume level (0-100)
        """
        if not self._rt_signals:
            return
        self._rt_signals.response.emit(build_output_volume_event(int(value)))

    def _ensure_rt_session(
            self, 
            mime: str, 
            rate: Optional[int], 
            channels: Optional[int]
    ) -> RealtimeSession:
        """
        Ensure a realtime audio playback session exists with the device's preferred (or nearest) format.
        Keep it simple: prefer Int16, reuse session if format unchanged.

        :param mime: MIME type of the audio data
        :param rate: Sample rate of the audio data
        :param channels: Number of channels in the audio data
        :return: RealtimeSession
        """
        device = self._select_output_device()

        # NOTE: start from device preferred format and coerce to Int16 if supported
        fmt = device.preferredFormat()
        try:
            if fmt.sampleFormat() != QAudioFormat.SampleFormat.Int16:
                test = QAudioFormat()
                test.setSampleRate(fmt.sampleRate())
                test.setChannelCount(fmt.channelCount())
                test.setSampleFormat(QAudioFormat.SampleFormat.Int16)
                if device.isFormatSupported(test):
                    fmt = test
                else:
                    try:
                        fmt = device.nearestFormat(test)
                    except Exception:
                        pass
        except Exception:
            pass

        # reuse current session if same format
        if self._rt_session is not None:
            try:
                ef = self._rt_session.format
                if (ef.sampleRate() == fmt.sampleRate()
                        and ef.channelCount() == fmt.channelCount()
                        and ef.sampleFormat() == fmt.sampleFormat()):
                    return self._rt_session
            except Exception:
                pass
            # NOTE: hard stop old one (we keep things simple)
            try:
                self._rt_session.stop()
            except Exception:
                pass
            self._rt_session = None

        session = RealtimeSession(
            device=device,
            fmt=fmt,
            parent=self,
            volume_emitter=self._emit_output_volume
        )
        # NOTE: when device actually stops (buffer empty), inform UI
        session.on_stopped = lambda: (
            self._rt_signals and self._rt_signals.response.emit(
                RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_END, {"source": "device"})
            ),
            setattr(self, "_rt_session", None)
        )
        self._rt_session = session
        return session

    def _convert_pcm_for_output(
            self, 
            data: bytes, 
            in_rate: int, 
            in_channels: int, 
            out_fmt: QAudioFormat
    ) -> bytes:
        """
        Minimal PCM converter to device format:
        - assumes input is S16LE,
        - converts channels (mono<->stereo) and sample rate,
        - keeps Int16; if device uses UInt8/Float, adapts sample width and bias.

        :param data: Input PCM data (assumed S16LE)
        :param in_rate: Input sample rate
        :param in_channels: Input number of channels
        :param out_fmt: Desired output QAudioFormat
        :return: Converted PCM data
        """
        if not data:
            return b""

        try:
            out_rate = int(out_fmt.sampleRate()) or in_rate
            out_ch = int(out_fmt.channelCount()) or in_channels
            out_sw = int(out_fmt.bytesPerSample()) or 2
            out_sf = out_fmt.sampleFormat()

            # pick string flag for format conversion
            if out_sf == QAudioFormat.SampleFormat.UInt8 and out_sw == 1:
                flag = "u8"
            elif out_sf == QAudioFormat.SampleFormat.Float and out_sw == 4:
                flag = "f32"
            else:
                flag = "s16"

            return convert_s16_pcm(
                data,
                in_rate=in_rate,
                in_channels=in_channels,
                out_rate=out_rate,
                out_channels=out_ch,
                out_width=out_sw,
                out_format=flag
            )
        except Exception:
            return data

    def stop_realtime(self):
        """Stop realtime audio playback session (simple/friendly)."""
        s = self._rt_session
        if s is not None:
            try:
                s.mark_final()  # NOTE: add small tail and let it finish
            except Exception:
                try:
                    s.stop()
                except Exception:
                    pass

    def set_rt_signals(self, signals) -> None:
        """
        Set signals object for realtime events.

        :param signals: Signals object
        """
        self._rt_signals = signals

    def handle_realtime(self, payload: dict) -> None:
        """
        Handle realtime audio playback payload.

        Expected payload keys:
        - data: bytes
        - mime: str (e.g. "audio/pcm", "audio/l16", etc.)
        - rate: int (sample rate)
        - channels: int (number of channels)
        - final: bool (True if final chunk)
        If mime is not PCM/L16, the chunk is ignored.

        :param payload: Payload dictionary        
        """
        try:
            data: bytes = payload.get("data", b"") or b""
            mime: str = (payload.get("mime", "audio/pcm") or "audio/pcm").lower()
            rate = int(payload.get("rate", 24000) or 24000)
            channels = int(payload.get("channels", 1) or 1)
            final = bool(payload.get("final", False))

            # only raw PCM/L16
            if ("pcm" not in mime) and ("l16" not in mime):
                if final and self._rt_session is not None:
                    try:
                        self._rt_session.mark_final()
                    except Exception:
                        pass
                return

            session = self._ensure_rt_session(mime, rate, channels)

            if data:
                out_fmt = session.format
                if (out_fmt.sampleRate() != rate) or (out_fmt.channelCount() != channels) or (
                        out_fmt.sampleFormat() != QAudioFormat.SampleFormat.Int16):
                    data = self._convert_pcm_for_output(data, rate, channels, out_fmt)
                session.feed(data)

            if final:
                session.mark_final()

        except Exception as e:
            try:
                self.window.core.debug.log(f"[audio][native] handle_realtime error: {e}")
            except Exception:
                pass

    # ---- REALTIME INPUT ----
    def _emit_rt_input_delta(self, data: bytes, final: bool) -> None:
        """
        Emit RT_INPUT_AUDIO_DELTA with a provider-agnostic payload.
        Standardizes to PCM16, little-endian, and includes rate/channels.

        :param data: audio data bytes
        :param final: True if this is the final chunk
        """
        if not self._rt_signals:
            return

        # Resolve current format safely
        try:
            rate = int(self.actual_audio_format.sampleRate())
            channels = int(self.actual_audio_format.channelCount())
        except Exception:
            rate = int(self.window.core.config.get('audio.input.rate', 44100))
            channels = int(self.window.core.config.get('audio.input.channels', 1))

        event = build_rt_input_delta_event(rate=rate, channels=channels, data=data or b"", final=bool(final))
        self._rt_signals.response.emit(event)

    def _convert_input_to_int16(self, raw: bytes, sample_format) -> bytes:
        """
        Convert arbitrary QAudioFormat sample format to PCM16 little-endian.
        Does not change sample rate or channel count.

        :param raw: input audio data bytes
        :param sample_format: QAudioFormat.SampleFormat of the input data
        :return: converted audio data bytes in PCM16 LE
        """
        return qaudio_to_s16le(raw, sample_format)