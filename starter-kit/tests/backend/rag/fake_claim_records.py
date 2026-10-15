"""Fixture claim records shaped like real starter-kit/data/knowledge-base/*.json files,
used by rag tests instead of the real (read-only) knowledge base.
"""

FAKE_CLAIM_ID_WATER_DAMAGE = "CLM-2099-001"
FAKE_CLAIM_DESCRIPTION_WATER_DAMAGE = "Burst pipe flooded the kitchen and basement overnight."
FAKE_CLAIM_ADJUSTER_NOTES_WATER_DAMAGE = "Confirmed with plumber invoice; no prior claims on file."

FAKE_CLAIM_ID_FIRE_DAMAGE = "CLM-2099-002"
FAKE_CLAIM_DESCRIPTION_FIRE_DAMAGE = "Kitchen fire caused smoke damage throughout the first floor."
FAKE_CLAIM_ADJUSTER_NOTES_FIRE_DAMAGE = "Fire department report attached; no fraud indicators."

FAKE_CLAIM_RECORD_WATER_DAMAGE = {
    "claim_id": FAKE_CLAIM_ID_WATER_DAMAGE,
    "damage_type": "water_damage",
    "severity": "moderate",
    "affected_areas": ["kitchen", "basement"],
    "description": FAKE_CLAIM_DESCRIPTION_WATER_DAMAGE,
    "adjuster_notes": FAKE_CLAIM_ADJUSTER_NOTES_WATER_DAMAGE,
    "policy_type": "standard_homeowner",
    "resolution": "paid",
}

FAKE_CLAIM_RECORD_FIRE_DAMAGE = {
    "claim_id": FAKE_CLAIM_ID_FIRE_DAMAGE,
    "damage_type": "fire_damage",
    "severity": "severe",
    "affected_areas": ["kitchen"],
    "description": FAKE_CLAIM_DESCRIPTION_FIRE_DAMAGE,
    "adjuster_notes": FAKE_CLAIM_ADJUSTER_NOTES_FIRE_DAMAGE,
    "policy_type": "premium_homeowner",
    "resolution": "paid",
}
