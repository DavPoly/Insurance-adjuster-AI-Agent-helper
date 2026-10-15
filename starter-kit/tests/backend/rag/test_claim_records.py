import json

from fake_claim_records import (
    FAKE_CLAIM_ADJUSTER_NOTES_WATER_DAMAGE,
    FAKE_CLAIM_DESCRIPTION_WATER_DAMAGE,
    FAKE_CLAIM_ID_FIRE_DAMAGE,
    FAKE_CLAIM_ID_WATER_DAMAGE,
    FAKE_CLAIM_RECORD_FIRE_DAMAGE,
    FAKE_CLAIM_RECORD_WATER_DAMAGE,
)

from app.rag.claim_records import build_embedding_text, load_claim_records


def test_load_claim_records_reads_every_json_file_in_directory(tmp_path):
    (tmp_path / "CLM-2099-001.json").write_text(json.dumps(FAKE_CLAIM_RECORD_WATER_DAMAGE))
    (tmp_path / "CLM-2099-002.json").write_text(json.dumps(FAKE_CLAIM_RECORD_FIRE_DAMAGE))

    records = load_claim_records(tmp_path)

    claim_ids = {record["claim_id"] for record in records}
    assert claim_ids == {FAKE_CLAIM_ID_WATER_DAMAGE, FAKE_CLAIM_ID_FIRE_DAMAGE}


def test_build_embedding_text_combines_description_and_adjuster_notes():
    text = build_embedding_text(FAKE_CLAIM_RECORD_WATER_DAMAGE)

    assert text == (
        f"{FAKE_CLAIM_DESCRIPTION_WATER_DAMAGE}\n\n{FAKE_CLAIM_ADJUSTER_NOTES_WATER_DAMAGE}"
    )
