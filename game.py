import numpy as np
from team import Team

class Game():
    def __init__(self, away_team : Team, home_team : Team, score : np.ndarray, probabilities : np.ndarray):
        self.away_team : Team = away_team # id: 0
        self.home_team : Team = home_team # id: 1
        self.score : np.ndarray = score # (1, 2) -> [away_team score, home_team score]
        self.probabilities : np.ndarray = probabilities # (1, 2) -> [away_team win probability, home_team win probability]

    def simulate(self):
        """
        Docstring for simulate
        
        :param self: Description

        returns away team record delta, home team record delta
        """
        winner_id = np.random.choice(2, p=self.probabilities)
        away_team_record_delta, home_team_record_delta = self._generate_records(winner_id)

        self.away_team.update_record(away_team_record_delta)
        self.home_team.update_record(home_team_record_delta)

    def _generate_records(self, winning_id):
        return np.array([1 - winning_id, winning_id, 0]), np.array([winning_id, 1 - winning_id, 0])