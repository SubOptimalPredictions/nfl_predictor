import nflreadpy as nfl
import polars as pl

# Load current season play-by-play data
pbp = nfl.load_pbp()
#
schedule: pl.DataFrame = nfl.load_schedules([2025])
print(schedule.head())
# save as pandas df as csv file
schedule.write_csv("data/schedules_2025.csv")
