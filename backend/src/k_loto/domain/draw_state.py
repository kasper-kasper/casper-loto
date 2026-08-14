"""Draw lifecycle state machine."""

from k_loto.domain.enums import DrawStatus
from k_loto.domain.errors import InvalidStateTransition

ALLOWED_DRAW_TRANSITIONS: dict[DrawStatus, frozenset[DrawStatus]] = {
    DrawStatus.SCHEDULED: frozenset({DrawStatus.CLOSED, DrawStatus.DRAWING}),
    DrawStatus.CLOSED: frozenset({DrawStatus.DRAWING}),
    DrawStatus.DRAWING: frozenset({DrawStatus.SETTLING, DrawStatus.FAILED}),
    DrawStatus.SETTLING: frozenset({DrawStatus.COMPLETED, DrawStatus.FAILED}),
    DrawStatus.FAILED: frozenset({DrawStatus.DRAWING}),
    DrawStatus.COMPLETED: frozenset(),
}


def ensure_draw_transition(current: DrawStatus, target: DrawStatus) -> None:
    """Raise when a transition would violate the immutable lifecycle."""
    if target not in ALLOWED_DRAW_TRANSITIONS[current]:
        raise InvalidStateTransition(
            f"Cannot transition draw from {current} to {target}."
        )
