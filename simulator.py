from season import Season
from team import Team
from game import Game
import numpy as np
from tqdm import tqdm
import math
import multiprocessing
import concurrent.futures
import time
import utils
import copy


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
    season = Season.load_season(
        teams_file_path="data/teams_with_records.csv",
        schedule_filepath="data/schedules_2026.csv",
    )
    season.simulate_games()
    nfc_ranking, afc_ranking = season.rank()
    return nfc_ranking, afc_ranking


def simulate(num_iterations=1000):
    aggregator = get_aggregator_dict()
    num_times_run = 0
    # TODO: Fix Try Catch?
    # print(f"Simulating {num_iterations} seasons...")
    for i in range(num_iterations):
        try:
            nfc_ranking, afc_ranking = simulate_single_season()
            aggregate_final_ranking(aggregator, nfc_ranking, afc_ranking)
            num_times_run += 1
        except NotImplementedError:
            print(f"Exception Occured During Ranking...Moving On...: {i}", end="\r")

    return aggregator, num_times_run


def simulate_silent(num_iterations=1000):
    """Version of simulate without print statements for parallel execution"""
    aggregator = get_aggregator_dict()
    num_times_run = 0

    for i in range(num_iterations):
        try:
            nfc_ranking, afc_ranking = simulate_single_season()
            aggregate_final_ranking(aggregator, nfc_ranking, afc_ranking)
            num_times_run += 1
        except NotImplementedError:
            pass  # Silently skip errors

    return aggregator, num_times_run


def aggregate_multiple_results(results):
    aggregator = get_aggregator_dict()
    num_times_run = 0

    for thread_aggregator, thread_num_times_run in results:
        for team in aggregator:
            aggregator[team] += thread_aggregator[team]
        num_times_run += thread_num_times_run
    return aggregator, num_times_run


def orig_parallel_simulatation(num_iterations=100, batch_size=10):
    num_batches = math.ceil(num_iterations / batch_size)
    print(f"Using {num_batches} processes each with batch size: {batch_size}")

    rankings = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = [executor.submit(simulate, batch_size) for _ in range(num_batches)]

        for f in concurrent.futures.as_completed(results):
            rankings.append(f.result())

    return aggregate_multiple_results(rankings)


def parallel_simulatation(num_iterations=100, batch_size=10, num_workers=None):
    utils.update_schedule("data/schedules_2026.csv")
    num_batches = math.ceil(num_iterations / batch_size)

    if num_workers is None:
        num_workers = min(multiprocessing.cpu_count(), num_batches)

    print(
        f"Using {num_batches} batches with {num_workers} workers, batch size: {batch_size}"
    )

    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(processes=num_workers) as pool:
        tasks = [batch_size] * num_batches
        rankings = pool.map(simulate, tasks)

    print("All jobs completed.")
    return aggregate_multiple_results(rankings)


class Simulator:
    def __init__(
        self,
        teams_file_path: str = "data/teams_with_records.csv",
        schedule_filepath: str = "data/schedules_2026.csv",
    ):
        self.base_season = Season.load_season(
            teams_file_path=teams_file_path,
            schedule_filepath=schedule_filepath,
        )

    def modify_game_probabilities(self, game: Game, updated_probabilities: np.ndarray):
        assert np.isclose(np.sum(updated_probabilities), 1), (
            "Updated Probabilities are invalid"
        )
        game.probabilities = updated_probabilities

    def simulate_single_season(self):
        season = copy.deepcopy(self.base_season)
        season.simulate_games()
        nfc_ranking, afc_ranking = season.rank()
        return nfc_ranking, afc_ranking

    def simulate(self, num_iterations=1000):
        aggregator = get_aggregator_dict()
        num_times_run = 0
        # TODO: Fix Try Catch?
        # print(f"Simulating {num_iterations} seasons...")
        for i in tqdm(range(num_iterations)):
            try:
                nfc_ranking, afc_ranking = self.simulate_single_season()
                aggregate_final_ranking(aggregator, nfc_ranking, afc_ranking)
                num_times_run += 1
            except NotImplementedError:
                print(f"Exception Occured During Ranking...Moving On...: {i}", end="\r")

        return aggregator, num_times_run

    @staticmethod
    def format_results(aggregator, num_times_run):
        aggregator = copy.deepcopy(aggregator)
        for team in aggregator:
            aggregator[team] = aggregator[team] / num_times_run
        return aggregator

    """ START: TO MOVE ELSEWHERE """

    @staticmethod
    def calculate_playoff_probability(finishing_pos_count, num_times_run):
        """Calculate probability of making playoffs (top 7)"""
        # print(finishing_pos_count)
        if num_times_run == 0:
            return 0.0
        return np.sum(finishing_pos_count[:7]) / num_times_run

    @staticmethod
    def calculate_division_winner_probability(finishing_pos_count, num_times_run):
        """Calculate probability of winning division (top 4)"""
        if num_times_run == 0:
            return 0.0
        return np.sum(finishing_pos_count[:4]) / num_times_run

    @staticmethod
    def calculate_conference_winner_probability(finishing_pos_count, num_times_run):
        """Calculate probability of winning division (top 4)"""
        if num_times_run == 0:
            return 0.0
        return np.sum(finishing_pos_count[:1]) / num_times_run

    """ END: TO MOVE ELSEWHERE """

    @staticmethod
    def compute_full_results_table(aggregator, num_times_run):
        playoff_probabilities = {}
        for team in aggregator:
            playoff_probabilities[team] = {
                "playoffs": Simulator.calculate_playoff_probability(
                    aggregator[team], num_times_run
                ),
                "division_winner": Simulator.calculate_division_winner_probability(
                    aggregator[team], num_times_run
                ),
                "conference_winner": Simulator.calculate_conference_winner_probability(
                    aggregator[team], num_times_run
                ),
            }
        return playoff_probabilities


