"""Season container module.

The :class:`Season` class is a placeholder for season-level
functionality (standings, schedule, etc.). It can be extended as the
project grows.
"""

from week import Week


class Season:
    """Representation of an NFL season.

    Currently a thin wrapper; intended to aggregate weeks, teams, and
    provide season-wide operations (scheduling, standings calculation,
    etc.).
    """

    def __init__(self):
        pass