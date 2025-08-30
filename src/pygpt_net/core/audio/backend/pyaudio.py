#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.30 06:00:00                  #
# ================================================== #

from typing import List, Tuple, Optional

import io
import threading
import time
import wave
import audioop
import numpy as np

from PySide6.QtCore import QTimer, QObject

from pygpt_net.core.events import RealtimeEvent

from ..realtime.pyaudio import RealtimeSessionPyAudio

class _FilePlaybackThread(threading.Thread):
    """
    File playback worker that owns its PyAudio instance and stream.
    All creation and teardown happen inside this thread to avoid cross-thread closes.
    """
    def __init__(self, device_index: int, audio_file: str, signals):
        """
        Initialize the playback thread.

        :param device_index: output device index
        :param audio_file: path to audio file
        :param signals: signals object to emit volume changes
        """
        super().__init__(daemon=True)
        self.device_index = int(device_index)
        self.audio_file = audio_file
        self.signals = signals
        self._stop_evt = threading.Event()

    def request_stop(self):
        """Ask the worker to stop gracefully."""
        self._stop_evt.set()

    def _emit_main(self, fn, *args):
        """
        Emit via Qt main thread.

        :param fn: function to call
        :param args: arguments to pass
        """
        try:
            QTimer.singleShot(0, lambda: fn(*args))
        except Exception:
            pass

    def run(self):
        """Thread entry point: play the audio file and emit volume changes."""
        import pyaudio
        import numpy as np
        from pydub import AudioSegment
        import wave as _wave

        pa = None
        wf = None
        stream = None
        try:
            # prepare WAV in memory (normalize rate to 44100 to be safe)
            audio = AudioSegment.from_file(self.audio_file)
            audio = audio.set_frame_rate(44100)
            wav_io = io.BytesIO()
            audio.export(wav_io, format='wav')
            wav_io.seek(0)
            wf = _wave.open(wav_io, 'rb')

            pa = pyaudio.PyAudio()

            def _try_open(idx: int):
                s = pa.open(
                    format=pa.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True,
                    output_device_index=idx,
                    frames_per_buffer=1024,
                )
                try:
                    s.start_stream()
                except Exception:
                    pass
                return s

            # open output; if the specific device fails, try fallbacks
            try:
                stream = _try_open(self.device_index)
            except Exception:
                # try default
                try:
                    di = pa.get_default_output_device_info()
                    stream = _try_open(int(di.get('index')))
                except Exception:
                    # scan first output-capable
                    for i in range(pa.get_device_count()):
                        try:
                            di = pa.get_device_info_by_index(i)
                            if di.get('maxOutputChannels', 0) > 0:
                                stream = _try_open(i)
                                break
                        except Exception:
                            continue

            if stream is None:
                return  # no device available

            # dtype for meter
            sw = wf.getsampwidth()
            if sw == 1:
                dtype = np.uint8
                max_value = 255.0
                offset = 128.0
                is_u8 = True
            elif sw == 2:
                dtype = np.int16
                max_value = 32767.0
                offset = 0.0
                is_u8 = False
            elif sw == 4:
                dtype = np.int32
                max_value = 2147483647.0
                offset = 0.0
                is_u8 = False
            else:
                dtype = np.int16
                max_value = 32767.0
                offset = 0.0
                is_u8 = False

            chunk = 1024
            data = wf.readframes(chunk)

            while data and not self._stop_evt.is_set():
                try:
                    stream.write(data)
                except Exception:
                    break

                # volume meter (emit on GUI thread)
                if self.signals is not None:
                    try:
                        arr = np.frombuffer(data, dtype=dtype).astype(np.float32)
                        if arr.size > 0:
                            if is_u8:
                                arr -= offset
                                denom = 127.0
                            else:
                                denom = max_value
                            rms = float(np.sqrt(np.mean(arr * arr)))
                            if denom > 0.0 and rms > 0.0:
                                db = 20.0 * float(np.log10(max(1e-12, rms / denom)))
                                db = max(-60.0, min(0.0, db))
                                vol = int(((db + 60.0) / 60.0) * 100.0)
                            else:
                                vol = 0
                        else:
                            vol = 0
                        self._emit_main(self.signals.volume_changed.emit, vol)
                    except Exception:
                        pass

                data = wf.readframes(chunk)

        finally:
            # teardown in the SAME thread
            try:
                if stream is not None:
                    try:
                        if stream.is_active():
                            stream.stop_stream()
                    except Exception:
                        pass
                    stream.close()
            except Exception:
                pass
            try:
                if pa is not None:
                    pa.terminate()
            except Exception:
                pass
            try:
                if wf is not None:
                    wf.close()
            except Exception:
                pass

            if self.signals is not None:
                try:
                    self._emit_main(self.signals.volume_changed.emit, 0)
                except Exception:
                    pass


