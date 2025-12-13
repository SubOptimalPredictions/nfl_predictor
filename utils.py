import math
import numpy as np

def moneyline_to_probability(away_team_moneyline: int, home_team_moneyline: int) -> np.ndarray:
    """
    returns: [away_team_win_prob, home_team_win_prob] probabilities are between [0, 1]
    """
    if away_team_moneyline < 0:
        # Home Team is Favorite
        away_team_win_prob_vig = (abs(away_team_moneyline) / (abs(away_team_moneyline) + 100))
        home_team_win_prob_vig = (100 / (abs(home_team_moneyline) + 100))

        away_team_win_prob = (away_team_win_prob_vig / (away_team_win_prob_vig + home_team_win_prob_vig))
        home_team_win_prob = (home_team_win_prob_vig / (away_team_win_prob_vig + home_team_win_prob_vig))

        result = np.array([away_team_win_prob, home_team_win_prob])
    elif home_team_moneyline < 0:
        # Away Team is Favorite
        away_team_win_prob_vig = (100 / (abs(away_team_moneyline) + 100))
        home_team_win_prob_vig = (abs(home_team_moneyline) / (abs(home_team_moneyline) + 100))

        away_team_win_prob = (away_team_win_prob_vig / (away_team_win_prob_vig + home_team_win_prob_vig))
        home_team_win_prob = (home_team_win_prob_vig / (away_team_win_prob_vig + home_team_win_prob_vig))
        
        result = np.array([away_team_win_prob, home_team_win_prob])
    else:
        raise NotImplementedError("What kind of betting is this?")

    assert (np.isclose(np.sum(result), 1)), "Probabilities are not normalized"
    return result

def record_to_pct(record):
    record = record[0]
    return (record[0] + 0.5 * record[2]) / np.sum(record)

if __name__ == '__main__':
    print(moneyline_to_probability(410, -550))