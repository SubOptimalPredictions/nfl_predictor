from season import Season
from team import Team
import numpy as np
from tqdm import tqdm
import math
import multiprocessing
import concurrent.futures
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
    season = Season.load_season(
        teams_file_path="data/teams_with_records.csv",
        schedule_filepath="data/schedules_2025.csv",
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


if __name__ == "__main__":
    # aggregator, num_times_run = simulate()
    start_time = time.time()
    aggregator, num_times_run = parallel_simulatation(
        num_iterations=1000, batch_size=100
    )
    print(f"Elapsed Time: {time.time() - start_time:.2f} seconds")
    print(f"\nNum Iterations Run: {num_times_run}")
    # for team, finishing_pos_count in aggregator.items():
    #     print(team, finishing_pos_count / num_times_run)

    # for team, finishing_pos_count in aggregator.items():
    #     print(team, np.sum((finishing_pos_count / num_times_run)[:7]))
