"""Diagnostic report on search_past_claims retrieval quality against the real
knowledge base and the real embedding model.
"""

import logging

from qdrant_client import QdrantClient

from app.config import get_settings
from app.constants.rag.claim_search_config import SIMILAR_CLAIMS_TOP_K
from app.constants.rag.knowledge_base_paths import knowledge_base_dir
from app.rag.claim_records import load_claim_records
from app.rag.embedder import ClaimEmbedder
from app.rag.ingest import ingest_claims
from app.tools.claim_search import search_past_claims
from evals.claim_search_queries import CLAIM_SEARCH_EVAL_CASES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reciprocal_rank(retrieved_claim_ids: list[str], expected_claim_ids: tuple[str, ...]) -> float:
    """1/rank of the first expected claim found in retrieved_claim_ids, or 0.0 if none appear."""
    for rank, claim_id in enumerate(retrieved_claim_ids, start=1):
        if claim_id in expected_claim_ids:
            return 1.0 / rank
    return 0.0


def run_eval() -> None:
    client = QdrantClient(url=get_settings().qdrant_url)
    embedder = ClaimEmbedder()
    records = load_claim_records(knowledge_base_dir())
    ingest_claims(client, records, embedder)

    reciprocal_ranks = []
    logger.info(
        "Evaluating %d hand-written queries (top_k=%d):",
        len(CLAIM_SEARCH_EVAL_CASES),
        SIMILAR_CLAIMS_TOP_K,
    )
    for case in CLAIM_SEARCH_EVAL_CASES:
        results = search_past_claims(case.query, client, embedder)
        retrieved_claim_ids = [result["claim_id"] for result in results]
        case_reciprocal_rank = reciprocal_rank(retrieved_claim_ids, case.expected_claim_ids)
        reciprocal_ranks.append(case_reciprocal_rank)

        found_rank = round(1 / case_reciprocal_rank) if case_reciprocal_rank > 0 else None
        logger.info(
            "  expected=%s found_at_rank=%s RR=%.2f | query=%r | retrieved=%s",
            case.expected_claim_ids,
            found_rank if found_rank is not None else "miss",
            case_reciprocal_rank,
            case.query,
            retrieved_claim_ids,
        )

    recall_at_k = sum(1 for rr in reciprocal_ranks if rr > 0) / len(reciprocal_ranks)
    mean_reciprocal_rank = sum(reciprocal_ranks) / len(reciprocal_ranks)
    logger.info("Recall@%d: %.1f%%", SIMILAR_CLAIMS_TOP_K, recall_at_k * 100)
    logger.info("MRR: %.3f", mean_reciprocal_rank)


if __name__ == "__main__":
    run_eval()
