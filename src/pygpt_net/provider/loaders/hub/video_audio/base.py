"""Video audio parser.

Contains parsers for mp3, mp4 files.

Based on: https://github.com/run-llama/llama_index/blob/main/llama-index-integrations/readers/llama-index-readers-file/llama_index/readers/file/video_audio/base.py

"""
import os.path
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, cast
from fsspec import AbstractFileSystem

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document

class VideoAudioReader(BaseReader):
    """Video audio parser.

    Extract text from transcript of video/audio files.

    """

    def __init__(
            self,
            *args: Any,
            model_version: str = "base",
            use_local: bool = False,
            window: None,
            **kwargs: Any
    ) -> None:
        """
        Init parser.

        :param args: arguments
        :param model_version: model version
        :param use_local: use local model
        :param window: Window instance
        :param kwargs: keyword arguments
        """
        super().__init__(*args, **kwargs)
        self._model_version = model_version
        self._use_local = use_local
        self._window = window
        self._initialized = False

    def _initialize(self) -> None:
        """Initialize parser."""
        try:
            import whisper
        except ImportError:
            raise ImportError(
                "Please install OpenAI whisper model "
                "'pip install git+https://github.com/openai/whisper.git' or pip install openai-whisper "
                "to use the model"
            )

        model = whisper.load_model(self._model_version)
        self.parser_config = {"model": model}
        self._initialized = True

    def _is_video(self, file: Path) -> bool:
        """
        Check if file is a video.

        :param file: file path
        :return: True if file is a video
        """
        return self._get_ext(file) in ["mp4", "avi", "mov", "mkv", "webm"]

    def _get_ext(self, file: Path) -> str:
        """
        Get file extension.

        :param file: file path
        :return: file extension
        """
        return file.suffix[1:]

    def _transcribe_local(self, file: Path) -> str:
        """
        Transcribe using local model.

        :param file: file path
        :return: transcript text
        """
        import whisper

        model = cast(whisper.Whisper, self.parser_config["model"])
        result = model.transcribe(str(file))
        return result["text"]

    def _transcribe_api(self, file: Path) -> str:
        """
        Transcribe using API.

        :param file: file path
        :return: transcript
        """
        return self._window.core.plugins.get("audio_input").get_provider().transcribe(str(file))

    def load_data(
        self,
        file: Path,
        extra_info: Optional[Dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> List[Document]:
        """
        Parse video.

        :param file: file path
        :param extra_info: additional metadata
        :param fs: file system
        :return: list of documents
        """
        if self._use_local:
            is_compiled = self._window.core.config.is_compiled() or self._window.core.platforms.is_snap()
            if is_compiled:
                raise ValueError("Local models are not available in compiled version.")

            if not self._initialized:
                self._initialize()

        post_delete = None
        if self._is_video(file):
            video_type = self._get_ext(file)

            try:
                from pydub import AudioSegment
            except ImportError:
                raise ImportError("Please install pydub 'pip install pydub' ")
            if fs:
                with fs.open(file, "rb") as f:
                    video = AudioSegment.from_file(f, format=video_type)
            else:
                # open file
                video = AudioSegment.from_file(file, format=video_type)

            # Extract audio from video
            audio = video.split_to_mono()[0]
            file_str = str(file)[:-4] + ".mp3"
            # export file, if file exists add date suffix
            if os.path.exists(file_str):
                date_suffix = datetime.now().strftime("%Y%m%d%H%M%S")
                file_str = str(file)[:-4] + "_" + date_suffix + ".mp3"
            audio.export(file_str, format="mp3")
            file = Path(file_str)
            post_delete = str(file)

        if self._use_local:
            transcript = self._transcribe_local(file)
        else:
            if self._window is None:
                raise ValueError("Window instance is required to use API model.")
            transcript = self._transcribe_api(file)

        # remove tmp file
        if post_delete:
            Path(post_delete).unlink()

        return [Document(text=transcript, metadata=extra_info or {})]