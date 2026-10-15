# Chainlit recalculates its pin-last-user-message-to-top layout (spacer height,
# measured via a DOM walk) on every streamed message update. Pushing one
# word/whitespace token per update forced that recalculation 50x/sec, which
# visibly fought with the attached-image layout. Grouping tokens into chunks
# cuts the update frequency while keeping the same overall streaming pace.
STREAM_CHUNK_TOKEN_COUNT = 10
STREAM_CHUNK_DELAY_SECONDS = 0.1
