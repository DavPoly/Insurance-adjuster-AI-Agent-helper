from pathlib import Path

from app.tools.loader import load_json_table


def load_claim_records(directory: Path) -> list[dict]:
    """Load every historical claim JSON record from a knowledge-base directory.

    Args:
        directory: Directory containing one ``*.json`` file per claim record.

    Returns:
        The parsed JSON object from each file, in no particular order.
    """
    return [load_json_table(path) for path in sorted(directory.glob("*.json"))]


def build_embedding_text(record: dict) -> str:
    """Build the text to embed for a claim record.

    Args:
        record: A parsed claim record containing ``description`` and
            ``adjuster_notes`` fields.

    Returns:
        The description and adjuster notes joined by a blank line.
    """
    return f"{record['description']}\n\n{record['adjuster_notes']}"
