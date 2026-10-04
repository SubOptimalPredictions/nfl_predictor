import nflreadpy as nfl
import polars as pl
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import update_schedule
from calculate_record import calculate_records

if __name__ == "__main__":
    schedule_file_path = "data/schedules_2026.csv"
    update_schedule(schedule_file_path)
    calculate_records(
        schedule_file_path, "data/teams.csv", "data/teams_with_records.csv"
    )
