"""Pairs of ``AFFECTED_AREA_VOCABULARY`` labels where one names a more specific
form of the same exterior component as the other.

Maps each broader label to the specific label that supersedes it: siding is the
cladding of the exterior wall, and a rear window is one of the windows. When
both labels of a pair are flagged they describe one component, so node 1 keeps
only the specific one rather than counting the component twice (see
``_extract_affected_areas``). The broader label is kept when flagged on its own.
"""

SPECIFIC_COMPONENT_AREA_BY_BROADER_AREA: dict[str, str] = {
    "exterior_wall": "siding",
    "windows": "rear_window",
}
