from pathlib import Path
from typing import Dict, List, Optional

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document, ImageDocument
from llama_index.core.utils import infer_torch_device


class ImageVisionLLMReader(BaseReader):
    """Image parser.

    Caption image using Blip2 (a multimodal vision-language model).

    Based on: https://github.com/run-llama/llama_index/blob/main/llama-index-integrations/readers/llama-index-readers-file/llama_index/readers/file/image_vision_llm/base.py

    """

    def __init__(
        self,
        use_local: bool = False,
        window = None,
        keep_image: bool = False,
        api_prompt: str = "Describe what you see in this image",
        api_model: str = "gpt-4o",
        api_tokens: int = 1000,
        local_prompt: str = "Question: describe what you see in this image. Answer:",
    ):
        """
        Init params.

        :param use_local: use local model
        :param window: Window instance
        :param keep_image: keep image in document
        :param api_prompt: API prompt
        :param api_model: API model
        :param api_tokens: API tokens
        :param local_prompt: local prompt
        """
        self._initialized = False
        self._use_local = use_local
        self._api_prompt = api_prompt
        self._api_model = api_model
        self._api_tokens = api_tokens
        self._window = window

        self._parser_config = None
        self._keep_image = keep_image
        self._local_prompt = local_prompt

    def _initialize(self) -> None:
        """Initialize local parser."""
        parser_config = None
        if self._parser_config is None:
            try:
                import sentencepiece  # noqa
                import torch
                from PIL import Image  # noqa
                from transformers import Blip2ForConditionalGeneration, Blip2Processor
            except ImportError:
                raise ImportError(
                    "Please install extra dependencies that are required for "
                    "the ImageVisionLLMReader: "
                    "`pip install torch transformers sentencepiece Pillow`"
                )

            device = infer_torch_device()
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
            model = Blip2ForConditionalGeneration.from_pretrained(
                "Salesforce/blip2-opt-2.7b", torch_dtype=dtype
            )
            parser_config = {
                "processor": processor,
                "model": model,
                "device": device,
                "dtype": dtype,
            }

        self._parser_config = parser_config
        self._initialized = True

    def load_local(self, file: Path, extra_info: Optional[Dict] = None) -> List[Document]:
        """
        Describe image using local model.

        :param file: file path
        :param extra_info: additional metadata
        :return: list of documents
        """
        if not self._initialized:
            self._initialize()

        from llama_index.core.img_utils import img_2_b64
        from PIL import Image

        # load document image
        image = Image.open(file)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Encode image into base64 string and keep in document
        image_str: Optional[str] = None
        if self._keep_image:
            image_str = img_2_b64(image)

        # Parse image into text
        model = self._parser_config["model"]
        processor = self._parser_config["processor"]

        device = self._parser_config["device"]
        dtype = self._parser_config["dtype"]
        model.to(device)

        # unconditional image captioning
        inputs = processor(image, self._local_prompt, return_tensors="pt").to(device, dtype)
        out = model.generate(**inputs)
        text_str = processor.decode(out[0], skip_special_tokens=True)

        return [
            ImageDocument(
                text=text_str,
                image=image_str,
                image_path=str(file),
                metadata=extra_info or {},
            )
        ]

    def load_api(self, file: Path, extra_info: Optional[Dict] = None) -> List[Document]:
        """
        Describe image using the selected image-capable model/provider.

        :param file: file path
        :param extra_info: additional metadata
        :return: list of documents
        """
        from llama_index.core.img_utils import img_2_b64
        from PIL import Image

        from pygpt_net.core.bridge.context import BridgeContext
        from pygpt_net.core.types import MODE_CHAT
        from pygpt_net.item.attachment import AttachmentItem
        from pygpt_net.item.ctx import CtxItem

        # Encode image into base64 string and keep in document when requested.
        image_str: Optional[str] = None
        if self._keep_image:
            image = Image.open(file)
            if image.mode != "RGB":
                image = image.convert("RGB")
            image_str = img_2_b64(image)

        core = self._window.core
        if not self._api_model or not core.models.has(self._api_model):
            raise ValueError(f"Image model is not available: {self._api_model}")

        model = core.models.get(self._api_model)
        if not model.is_image_input():
            raise ValueError(
                f"Selected image model does not declare Image input support: {self._api_model}"
            )

        attachment = AttachmentItem()
        attachment.path = str(file)
        attachment.name = file.name

        tmp_ctx = CtxItem(mode=MODE_CHAT)
        context = BridgeContext(
            ctx=tmp_ctx,
            prompt=self._api_prompt,
            attachments={"image": attachment},
            history=[],
            stream=False,
            model=model,
            mode=MODE_CHAT,
            parent_mode=MODE_CHAT,
            max_tokens=self._api_tokens,
            request=True,
        )

        # Follow the same native-provider routing policy as regular chat/vision
        # requests instead of forcing every image model through OpenAI.
        api = core.api.openai
        if model.provider == "google" and core.config.get("api_native_google", False):
            api = core.api.google
        elif model.provider == "anthropic" and core.config.get("api_native_anthropic", False):
            api = core.api.anthropic
        elif model.provider == "x_ai" and core.config.get("api_native_xai", False):
            api = core.api.xai

        text = (api.quick_call(context=context, extra={}) or "").strip()
        if not text:
            raise ValueError(f"Image analysis returned an empty response: {self._api_model}")

        return [
            ImageDocument(
                text=text,
                image=image_str,
                image_path=str(file),
                metadata=extra_info or {},
            )
        ]

    def load_data(
        self, file: Path, extra_info: Optional[Dict] = None
    ) -> List[Document]:
        """
        Parse file.

        :param file: file path
        :param extra_info: additional metadata
        :return: list of documents
        """
        if self._use_local:
            is_compiled = self._window.core.config.is_compiled() or self._window.core.platforms.is_snap()
            if is_compiled:
                raise ValueError("Local models are not available in compiled version.")
            return self.load_local(file, extra_info)
        else:
            if self._window is None:
                raise ValueError("Window instance is required to use API model.")
            return self.load_api(file, extra_info)

    def load_data_custom(
        self, file: Path, extra_info: Optional[Dict] = None, **kwargs
    ) -> List[Document]:
        """
        Parse file.

        :param file: file path
        :param extra_info: additional metadata
        :param kwargs: additional arguments
        :return: list of documents
        """
        extra_args = kwargs.get("extra_args", {})
        if self._use_local:
            is_compiled = self._window.core.config.is_compiled() or self._window.core.platforms.is_snap()
            if is_compiled:
                raise ValueError("Local models are not available in compiled version.")
            return self.load_local(file, extra_info)
        else:
            if self._window is None:
                raise ValueError("Window instance is required to use API model.")
            return self.load_api(file, extra_info)
