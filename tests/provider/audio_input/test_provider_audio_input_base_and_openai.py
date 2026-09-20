from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.provider.audio_input.base import BaseProvider
from pygpt_net.provider.audio_input.openai_whisper import OpenAIWhisper


def plugin(api_key="key", model="whisper-1"):
    client = MagicMock()
    core = SimpleNamespace(
        api=SimpleNamespace(openai=SimpleNamespace(get_client=MagicMock(return_value=client))),
        config=SimpleNamespace(get=MagicMock(return_value=api_key)),
    )
    p = MagicMock()
    p.window = SimpleNamespace(core=core)
    p.get_option_value.return_value = model
    return p, client


def test_audio_input_base_contract_and_init():
    p, _ = plugin()
    base = BaseProvider()
    base.init_options = MagicMock()
    base.init(p)
    assert base.plugin is p
    base.init_options.assert_called_once_with()
    assert base.transcribe("x.wav") is None
    assert base.is_configured() is None
    assert base.get_config_message() == ""


def test_openai_whisper_options_configuration_and_message():
    p, _ = plugin(api_key="key")
    provider = OpenAIWhisper(plugin=p)
    assert provider.id == "openai_whisper"
    provider.init_options()
    p.add_option.assert_called_once()
    assert p.add_option.call_args.args[0] == "whisper_model"
    assert provider.is_configured() is True
    p.window.core.config.get.return_value = ""
    assert provider.is_configured() is False
    p.window.core.config.get.return_value = None
    assert provider.is_configured() is False
    assert "OpenAI API key" in provider.get_config_message()


def test_openai_whisper_transcribe_uses_mocked_sdk(tmp_path):
    p, client = plugin(model="whisper-1")
    client.audio.transcriptions.create.return_value = "transcript"
    provider = OpenAIWhisper(plugin=p)
    path = tmp_path / "audio.wav"
    path.write_bytes(b"RIFF")

    assert provider.transcribe(str(path)) == "transcript"
    kwargs = client.audio.transcriptions.create.call_args.kwargs
    assert kwargs["model"] == "whisper-1"
    assert kwargs["response_format"] == "text"
    assert kwargs["file"].name == str(path)
    assert kwargs["file"].closed is True
