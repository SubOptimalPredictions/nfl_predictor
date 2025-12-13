"""Game simulation utilities.

This module defines the :class:`Game` class which represents a single
game between two :class:`Team` objects. Games can be simulated either
deterministically from a final score or probabilistically using a
two-element probability vector for the away/home team.
"""

import numpy as np
from team import Team


class Game:
    """Representation of a single matchup between two teams.

    Attributes:
        away_team (Team): The visiting team (index 0).
        home_team (Team): The home team (index 1).
        score (np.ndarray | None): If provided, a shape-(1, 2) array
            containing final scores [away_score, home_score]. If ``None``,
            the winner is chosen using ``probabilities``.
        probabilities (np.ndarray): Shape-(2,) array with the win
            probability for the away and home teams respectively. Used
            only when ``score`` is ``None``.
    """

    def __init__(self, away_team : Team, home_team : Team, score : np.ndarray | None, probabilities : np.ndarray):
        self.away_team : Team = away_team
        self.home_team : Team = home_team
        self.score : np.ndarray | None = score
        self.probabilities : np.ndarray = probabilities

    def simulate(self) -> None:
        """Simulate the game and update team records.

        If ``self.score`` is provided, the winner/loser/tie are determined
        from the scores. Otherwise, a winner is sampled using
        ``self.probabilities``. The method updates each team's record in
        place by calling ``Team.update_record`` with a (1, 3) numpy array
        representing increments of wins, losses, and ties respectively.

        Returns:
            None
        """

        if self.score is None:
            winner_id = np.random.choice(2, p=self.probabilities)
            away_team_record_delta, home_team_record_delta = self._generate_records(winner_id)
        else:
            away_team_record_delta, home_team_record_delta = self._generate_records_from_score(self.score)

        self.away_team.update_record(away_team_record_delta)
        self.home_team.update_record(home_team_record_delta)

    def _generate_records_from_score(self, score: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Generate record deltas from a final score.

        Args:
            score: A numpy array of shape (1, 2) or (2,) containing
                ``[away_score, home_score]``.

        Returns:
            Tuple of two numpy arrays (away_delta, home_delta), each of
            shape (1, 3) representing increments for [wins, losses, ties].
        """

        away_score, home_score = score.flatten()
        if away_score > home_score:
            return np.array([1, 0, 0]), np.array([0, 1, 0])
        elif away_score < home_score:
            return np.array([0, 1, 0]), np.array([1, 0, 0])
        elif away_score == home_score:
            return np.array([0, 0, 1]), np.array([0, 0, 1])
        else:
            raise NotImplementedError("Unhandled score comparison")

    def _generate_records(self, winning_id: int) -> tuple[np.ndarray, np.ndarray]:
        """Generate record deltas given the winning team's index.

        Args:
            winning_id: 0 if the away team won, 1 if the home team won.

        Returns:
            Tuple of two numpy arrays (away_delta, home_delta) with
            increments for [wins, losses, ties].
        """

        return np.array([1 - winning_id, winning_id, 0]), np.array([winning_id, 1 - winning_id, 0])