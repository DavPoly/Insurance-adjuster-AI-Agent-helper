"""Per-level definitions for the node-1 ``severity`` Choice question.

Jev scores a Choice by comparing the claim against each criterion's text, so
each level carries its own definition rather than a bare label. The line
between minor and moderate is drawn by what must be repaired: one element
(cleaned, dried, refinished, or replaced) is minor, and a failed building
system or envelope section is moderate.

No level is defined by how many rooms the damage reaches: the repair estimate
already multiplies the per-area cost by the distinct affected-area count, so
raising severity for multi-room damage would count that spread twice (the
IMG_001 inspection fixture states "moderate water damage in exactly two rooms").
"""

from app.constants.claims.claim_taxonomy import SeverityLevel

SEVERITY_LEVEL_DEFINITIONS: dict[SeverityLevel, str] = {
    SeverityLevel.MINOR: (
        "Localized damage to a single element, fixed by cleaning, drying, refinishing, or "
        "replacing just that element (for example one window or pane, a lock, a gutter run, a "
        "patch of flooring or carpet, an exterior surface that needs cleaning or repainting, a "
        "freestanding item such as a mailbox). Water released by an appliance or fixture that "
        "wets the floor and lower wall is still minor when the building's own plumbing has not "
        "failed. The building's systems, envelope, and structure are intact."
    ),
    SeverityLevel.MODERATE: (
        "A building system or a section of the building envelope has failed and must be repaired "
        "or replaced (for example a ruptured supply line or failed water heater, a section of "
        "roofing or siding, an exterior door together with its frame, a whole door or glazing "
        "assembly), or fire, smoke, or mold has spread across several surfaces of one room. "
        "Contained to one room or component, with load-bearing structure intact."
    ),
    SeverityLevel.SEVERE: (
        "Load-bearing structure is damaged (framing, rafters, beams, joists, foundation), or a "
        "space holds standing water, or fire, impact, or intrusion has wrecked a room's fixtures, "
        "furnishings, and finishes throughout."
    ),
    SeverityLevel.CATASTROPHIC: (
        "The main structure has collapsed or is a total loss, or the home is unsafe or "
        "uninhabitable."
    ),
}
