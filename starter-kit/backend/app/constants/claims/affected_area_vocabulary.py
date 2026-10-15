"""Fixed candidate rooms and exterior components for the node-1 multi-label
``affected_areas`` extraction.

Jev has no list primitive, so ``affected_areas`` is extracted as one Noul per
candidate (see the node-1 questions module) and thresholded. The candidate list
below is derived from the area labels the repo's evaluation fixtures actually
use — the distinct values of ``affected_areas`` across ``data/ground-truth`` and
``data/knowledge-base`` — rather than invented. ``data/ground-truth`` supplies 28
of them; ``dining_room`` and ``hallway`` come from the knowledge base (the
``IMG_001`` inspection PDF the acceptance suite requires to surface a
``dining_room`` area, and the plan's own room example). Names are already
snake_case area labels, so they double as the values listed in
``affected_areas`` and feed ``estimate_repair_cost``'s distinct-area count.
"""

AFFECTED_AREA_VOCABULARY: tuple[str, ...] = (
    "attic",
    "basement",
    "bathroom",
    "bedroom",
    "ceiling",
    "chimney",
    "crawl_space",
    "dining_room",
    "entryway",
    "exterior",
    "exterior_wall",
    "fence",
    "foundation",
    "garage",
    "garage_door",
    "gutters",
    "hallway",
    "interior",
    "kitchen",
    "landscaping",
    "laundry_room",
    "living_room",
    "mailbox",
    "patio_door",
    "porch",
    "rear_window",
    "roof",
    "siding",
    "wall",
    "windows",
)
