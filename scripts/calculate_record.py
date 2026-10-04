import polars as pl

# write a function that loads schedules_2026.csv and calculates each team's win-loss-tie record, and adds it to teams.csv as 3 new columns


def calculate_records(schedule_path: str, teams_path: str, output_path: str):
    # Load the schedule data
    schedule = pl.read_csv(schedule_path)

    # Initialize a dictionary to hold team records
    records = {}

    # Iterate through each game in the schedule
    for row in schedule.iter_rows(named=True):
        home_team = row["home_team"]
        away_team = row["away_team"]
        home_score = row["home_score"]
        away_score = row["away_score"]

        # Initialize records if teams are not already in the dictionary
        if home_team not in records:
            records[home_team] = [0, 0, 0]  # wins, losses, ties
        if away_team not in records:
            records[away_team] = [0, 0, 0]  # wins, losses, ties

        # Update records based on game outcome
        if home_score is None:  # bye week or not played yet
            continue
        if home_score > away_score:
            records[home_team][0] += 1  # home win
            records[away_team][1] += 1  # away loss
        elif home_score < away_score:
            records[away_team][0] += 1  # away win
            records[home_team][1] += 1  # home loss
        else:
            records[home_team][2] += 1  # home tie
            records[away_team][2] += 1  # away tie

    # Load the teams data
    teams = pl.read_csv(teams_path)

    # Add new columns for wins, losses, and ties
    wins = []
    losses = []
    ties = []

    for team in teams["Abbreviation"]:
        if team in records:
            win, loss, tie = records[team]
        else:
            win, loss, tie = 0, 0, 0
        wins.append(win)
        losses.append(loss)
        ties.append(tie)

    teams = teams.with_columns(
        [pl.Series("Wins", wins), pl.Series("Losses", losses), pl.Series("Ties", ties)]
    )

    # Save the updated teams data to a new CSV file
    teams.write_csv(output_path)


if __name__ == "__main__":
    calculate_records(
        "data/schedules_2026.csv", "data/teams.csv", "data/teams_with_records.csv"
    )
