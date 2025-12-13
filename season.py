"""Season container module.

The :class:`Season` class is a placeholder for season-level
functionality (standings, schedule, etc.). It can be extended as the
project grows.
"""

from team import Team
from week import Week
import numpy as np


class Season:
    """Representation of an NFL season.

    Currently a thin wrapper; intended to aggregate weeks, teams, and
    provide season-wide operations (scheduling, standings calculation,
    etc.).
    """

    def __init__(self):
        self.list_of_weeks : list[Week] = []

        self.team_name_to_team : dict[str, Team] = {}

    def add_team(self, name, conference, division, record=np.array([0, 0, 0])):
        team = Team(name=name, record=record, conference=conference, division=division)

        # Map team name to team object
        self.team_name_to_team[name] = team

    def simulate_season(self) -> None:
        assert (len(self.list_of_weeks) == 18), "NFL Season Must Have 18 Weeks"

        for week in self.list_of_weeks:
            week.simulate_games()