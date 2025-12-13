"""Team representation and record utilities.

This module provides the :class:`Team` class which stores a team's
identity and its season record as a numpy array with the layout
[wins, losses, ties].
"""

from typing import Dict
import numpy as np
import polars as pl
from utils import record_to_pct


class Team:
    """Model of an NFL team.

    Attributes:
        name (str): Team name.
        record (np.ndarray): Shape (1, 3) array for [wins, losses, ties].
        conference (str): Conference name.
        division (str): Division name.
    """

    def __init__(
        self,
        name: str,
        abbreviation: str,
        record: np.ndarray,
        conference: str,
        division: str,
    ):

        # Ensure Record is of the proper type and shape
        assert type(record) == np.ndarray
        assert record.shape == (1, 3)

        self.name: str = name
        self.abbreviation: str = abbreviation
        self.record: np.ndarray = record
        self.conference: str = conference
        self.division: str = division
        self.conference_record: np.ndarray = np.array([[0, 0, 0]])
        self.division_record: np.ndarray = np.array([[0, 0, 0]])
        # opponent abbreviation -> head-to-head record
        self.head_to_head_record: Dict[str, np.ndarray] = {}

    @staticmethod
    def load_teams_from_csv(
        filepath: str, load_existing_record=False
    ) -> Dict[str, "Team"]:
        """
        Load teams from a CSV file.
        Args:
            filepath: Path to the CSV file containing team data.
        Returns:
            A dictionary mapping team abbreviations to Team instances.
        """
        df = pl.read_csv(filepath)
        teams = {}
        for row in df.iter_rows(named=True):
            name = row["Name"]
            if load_existing_record:
                record = np.array([[row["Wins"], row["Losses"], row["Ties"]]])
            else:
                record = np.array([[0, 0, 0]])
            conference = row["Conference"]
            division = row["Division"]
            abbreviation = row["Abbreviation"]
            team = Team(name, abbreviation, record, conference, division)
            teams[abbreviation] = team
        return teams

    def get_record_pct(self, record_type="full"):
        if record_type == "full":
            return record_to_pct(self.record)
        elif record_type == "division":
            return record_to_pct(self.division_record)
        elif record_type == "conference":
            return record_to_pct(self.conference_record)
        else:
            raise NotImplementedError("Record Type?")

    def update_record(self, delta: np.ndarray, opponent_team: "Team") -> None:
        """Apply an increment to the team's record.

        Args:
            delta: A numpy array of shape (1, 3) representing the
                increments to add to `[wins, losses, ties]`.
            opposing_team: The opposing Team instance.

        The operation mutates ``self.record`` in place.
        """

        self.record += delta
        if self.conference == opponent_team.conference:
            self.conference_record += delta
        if self.division == opponent_team.division:
            self.division_record += delta
        self.head_to_head_record[opponent_team.abbreviation] = (
            self.head_to_head_record.get(
                opponent_team.abbreviation, np.array([[0, 0, 0]])
            )
            + delta
        )

    def _overall_record_lt(self, other):
        my_pct = self.get_record_pct()
        other_pct = other.get_record_pct()

        if my_pct < other_pct:
            return True
        elif my_pct > other_pct:
            return False

        return None

    def _h2h_record_lt(self, other):
        my_h2h_pct = record_to_pct(self.head_to_head_record[other.abbreviation])
        if my_h2h_pct < 0.5:
            return True
        elif my_h2h_pct > 0.5:
            return False
        return None

    def _division_record_lt(self, other):
        my_division_pct = self.get_record_pct(record_type="division")
        other_division_pct = other.get_record_pct(record_type="division")

        if my_division_pct < other_division_pct:
            return True
        elif my_division_pct > other_division_pct:
            return False

        return None

    def _conference_record_lt(self, other):
        my_conference_pct = self.get_record_pct(record_type="conference")
        other_conference_pct = other.get_record_pct(record_type="conference")

        if my_conference_pct < other_conference_pct:
            return True
        elif my_conference_pct > other_conference_pct:
            return False

        return None

    def __repr__(self) -> str:
        return f"Team(name={self.name}, abbreviation={self.abbreviation}, record={self.record}, conference={self.conference}, division={self.division}, conference_record={self.conference_record}, division_record={self.division_record})"


class DivisionTeamWrapper:
    def __init__(self, team):
        self.team = team

    def __lt__(self, other: "DivisionTeamWrapper"):
        comparisons = [
            self.team._overall_record_lt,
            self.team._h2h_record_lt,
            self.team._division_record_lt,
        ]

        for comparison in comparisons:
            result = comparison(other.team)
            if result is not None:
                return result

        raise NotImplementedError("OOps")


class ConferenceTeamWrapper:
    def __init__(self, team):
        self.team = team

    def __lt__(self, other: "ConferenceTeamWrapper"):
        comparisons = [
            self.team._h2h_record_lt,
            self.team._conference_record_lt,
        ]

        for comparison in comparisons:
            result = comparison(other)
            if result is not None:
                return result

        raise NotImplementedError("OOps")


if __name__ == "__main__":
    teams = Team.load_teams_from_csv("data/teams_with_records.csv")
    for name, team in teams.items():
        print(team)
