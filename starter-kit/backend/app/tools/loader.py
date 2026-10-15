import json
from pathlib import Path


def load_json_table(path: Path) -> dict:
    """Load a JSON lookup table from disk.

    Reads with the ``utf-8-sig`` encoding so a leading UTF-8 byte-order mark is
    tolerated if present, while plain UTF-8 files are read normally.
    """
    return json.loads(path.read_text(encoding="utf-8-sig"))
