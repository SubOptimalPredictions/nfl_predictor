"""Team representation and record utilities.

This module provides the :class:`Team` class which stores a team's
identity and its season record as a numpy array with the layout
[wins, losses, ties].
"""

from typing import Dict
import numpy as np
import polars as pl


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

    @staticmethod
    def load_teams_from_csv(filepath: str, load_existing_record=False) -> Dict[str, "Team"]:
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

    def update_record(self, delta: np.ndarray) -> None:
        """Apply an increment to the team's record.

        Args:
            delta: A numpy array of shape (1, 3) representing the
                increments to add to `[wins, losses, ties]`.

        The operation mutates ``self.record`` in place.
        """

        self.record += delta

    def __repr__(self) -> str:
        return f"Team(name={self.name}, abbreviation={self.abbreviation}, record={self.record}, conference={self.conference}, division={self.division})"


if __name__ == "__main__":
    teams = Team.load_teams_from_csv("data/teams_with_records.csv")
    for name, team in teams.items():
        print(team)
