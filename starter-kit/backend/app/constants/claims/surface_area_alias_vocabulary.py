"""The labels in ``AFFECTED_AREA_VOCABULARY`` that name a surface of a room or
component rather than a distinct area.

The cost table's counting rule (``tools/cost-estimator.json``) and
:data:`~app.constants.claims.area_counting_rule.AREA_COUNTING_RULE` both say a
room must not be counted again for its own wall or floor. Jev scores each area
as an independent per-question probability, so it routinely flags ``wall`` or
``ceiling`` next to the room it belongs to and doubles the repair estimate.
Node 1 drops these surfaces deterministically whenever a specific room or
component is flagged, and keeps them only when they are the whole scope (see
``_extract_affected_areas``).
"""

SURFACE_AREA_ALIASES: tuple[str, ...] = ("ceiling", "wall")
