"""Season container module.

The :class:`Season` class is a placeholder for season-level
functionality (standings, schedule, etc.). It can be extended as the
project grows.
"""

from team import Team
from game import Game
import numpy as np
import time


class Season:
    """Representation of an NFL season.

    Currently a thin wrapper; intended to aggregate weeks, teams, and
    provide season-wide operations (scheduling, standings calculation,
    etc.).
    """

    def __init__(self, list_of_games, team_name_to_team):

        self.list_of_games : list[Game] = list_of_games
        self.team_name_to_team : dict[str, Team] = team_name_to_team

    def add_team(self, name, conference, division, record=np.array([0, 0, 0])):
        team = Team(name=name, record=record, conference=conference, division=division)

        # Map team name to team object
        self.team_name_to_team[name] = team

    def simulate_games(self) -> None:
        """Simulate every game in the week in order.

        The method asserts there are a reasonable number of games
        scheduled (a sanity check) and then calls ``simulate`` on each
        :class:`Game`.
        """

        # TODO: Check actual minimum number of games
        assert (len(self.list_of_games) > 13), "Less than Minimum Number of games per week" 
        for game in self.list_of_games:
            game.simulate()

    def rank(self):
        nfc_teams, afc_teams = self.split_teams_into_conferences()

        nfc_north, nfc_south, nfc_east, nfc_west = self.split_conferences_into_divison(nfc_teams)
        afc_north, afc_south, afc_east, afc_west = self.split_conferences_into_divison(afc_teams)

        # Print NFC Division
        print("NFC North: ", [t.name for t in nfc_north])
        print("NFC South: ", [t.name for t in nfc_south])
        print("NFC East: ", [t.name for t in nfc_east])
        print("NFC West: ", [t.name for t in nfc_west])

        # Print AFC Division
        print("AFC North: ", [t.name for t in afc_north])
        print("AFC South: ", [t.name for t in afc_south])
        print("AFC East: ", [t.name for t in afc_east])
        print("AFC West: ", [t.name for t in afc_west])

        

    def split_teams_into_conferences(self):
        nfc_teams = []
        afc_teams = []

        for _, team in self.team_name_to_team.items():
            team_conference = team.conference.lower() 
            if team_conference == 'nfc':
                nfc_teams.append(team)
            elif team_conference == 'afc':
                afc_teams.append(team)
            else:
                raise NotImplementedError("Team has incorrect conference?")

        return nfc_teams, afc_teams

    def split_conferences_into_divison(self, conference_teams):
        north_teams = []
        south_teams = [] 
        east_teams = []
        west_teams = []

        for team in conference_teams:
            team_division = team.division.lower()
            if team_division == 'north':
                north_teams.append(team)
            elif team_division == 'south':
                south_teams.append(team)
            elif team_division == 'east':
                east_teams.append(team)
            elif team_division == 'west':
                west_teams.append(team)
            else:
                raise NotImplementedError("Team has incorrect division?")
        return north_teams, south_teams, east_teams, west_teams


    @staticmethod
    def load_season(
        teams_file_path: str,
        schedule_filepath: str
    ):
        teams = Team.load_teams_from_csv(teams_file_path)
        games = Game.load_games_from_csv(schedule_filepath, teams)

        season = Season(list_of_games=games, team_name_to_team=teams)
        return season

    def __repr__(self) -> str:
        output = ""
        for game in self.list_of_games:
            output += game.__repr__()
            output += "\n"
        for team in self.team_name_to_team:
            output += f"Team Name: {team}, {self.team_name_to_team[team].__repr__()}"
            output += "\n"
        return output
    
if __name__ == "__main__":
    season = Season.load_season(teams_file_path="data/teams_with_records.csv",
                                schedule_filepath="data/schedules_2025.csv")
    
    for team_name, team in season.team_name_to_team.items():
        print(team_name, team.record)

    st = time.time()
    season.simulate_games()
    et = time.time()
    print(f"Time to Simulate Games: {et - st}")

    for team_name, team in season.team_name_to_team.items():
        print(team_name, team.record[0])
    
    season.rank()



