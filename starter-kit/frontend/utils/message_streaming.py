import asyncio
import re

import chainlit as cl

from constants.message_stream_chunking import (
    STREAM_CHUNK_DELAY_SECONDS,
    STREAM_CHUNK_TOKEN_COUNT,
)

_WHITESPACE_RUN_PATTERN = re.compile(r"(\s+)")


async def send_streamed_message(
    content: str, elements: list | None = None, actions: list | None = None
) -> cl.Message:
    message = cl.Message(content="", elements=elements or [], actions=actions or [])
    await message.send()
    tokens = [token for token in _WHITESPACE_RUN_PATTERN.split(content) if token]
    for chunk_start in range(0, len(tokens), STREAM_CHUNK_TOKEN_COUNT):
        chunk = "".join(tokens[chunk_start : chunk_start + STREAM_CHUNK_TOKEN_COUNT])
        await message.stream_token(chunk)
        await asyncio.sleep(STREAM_CHUNK_DELAY_SECONDS)
    await message.update()
    return message
