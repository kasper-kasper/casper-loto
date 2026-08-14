"""Expected business-rule failures."""


class DomainError(Exception):
    """Base class for expected domain failures."""


class InvalidStateTransition(DomainError):
    """The requested state transition is forbidden."""


class InvalidTicket(DomainError):
    """A ticket combination violates its lottery rules."""


class InsufficientBalance(DomainError):
    """The user cannot fund a purchase."""


class InsufficientReserve(DomainError):
    """Guaranteed payouts exceed the distribution fund and reserve."""


class NoAvailableDraw(DomainError):
    """No future draw is open for ticket sales."""


class ConfigurationError(DomainError):
    """Lottery configuration is incomplete or inconsistent."""
