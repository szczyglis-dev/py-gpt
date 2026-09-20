from pygpt_net.core.types.chunk import ChunkType


def test_chunk_type_values_are_stable_strings():
    assert ChunkType.API_CHAT == "api_chat"
    assert ChunkType.API_CHAT_RESPONSES.value == "api_chat_responses"
    assert ChunkType.LLAMA_CHAT.value == "llama_chat"
    assert ChunkType.RAW.value == "raw"
