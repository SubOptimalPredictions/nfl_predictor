import nflreadpy as nfl
import polars as pl
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import update_schedule

if __name__ == "__main__":
    update_schedule("data/schedules_2026.csv")
