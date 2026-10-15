from fake_embedding_model import FakeEmbeddingModel
from fake_embedding_vectors import (
    FAKE_EMBEDDING_PASSAGE_TEXT_ONE,
    FAKE_EMBEDDING_PASSAGE_TEXT_TWO,
    FAKE_EMBEDDING_PASSAGE_VECTOR_ONE,
    FAKE_EMBEDDING_PASSAGE_VECTOR_TWO,
    FAKE_EMBEDDING_QUERY_TEXT,
    FAKE_EMBEDDING_QUERY_VECTOR,
)

from app.constants.rag.claim_embedding_config import EMBEDDING_VECTOR_SIZE, QUERY_INSTRUCTION_PREFIX
from app.rag.embedder import ClaimEmbedder


def test_embed_passages_encodes_texts_without_a_prefix():
    model = FakeEmbeddingModel(
        vector_for_text={
            FAKE_EMBEDDING_PASSAGE_TEXT_ONE: FAKE_EMBEDDING_PASSAGE_VECTOR_ONE,
            FAKE_EMBEDDING_PASSAGE_TEXT_TWO: FAKE_EMBEDDING_PASSAGE_VECTOR_TWO,
        }
    )
    embedder = ClaimEmbedder(model=model)

    vectors = embedder.embed_passages(
        [FAKE_EMBEDDING_PASSAGE_TEXT_ONE, FAKE_EMBEDDING_PASSAGE_TEXT_TWO]
    )

    assert vectors == [FAKE_EMBEDDING_PASSAGE_VECTOR_ONE, FAKE_EMBEDDING_PASSAGE_VECTOR_TWO]
    assert model.encode_calls == [
        [FAKE_EMBEDDING_PASSAGE_TEXT_ONE, FAKE_EMBEDDING_PASSAGE_TEXT_TWO]
    ]


def test_embed_query_prepends_the_query_instruction_prefix():
    prefixed_text = QUERY_INSTRUCTION_PREFIX + FAKE_EMBEDDING_QUERY_TEXT
    model = FakeEmbeddingModel(vector_for_text={prefixed_text: FAKE_EMBEDDING_QUERY_VECTOR})
    embedder = ClaimEmbedder(model=model)

    vector = embedder.embed_query(FAKE_EMBEDDING_QUERY_TEXT)

    assert vector == FAKE_EMBEDDING_QUERY_VECTOR
    assert model.encode_calls == [prefixed_text]


def test_embed_passages_with_the_real_model_returns_configured_vector_size():
    embedder = ClaimEmbedder()

    vectors = embedder.embed_passages([FAKE_EMBEDDING_PASSAGE_TEXT_ONE])

    assert len(vectors) == 1
    assert len(vectors[0]) == EMBEDDING_VECTOR_SIZE
