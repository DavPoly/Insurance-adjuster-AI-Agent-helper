EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_VECTOR_SIZE = 384
CLAIMS_COLLECTION_NAME = "historical_claims"

# BGE models are asymmetric: queries need this instruction prefix for best
# retrieval quality, passages being indexed do not.
QUERY_INSTRUCTION_PREFIX = "Represent this sentence for searching relevant passages: "
