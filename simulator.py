from season import Season
from collections import defaultdict
from team import Team
import numpy as np
import time

def get_aggregator_dict():
    teams = Team.load_teams_from_csv("data/teams_with_records.csv")
    aggregator = {}

    for _, team in teams.items():
        aggregator[team.abbreviation] = np.array([0] * 16)
    return aggregator

def aggregate_final_ranking(aggregator, nfc_ranking, afc_ranking):
    for i, team in enumerate(nfc_ranking):
        aggregator[team.abbreviation][i] += 1

    for i, team in enumerate(afc_ranking):
        aggregator[team.abbreviation][i] += 1

def simulate_single_season():
    season = Season.load_season(teams_file_path="data/teams_with_records.csv",
                                schedule_filepath="data/schedules_2025.csv")
    season.simulate_games()
    nfc_ranking, afc_ranking = season.rank()
    return nfc_ranking, afc_ranking

def simulate(num_iterations=1000):
    aggregator = get_aggregator_dict()
    num_times_run = 0
    # TODO: Fix Try Catch?
    for i in range(num_iterations):
        try:
            nfc_ranking, afc_ranking = simulate_single_season()
            aggregate_final_ranking(aggregator, nfc_ranking, afc_ranking)
            num_times_run += 1
        except NotImplementedError:
            print(f"Exception Occured During Ranking...Moving On...: {i}", end='\r')
    
    return aggregator, num_times_run

if __name__ == '__main__':
    aggregator, num_times_run = simulate()
    print(f"Num Iterations Run: {num_times_run}")

    for team, finishing_pos_count in aggregator.items():
        print(team, finishing_pos_count/num_times_run)

    for team, finishing_pos_count in aggregator.items():
        print(team, np.sum((finishing_pos_count/num_times_run)[:7]))




