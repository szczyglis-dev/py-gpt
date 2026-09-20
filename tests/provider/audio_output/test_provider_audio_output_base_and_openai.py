import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.provider.audio_output.base import BaseProvider
from pygpt_net.provider.audio_output.openai_tts import OpenAITextToSpeech


def plugin(tmp_path, model="tts-1", voice="alloy"):
    client = MagicMock()
    values = {"openai_model": model, "openai_voice": voice}
    p = MagicMock()
    p.output_file = "speech.mp3"
    p.get_option_value.side_effect = lambda key: values.get(key)
    p.window = SimpleNamespace(core=SimpleNamespace(
        config=SimpleNamespace(path=str(tmp_path)),
        api=SimpleNamespace(openai=SimpleNamespace(get_client=MagicMock(return_value=client))),
        audio=SimpleNamespace(whisper=SimpleNamespace(get_voices=MagicMock(return_value=["alloy"]))),
    ))
    return p, client


def test_audio_output_base_contract_and_init(tmp_path):
    p, _ = plugin(tmp_path)
    base = BaseProvider()
    base.init_options = MagicMock()
    base.init(p)
    assert base.plugin is p
    base.init_options.assert_called_once_with()
    assert base.speech("x") is None
    assert base.is_configured() is None
    assert "Google API key" in base.get_config_message()


def test_prepare_output_path_is_unique_extension_aware_and_creates_directory(tmp_path):
    p, _ = plugin(tmp_path)
    base = BaseProvider(p)
    with patch("pygpt_net.provider.audio_output.base.uuid.uuid4") as uid:
        uid.side_effect = [SimpleNamespace(hex="a"), SimpleNamespace(hex="b")]
        first = base.prepare_output_path()
        open(first, "wb").close()
        second = base.prepare_output_path("wav")
    assert first.endswith("speech_a.mp3")
    assert second.endswith("speech_b.wav")
    assert os.path.isdir(tmp_path / "tmp" / "audio_output")


def test_cleanup_output_dir_uses_file_mtimes_not_local_datetimes(tmp_path):
    output = tmp_path / "audio"
    output.mkdir()
    files = []
    for i, ts in enumerate((1_700_000_003, 1_700_000_001, 1_700_000_002)):
        path = output / f"{i}.mp3"
        path.write_bytes(b"x")
        os.utime(path, (ts, ts))
        files.append(path)
    (output / "subdir").mkdir()

    BaseProvider._cleanup_output_dir(str(output), keep_files=2)

    assert not files[1].exists()
    assert files[0].exists() and files[2].exists()
    assert (output / "subdir").exists()


def test_cleanup_output_dir_tolerates_directory_and_file_errors(tmp_path):
    with patch("pygpt_net.provider.audio_output.base.os.listdir", side_effect=OSError("dir")):
        BaseProvider._cleanup_output_dir(str(tmp_path), 1)

    output = tmp_path / "audio"; output.mkdir()
    f = output / "a.mp3"; f.write_bytes(b"x")
    with patch("pygpt_net.provider.audio_output.base.os.path.getmtime", side_effect=OSError("stat")):
        BaseProvider._cleanup_output_dir(str(output), 0)
    assert f.exists()


def test_openai_tts_options_speech_and_configuration_use_mocked_sdk(tmp_path):
    p, client = plugin(tmp_path, model="tts-1-hd", voice="nova")
    provider = OpenAITextToSpeech(plugin=p)
    provider.init_options()
    assert [c.args[0] for c in p.add_option.call_args_list] == ["openai_model", "openai_voice"]
    provider.prepare_output_path = MagicMock(return_value=str(tmp_path / "tts.mp3"))
    response = client.audio.speech.create.return_value

    assert provider.speech("hello") == str(tmp_path / "tts.mp3")
    client.audio.speech.create.assert_called_once_with(model="tts-1-hd", voice="nova", input="hello")
    response.stream_to_file.assert_called_once_with(str(tmp_path / "tts.mp3"))
    assert provider.is_configured() is True
    assert provider.get_config_message() == ""
