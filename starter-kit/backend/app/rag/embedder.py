from app.constants.rag.claim_embedding_config import EMBEDDING_MODEL_NAME, QUERY_INSTRUCTION_PREFIX


class ClaimEmbedder:
    """Embeds claim text with a local sentence-transformers model.

    BGE models are asymmetric: passages being indexed are encoded as-is, while
    queries get an instruction prefix for best retrieval quality.
    """

    def __init__(self, model=None):
        if model is None:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self._model = model

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._model.encode(QUERY_INSTRUCTION_PREFIX + text).tolist()