def compute_win_loss_next_game_playoff_probabilities():
    # TODO: Fix the situation when there are no next unplayed games
    playoff_prob_by_team_after_next_game_outcome = {}
    sim = Simulator()
    season = sim.base_season
    teams = season.team_name_to_team

    for name, team in teams.items():
        sim = Simulator()
        next_game = sim.base_season.get_team_next_game(name)
        playoff_prob_by_team_after_next_game_outcome[name] = np.array([0.0, 0.0])
        print(f"Team: {name}")
        print(next_game)
        # Away Win
        new_probability = np.array([1.0, 0.0])
        sim.modify_game_probabilities(next_game, new_probability)
        aggregator, num_times_run = sim.simulate()
        standing_probabilities = Simulator.format_results(aggregator, num_times_run)
        playoff_prob = np.sum(standing_probabilities[name][:7])
        idx = 0 if next_game.away_team.abbreviation == name else 1
        playoff_prob_by_team_after_next_game_outcome[name][idx] = playoff_prob

        # Home Win
        new_probability = np.array([0.0, 1.0])
        sim.modify_game_probabilities(next_game, new_probability)
        aggregator, num_times_run = sim.simulate()
        standing_probabilities = Simulator.format_results(aggregator, num_times_run)
        playoff_prob = np.sum(standing_probabilities[name][:7])
        idx = 0 if next_game.home_team.abbreviation == name else 1
        playoff_prob_by_team_after_next_game_outcome[name][idx] = playoff_prob

    return playoff_prob_by_team_after_next_game_outcome


if __name__ == "__main__":
    playoff_prob_by_team_after_next_game_outcome = (
        compute_win_loss_next_game_playoff_probabilities()
    )
    for team in playoff_prob_by_team_after_next_game_outcome:
        print(team, playoff_prob_by_team_after_next_game_outcome[team])
    exit()
    # aggregator, num_times_run = simulate()
    start_time = time.time()
    # aggregator, num_times_run = parallel_simulatation(
    #     num_iterations=1000, batch_size=100
    # )
    sim = Simulator()
    # sim.modify_game_probabilities("GB-CHI", np.array([0.0, 1.0]))
    # nfc, afc = sim.simulate_single_season()
    # print(nfc)
    aggregator, num_times_run = sim.simulate(num_iterations=10)
    # print(aggregator)
    output = Simulator.compute_full_results_table(aggregator, num_times_run)
    print(output)
    # aggregator, num_times_run = simulate()

    print(f"Elapsed Time: {time.time() - start_time:.2f} seconds")
    print(f"\nNum Iterations Run: {num_times_run}")
    print(aggregator)
    for team, finishing_pos_count in aggregator.items():
        print(team, finishing_pos_count / num_times_run)

    for team, finishing_pos_count in aggregator.items():
        print(team, np.sum((finishing_pos_count / num_times_run)[:7]))
