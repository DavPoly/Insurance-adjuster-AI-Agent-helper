"""A minimal stand-in for sentence_transformers.SentenceTransformer, recording
what it was asked to encode so tests can assert on it without loading a real model.
"""


class FakeEmbeddingVector:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values


class FakeEmbeddingModel:
    def __init__(self, vector_for_text):
        self.vector_for_text = vector_for_text
        self.encode_calls = []

    def encode(self, value):
        self.encode_calls.append(value)
        if isinstance(value, list):
            return FakeEmbeddingVector([self.vector_for_text[text] for text in value])
        return FakeEmbeddingVector(self.vector_for_text[value])
