"""The two umbrella labels in ``AFFECTED_AREA_VOCABULARY`` that restate a
specific room or component rather than naming a distinct one.

:data:`~app.constants.claims.area_counting_rule.AREA_COUNTING_RULE` tells Jev
not to flag one of these alongside a specific room already listed, but each
area is scored as an independent per-question probability with no visibility
into the other answers, so Jev cannot reliably self-enforce that rule. Node 1
applies it deterministically instead (see ``_extract_affected_areas``): these
are the least specific labels, dropped whenever a specific area or a surface
alias is flagged.
"""

GENERIC_AREA_ALIASES: tuple[str, ...] = ("interior", "exterior")
