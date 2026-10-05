from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.provider.loaders.hub.yt.base import YoutubeTranscriptReader, NoTranscriptFound


@pytest.mark.parametrize('modern', [False, True])
def test_youtube_uses_available_polish_transcript_when_english_missing(monkeypatch, modern):
    selected = MagicMock()
    selected.fetch.return_value = [SimpleNamespace(text='Polska transkrypcja')] if modern else [{'text': 'Polska transkrypcja'}]
    transcripts = MagicMock()
    transcripts.find_transcript.side_effect = NoTranscriptFound('F3uvhqiKrcI', ['en'], '')
    transcripts.__iter__.return_value = iter([selected])
    method = MagicMock(return_value=transcripts)
    api = (lambda: SimpleNamespace(list=method)) if modern else SimpleNamespace(list_transcripts=method)
    monkeypatch.setattr('pygpt_net.provider.loaders.hub.yt.base.YouTubeTranscriptApi', api)
    docs = YoutubeTranscriptReader().load_data(['https://www.youtube.com/watch?v=F3uvhqiKrcI'])
    assert docs[0].text == 'Polska transkrypcja'
    assert docs[0].metadata['video_id'] == 'F3uvhqiKrcI'
    method.assert_called_once_with('F3uvhqiKrcI')


def test_youtube_prefers_requested_language_and_propagates_fetch_failure(monkeypatch):
    selected = MagicMock()
    selected.fetch.side_effect = RuntimeError('fetch failed')
    transcripts = MagicMock()
    transcripts.find_transcript.return_value = selected
    monkeypatch.setattr('pygpt_net.provider.loaders.hub.yt.base.YouTubeTranscriptApi', SimpleNamespace(list_transcripts=lambda video: transcripts))
    with pytest.raises(RuntimeError, match='fetch failed'):
        YoutubeTranscriptReader().load_data(['https://youtu.be/F3uvhqiKrcI'], languages=['pl'])
    transcripts.find_transcript.assert_called_once_with(['pl'])
