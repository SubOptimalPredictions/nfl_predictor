import polars as pl
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import gemini_probability_batch, init_gemini_client
from team import Team


def precompute_gemini_predictions(
    schedule_path: str, teams_path: str, output_path: str
):
    """
    Load the schedule, identify games without scores or moneylines,
    batch predict their probabilities using Gemini, and add new columns
    for gemini_away_win_prob and gemini_home_win_prob.
    """
    # Load the schedule data
    schedule = pl.read_csv(schedule_path)

    # Load teams to get full names
    teams = Team.load_teams_from_csv(teams_path)

    # Collect games that need Gemini predictions
    games_needing_prediction = []
    game_indices = []

    for idx, row in enumerate(schedule.iter_rows(named=True)):
        # Skip games that already have scores
        if row["away_score"] is not None and row["home_score"] is not None:
            continue
        # Skip games that have moneylines
        if row["away_moneyline"] is not None and row["home_moneyline"] is not None:
            continue

        # Need Gemini prediction for this game
        away_abbr = row["away_team"]
        home_abbr = row["home_team"]

        # Get full team names
        away_team = teams[away_abbr]
        home_team = teams[home_abbr]

        games_needing_prediction.append((away_team.name, home_team.name))
        game_indices.append(idx)

    print(f"Found {len(games_needing_prediction)} games needing Gemini predictions")

    # Initialize columns with None
    gemini_away_probs = [None] * len(schedule)
    gemini_home_probs = [None] * len(schedule)

    # Batch predict if there are games to predict
    if games_needing_prediction:
        print("Calling Gemini API for batch predictions...")
        client = init_gemini_client()
        batch_predictions = gemini_probability_batch(client, games_needing_prediction)

        # Fill in the predictions
        for idx, matchup in zip(game_indices, games_needing_prediction):
            if matchup in batch_predictions:
                probs = batch_predictions[matchup]
                gemini_away_probs[idx] = float(probs[0])
                gemini_home_probs[idx] = float(probs[1])
                print(f"  {matchup[0]} @ {matchup[1]}: {probs[0]:.3f} / {probs[1]:.3f}")
            else:
                print(f"  Warning: No prediction for {matchup[0]} @ {matchup[1]}")

    # Add new columns to the schedule
    schedule = schedule.with_columns(
        [
            pl.Series("gemini_away_win_prob", gemini_away_probs),
            pl.Series("gemini_home_win_prob", gemini_home_probs),
        ]
    )

    # Save the updated schedule
    schedule.write_csv(output_path)
    print(f"\nUpdated schedule saved to {output_path}")


if __name__ == "__main__":
    precompute_gemini_predictions(
        "data/schedules_2025.csv",
        "data/teams_with_records.csv",
        "data/schedules_2025.csv",
    )
