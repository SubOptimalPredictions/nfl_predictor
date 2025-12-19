import numpy as np
from google import genai
import dotenv
import os
from pydantic import BaseModel
import nflreadpy as nfl
import polars as pl
import pandas as pd

def _single_moneyline_to_probability(team_moneyline: int):
    if team_moneyline < 0:
        return abs(team_moneyline) / (abs(team_moneyline) + 100)
    else:
        return 100 / (abs(team_moneyline) + 100)

def moneyline_to_probability(
    away_team_moneyline: int, home_team_moneyline: int
) -> np.ndarray:
    """
    returns: [away_team_win_prob, home_team_win_prob] probabilities are between [0, 1]
    """
    away_team_win_prob_vig = _single_moneyline_to_probability(away_team_moneyline)
    home_team_win_prob_vig = _single_moneyline_to_probability(home_team_moneyline)

    away_team_win_prob = away_team_win_prob_vig / (away_team_win_prob_vig + home_team_win_prob_vig)
    home_team_win_prob = home_team_win_prob_vig / (away_team_win_prob_vig + home_team_win_prob_vig)

    result = np.array([away_team_win_prob, home_team_win_prob])

    assert np.isclose(np.sum(result), 1), "Probabilities are not normalized"
    return result


def total_record_to_pct(records):
    return record_to_pct(np.sum(records, axis=0, keepdims=True))


def record_to_pct(record):
    record = record[0]
    return (record[0] + 0.5 * record[2]) / np.sum(record)


GEMINI_MODEL_NAME = "gemini-2.5-flash"


class WinProbability(BaseModel):
    away_team_win_prob: float
    home_team_win_prob: float


class GameMatchup(BaseModel):
    away_team: str
    home_team: str
    away_team_win_prob: float
    home_team_win_prob: float


class BatchWinProbability(BaseModel):
    predictions: list[GameMatchup]


def init_gemini_client():
    dotenv.load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return client


def gemini_probability(client: genai.Client, away_team, home_team) -> np.ndarray:
    prompt = f"""Given that the {away_team} are playing the {home_team}, 
    what is the probability that each team will win? 
    Provide two probabilities between 0 and 1 that sum to 1."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": WinProbability.model_json_schema(),
            "system_instruction": "You are an expert football analyst. For the 2025 NFL season, provide insights.",
        },
    )

    win_prob = WinProbability.model_validate_json(response.text)
    return np.array([win_prob.away_team_win_prob, win_prob.home_team_win_prob])


def gemini_probability_batch(
    client: genai.Client, matchups: list[tuple[str, str]]
) -> dict[tuple[str, str], np.ndarray]:
    """Batch predict win probabilities for multiple games.

    Args:
        client: Gemini API client
        matchups: List of (away_team, home_team) tuples

    Returns:
        Dictionary mapping (away_team, home_team) to probability arrays
    """
    if not matchups:
        return {}

    matchups_str = "\n".join([f"- {away} @ {home}" for away, home in matchups])

    prompt = f"""For the following NFL matchups, predict the win probability for each team.
    Provide probabilities between 0 and 1 that sum to 1 for each game.
    
    Matchups:
    {matchups_str}
    """

    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": BatchWinProbability.model_json_schema(),
            "system_instruction": "You are an expert football analyst. For the 2025 NFL season, provide insights.",
        },
    )

    batch_result = BatchWinProbability.model_validate_json(response.text)

    # Create a dictionary mapping matchups to probability arrays
    result_dict = {}
    for pred in batch_result.predictions:
        key = (pred.away_team, pred.home_team)
        result_dict[key] = np.array([pred.away_team_win_prob, pred.home_team_win_prob])

    return result_dict


def update_schedule(
    schedule_filepath: str,
    columns_to_preserve: list[str] = [
        "game_id",
        "gemini_away_win_prob",
        "gemini_home_win_prob",
    ],
):
    pbp = nfl.load_pbp()
    schedule_new: pl.DataFrame = nfl.load_schedules([2025])
    try:
        schedule_existing = pl.read_csv(schedule_filepath)

        custom_cols = schedule_existing.select(columns_to_preserve)

        # Merge: keep all new data and join the custom columns
        schedule = schedule_new.join(custom_cols, on="game_id", how="left")
        schedule.write_csv("data/schedules_2025.csv")
    except FileNotFoundError:
        schedule_new.write_csv("data/schedules_2025.csv")

def generate_team_with_weekly_records_table():
    schedules = nfl.load_schedules([2025]).to_pandas()

    # Create a DataFrame to store the weekly records for each team
    team_weekly_records = pd.DataFrame(columns=["team", "week", "games_played", "wins", "losses", "ties"])

    for idx, row in schedules.iterrows():

        away_team_record = pd.DataFrame({
            "team": [row['away_team']],
            "week": [row['week']],
            "games_played": [1],
            "wins": [1 if row['away_score'] > row['home_score'] else 0],
            "losses": [1 if row['away_score'] < row['home_score'] else 0],
            "ties": [1 if row['away_score'] == row['home_score'] else 0],
        })
        team_weekly_records = pd.concat([team_weekly_records, away_team_record], ignore_index=True)

        home_team_record = pd.DataFrame({
            "team": [row['home_team']],
            "week": [row['week']],
            "games_played": [1],
            "wins": [1 if row['home_score'] > row['away_score'] else 0],
            "losses": [1 if row['home_score'] < row['away_score'] else 0],
            "ties": [1 if row['home_score'] == row['away_score'] else 0],
        })

        team_weekly_records = pd.concat([team_weekly_records, home_team_record], ignore_index=True)

    return team_weekly_records

if __name__ == "__main__":
    dotenv.load_dotenv()
    print(moneyline_to_probability(410, -550))

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    test_matchups = [
        ("San Francisco 49ers", "Kansas City Chiefs"),
        ("Buffalo Bills", "Miami Dolphins"),
    ]
    probs = gemini_probability_batch(client, test_matchups)
    for matchup, prob in probs.items():
        print(f"{matchup}: {prob}")
