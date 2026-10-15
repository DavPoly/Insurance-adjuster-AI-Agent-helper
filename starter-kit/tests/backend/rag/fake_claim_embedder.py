"""A fake ClaimEmbedder returning deterministic per-text vectors, so ingest tests
don't need the real embedding model.
"""


class FakeClaimEmbedder:
    def __init__(self, vector_for_text):
        self.vector_for_text = vector_for_text

    def embed_passages(self, texts):
        return [self.vector_for_text[text] for text in texts]