class PyaudioBackend:

    MIN_FRAMES = 25  # minimum frames to start transcription

    def __init__(self, window=None):
        """
        Audio input capture core using PyAudio backend

        :param window: Window instance
        """
        self.window = window
        self.path = None
        self.frames = []
        self.loop = False
        self.stop_callback = None
        self.start_time = 0
        self.initialized = False
        self.pyaudio_instance = None
        self.pyaudio_instance_output = None
        self.stream = None
        self.stream_output = None
        self.mode = "input"  # input|control

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

        # realtime members (compatible with native backend)
        self._rt_session: Optional[RealtimeSessionPyAudio] = None
        self._rt_signals = None  # set by set_rt_signals()

        # input state guard (prevents races on stop)
        self._input_active = False

        # file playback worker + guard timer
        self._file_thread: Optional[_FilePlaybackThread] = None
        self._file_check_timer: Optional[QTimer] = None

    def init(self):
        """Initialize audio input backend."""
        import pyaudio
        if not self.initialized:
            self.format = pyaudio.paInt16   # Default input format
            self.pyaudio_instance = pyaudio.PyAudio()
            self.check_audio_devices()
            self.initialized = True

    def set_mode(self, mode: str):
        """
        Set input mode (input|control).

        :param mode: mode name
        """
        self.mode = mode

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

        :param path: file path
        """
        self.path = path

    def start(self) -> bool:
        """
        Start audio input recording using PyAudio.

        :return: True if started
        """
        self.init()
        self.frames = []
        self.prepare_device()
        if self.selected_device is None:
            print("No audio input device selected")
            return False
        if self.stream is not None:
            return False
        self.setup_audio_input()
        self.start_time = time.time()
        return True

    def stop(self) -> bool:
        """
        Stop audio input recording safely.

        :return: True if stopped (and file saved) or False otherwise.
        """
        result = False
        # block callback processing immediately
        self._input_active = False

        if self.stream is not None:
            try:
                self.stream.stop_stream()
            except Exception:
                pass
            try:
                self.stream.close()
            except Exception as e:
                print(f"Error closing input stream: {e}")
            self.stream = None

            if self.frames:
                if self.path:
                    try:
                        self.save_audio_file(self.path)
                        result = True
                    except Exception as e:
                        print(f"Error saving input WAV: {e}")
                else:
                    print("File path is not set.")
            else:
                print("No audio data recorded")

        # reset input meter
        try:
            self.reset_audio_level()
        except Exception:
            pass
        return result

    def has_source(self) -> bool:
        """
        Check if audio source is available.

        :return: True if available
        """
        return self.stream is not None

    def has_frames(self) -> bool:
        """
        Check if audio frames are available.

        :return: True if available
        """
        return bool(self.frames)

    def has_min_frames(self) -> bool:
        """
        Check if minimum required audio frames have been recorded.

        :return: True if min frames
        """
        return len(self.frames) >= self.MIN_FRAMES

    def reset_audio_level(self):
        """Reset the audio level bar."""
        self.window.controller.audio.ui.on_input_volume_change(0, self.mode)

    def check_audio_input(self) -> bool:
        """
        Check if default audio input device is working using PyAudio.

        :return: True if working
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
        except Exception:
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
            except Exception:
                continue

        if not self.devices:
            self.selected_device = None
            print("No audio input devices found.")
        else:
            self.selected_device = self.devices[0]['index']

    def device_changed(self, index: int):
        """
        Change audio input device based on device list index.

        :param index: index in self.devices list
        """
        self.init()
        if 0 <= index < len(self.devices):
            self.selected_device = self.devices[index]['index']
        else:
            self.selected_device = 0

    def prepare_device(self):
        """Set the current audio input device from configuration."""
        self.init()
        if self.window is not None and hasattr(self.window, "core"):
            device_id = int(self.window.core.config.get('audio.input.device', 0))
            self.device_changed(device_id)
        else:
            if self.devices:
                self.selected_device = self.devices[0]['index']
            else:
                self.selected_device = None

    def setup_audio_input(self):
        """Set up audio input device and start recording using PyAudio."""
        self.init()
        if self.selected_device is None:
            print("No audio input device selected")
            return

        try:
            self.stream = self.pyaudio_instance.open(format=self.format,
                                                     channels=self.channels,
                                                     rate=self.rate,
                                                     input=True,
                                                     frames_per_buffer=1024,
                                                     stream_callback=self._audio_callback)
            try:
                self.stream.start_stream()
            except Exception:
                pass
            self._input_active = True
        except Exception as e:
            print(f"Failed to open audio input stream: {e}")
            self.stream = None
            self._input_active = False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio input callback to process incoming audio data.

        :param in_data: audio data
        :param frame_count: number of frames
        :param time_info: timing information
        :param status: status flags
        """
        import pyaudio

        # If stop was requested, finish the callback loop cleanly
        if not self._input_active:
            return None, pyaudio.paComplete

        # Append raw data to the frames list for saving
        self.frames.append(in_data)

        # Compute input metering
        dtype = self.get_dtype_from_format(self.format)
        samples = np.frombuffer(in_data, dtype=dtype)
        if samples.size == 0:
            return None, pyaudio.paContinue

        rms = np.sqrt(np.mean(samples.astype(np.float64) ** 2))
        normalization_factor = self.get_normalization_factor(self.format)
        level = rms / normalization_factor
        level = min(max(level, 0.0), 1.0)
        level_percent = int(level * 100)

        # Update UI on the main thread only when recording is active
        if self._input_active:
            try:
                QTimer.singleShot(0, lambda: self.window.controller.audio.ui.on_input_volume_change(level_percent, self.mode))
            except Exception:
                pass

        # Handle loop recording if enabled.
        if self.loop and self.stop_callback is not None and self._input_active:
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

        :param level: volume level (0-100)
        """
        self.window.controller.audio.ui.on_input_volume_change(level, self.mode)

    def save_audio_file(self, filename: str):
        """
        Save the recorded audio frames to a WAV file.

        :param filename: path to save the WAV file
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

        :param fmt: PyAudio format
        :return: NumPy dtype
        """
        import pyaudio
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

        :param fmt: PyAudio format
        :return: normalization factor
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

        :return: True if stopped
        """
        return self.stop()

    def _stop_file_playback(self, signals=None, join_timeout: float = 1.0):
        """
        Cooperatively stop file playback worker and stop guard timer.

        :param signals: signals object to emit volume reset
        :param join_timeout: max seconds to wait for worker to join
        """
        try:
            if self._file_check_timer is not None:
                self._file_check_timer.stop()
        except Exception:
            pass
        self._file_check_timer = None

        t = self._file_thread
        self._file_thread = None
        if t is None:
            return
        try:
            t.request_stop()
        except Exception:
            pass
        try:
            t.join(timeout=join_timeout)
        except Exception:
            pass
        if signals is not None:
            try:
                signals.volume_changed.emit(0)
            except Exception:
                pass

    def _release_realtime_for_playback(self, wait_sec: float = 0.6):
        """
        Finalize realtime session to free the device before starting file playback.

        :param wait_sec: max seconds to wait for session to finalize
        """
        s = self._rt_session
        if not s:
            return
        try:
            s.stop()
        except Exception:
            pass
        self._rt_session = None
        t0 = time.time()
        while time.time() - t0 < wait_sec:
            time.sleep(0.02)

    def play(
            self,
            audio_file: str,
            event_name: str,
            stopped: callable,
            signals=None
    ):
        """
        Start non-blocking file playback on its own thread.
        Poll 'stopped()' on the GUI thread and request worker stop when needed.

        :param audio_file: path to audio file
        :param event_name: event name to emit on playback start
        :param stopped: callable that returns True when playback should stop
        :param signals: signals object to emit playback and volume events
        """
        # stop any previous file playback
        self._stop_file_playback(signals=signals, join_timeout=1.0)

        # ensure realtime session released
        self._release_realtime_for_playback(wait_sec=0.6)

        # emit start event in GUI
        if signals is not None:
            try:
                signals.playback.emit(event_name)
            except Exception:
                pass

        # select device and start worker
        dev_idx = self._select_output_device()
        t = _FilePlaybackThread(
            device_index=dev_idx,
            audio_file=audio_file,
            signals=signals
        )
        self._file_thread = t
        t.start()

        # guard timer: stop worker if 'stopped()' turns True; also cleanup when worker ends
        parent = self.window if isinstance(self.window, QObject) else None
        self._file_check_timer = QTimer(parent)
        self._file_check_timer.setInterval(100)

        def _tick():
            try:
                # stop requested by app
                if callable(stopped) and stopped():
                    self._stop_file_playback(signals=signals, join_timeout=1.0)
                    return
                # worker finished on its own
                if self._file_thread is None or not self._file_thread.is_alive():
                    self._stop_file_playback(signals=signals, join_timeout=0.0)
                    return
            except Exception:
                self._stop_file_playback(signals=signals, join_timeout=0.0)

        self._file_check_timer.timeout.connect(_tick)
        self._file_check_timer.start()

    def stop_playback(self, signals=None):
        """
        Stop audio playback (realtime and file-based) without cross-thread closes.

        :param signals: signals object to emit volume reset
        """
        # stop realtime session if any
        if self._rt_session:
            try:
                self._rt_session.stop()
            except Exception:
                pass
            self._rt_session = None

        # cooperatively stop file worker; do NOT close stream/terminate here
        self._stop_file_playback(signals=signals, join_timeout=1.0)

        # ensure UI meter is reset
        try:
            if signals is not None:
                signals.volume_changed.emit(0)
        except Exception:
            pass
        return False

    def get_input_devices(self) -> List[Tuple[int, str]]:
        """
        Get input devices list: [(id, name)].

        Uses BeautifulSoup's UnicodeDammit to ensure proper UTF-8 encoding.

        :return: list of (device index, device name)
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
        Get output devices using PyAudio.

        :return: list of (device index, device name)
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

        :return: (device index, device name)
        """
        import pyaudio
        p = pyaudio.PyAudio()
        try:
            default_info = p.get_default_input_device_info()
            device_id = default_info.get('index')
            device_name = default_info.get('name', 'Unknown')
        except IOError as e:
            print("Error getting default input device:", e)
            device_id, device_name = None, None
        p.terminate()
        return device_id, device_name

    def get_default_output_device(self) -> tuple:
        """
        Retrieve the default output device using PyAudio.

        :return: (device index, device name)
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

    # ---- REALTIME ----

    def set_rt_signals(self, signals) -> None:
        """
        Set signals object for realtime events.

        :param signals: signals object with 'response' and 'playback' signals
        """
        self._rt_signals = signals

    def set_signals(self, signals) -> None:
        """
        Alias to set_rt_signals

        :param signals: signals object with 'response' and 'playback' signals
        """
        self.set_rt_signals(signals)

    def _emit_output_volume(self, value: int) -> None:
        """
        Emit output volume change event (0-100) via rt_signals.

        :param value: volume level (0-100)
        """
        if not self._rt_signals:
            return
        try:
            self._rt_signals.response.emit(
                RealtimeEvent(RealtimeEvent.AUDIO_OUTPUT_VOLUME_CHANGED, {"volume": int(value)})
            )
        except Exception:
            pass

    def _select_output_device(self) -> int:
        """
        Select PyAudio output device index based on configuration or default.

        :return: device index
        """
        import pyaudio
        pa = pyaudio.PyAudio()
        try:
            cfg_idx = int(self.window.core.config.get('audio.output.device', -1)) \
                if self.window and hasattr(self.window, "core") else -1
        except Exception:
            cfg_idx = -1

        chosen = None
        if cfg_idx >= 0:
            try:
                di = pa.get_device_info_by_index(cfg_idx)
                if di.get('maxOutputChannels', 0) > 0:
                    chosen = cfg_idx
            except Exception:
                chosen = None

        if chosen is None:
            try:
                chosen = pa.get_default_output_device_info().get('index')
            except Exception:
                chosen = None

        if chosen is None:
            for i in range(pa.get_device_count()):
                try:
                    di = pa.get_device_info_by_index(i)
                    if di.get('maxOutputChannels', 0) > 0:
                        chosen = i
                        break
                except Exception:
                    continue

        pa.terminate()
        return int(chosen if chosen is not None else 0)

    def _probe_supported_format(
            self,
            device_index: int,
            rate: int,
            channels: int
    ) -> Tuple[int, int, int]:
        """
        Probe a supported (rate, channels, width_bytes=2) combination for the device.
        Prefers requested values; falls back to common rates/channels.

        :param device_index: PyAudio device index
        :param rate: desired sample rate
        :param channels: desired number of channels
        :return: (rate, channels, width_bytes)
        """
        import pyaudio
        pa = pyaudio.PyAudio()
        fmt = pyaudio.paInt16
        try_order = [
            (rate, channels),
            (rate, 2),
            (rate, 1),
            (44100, channels),
            (48000, channels),
            (44100, 2),
            (48000, 2),
            (44100, 1),
            (48000, 1),
        ]
        for sr, ch in try_order:
            try:
                if pa.is_format_supported(sr, output_device=device_index, output_channels=ch, output_format=fmt):
                    pa.terminate()
                    return int(sr), int(ch), 2
            except ValueError:
                continue
            except Exception:
                continue
        pa.terminate()
        return int(rate), int(channels), 2

    def _ensure_rt_session(self, rate: int, channels: int) -> RealtimeSessionPyAudio:
        """
        Ensure a realtime output session exists with a supported device format.
        Reuse only if still active and not finalized; otherwise recreate.

        :param rate: desired sample rate
        :param channels: desired number of channels
        :return: RealtimeSessionPyAudio instance
        """
        # make sure file playback is not holding the device
        self._stop_file_playback(join_timeout=0.8)

        dev_idx = self._select_output_device()
        out_rate, out_ch, out_w = self._probe_supported_format(dev_idx, rate, channels)

        s = self._rt_session
        if s is not None:
            try:
                same_fmt = (s.device_index == dev_idx and s.rate == out_rate and
                            s.channels == out_ch and s.width == out_w)
                if same_fmt and s.is_active() and not s.is_finalized():
                    return s
            except Exception:
                pass
            try:
                s.stop()
            except Exception:
                pass
            self._rt_session = None

        session = RealtimeSessionPyAudio(
            device_index=dev_idx,
            rate=out_rate,
            channels=out_ch,
            width_bytes=out_w,
            parent=None,
            volume_emitter=self._emit_output_volume
        )
        session.on_stopped = lambda: (
            self._rt_signals and self._rt_signals.response.emit(
                RealtimeEvent(RealtimeEvent.AUDIO_OUTPUT_END, {"source": "device"})
            ),
            setattr(self, "_rt_session", None)
        )
        self._rt_session = session
        return session

    def _convert_pcm_for_output(
            self, data: bytes,
            in_rate: int,
            in_channels: int,
            out_rate: int,
            out_channels: int,
            out_width: int = 2
    ) -> bytes:
        """
        Convert raw S16LE PCM to target (rate, channels, width).

        :param data: input PCM bytes
        :param in_rate: input sample rate
        :param in_channels: input number of channels
        :param out_rate: output sample rate
        :param out_channels: output number of channels
        :param out_width: output sample width in bytes (1, 2, or 4)
        """
        if not data:
            return b""
        try:
            src = data

            # channels
            if in_channels != out_channels:
                if in_channels == 2 and out_channels == 1:
                    src = audioop.tomono(src, 2, 0.5, 0.5)
                elif in_channels == 1 and out_channels == 2:
                    src = audioop.tostereo(src, 2, 1.0, 1.0)
                else:
                    mid = audioop.tomono(src, 2, 0.5, 0.5) if in_channels > 1 else src
                    src = audioop.tostereo(mid, 2, 1.0, 1.0) if out_channels == 2 else mid

            # sample rate
            if in_rate != out_rate:
                src, _ = audioop.ratecv(src, 2, out_channels, in_rate, out_rate, None)

            # sample width (keep Int16 by default)
            if out_width != 2:
                src = audioop.lin2lin(src, 2, out_width)

            return src
        except Exception:
            return data

    def stop_realtime(self):
        """Stop realtime audio playback session (friendly)."""
        s = self._rt_session
        if s is not None:
            try:
                s.mark_final()
            except Exception:
                try:
                    s.stop()
                except Exception:
                    pass

    def handle_realtime(self, payload: dict) -> None:
        """
        Handle realtime audio playback payload (compatible with native).
        Accepts dict with keys: data (bytes), mime (str), rate (int), channels (int), final (bool).

        :param payload: dict with audio data and parameters
        """
        try:
            data: bytes = payload.get("data", b"") or b""
            mime: str = (payload.get("mime", "audio/pcm") or "audio/pcm").lower()
            rate = int(payload.get("rate", 24000) or 24000)
            channels = int(payload.get("channels", 1) or 1)
            final = bool(payload.get("final", False))

            # only raw PCM/L16 is supported here
            if ("pcm" not in mime) and ("l16" not in mime):
                if final and self._rt_session is not None:
                    try:
                        self._rt_session.mark_final()
                    except Exception:
                        pass
                return

            session = self._ensure_rt_session(rate, channels)

            if data:
                # normalize to session format (assume input is S16LE)
                if session.rate != rate or session.channels != channels or session.width != 2:
                    data = self._convert_pcm_for_output(
                        data, in_rate=rate, in_channels=channels,
                        out_rate=session.rate, out_channels=session.channels,
                        out_width=session.width
                    )
                session.feed(data)

            if final:
                session.mark_final()

        except Exception as e:
            try:
                self.window.core.debug.log(f"[audio][pyaudio] handle_realtime error: {e}")
            except Exception:
                pass