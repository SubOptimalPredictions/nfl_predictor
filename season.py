"""Season container module.

The :class:`Season` class is a placeholder for season-level
functionality (standings, schedule, etc.). It can be extended as the
project grows.
"""

from team import Team, DivisionTeamWrapper, ConferenceTeamWrapper
from game import Game
import numpy as np
import time
from utils import total_record_to_pct
from operator import itemgetter

def get_strength_of_victory(team: Team, team_name_to_team):
    losing_abbvrs = [loser for loser, record in list(team.head_to_head_record.items()) if record[0, 0] > 0]
    losing_teams = itemgetter(*losing_abbvrs)(team_name_to_team)
    loser_records = [np.concatenate(list(opp.head_to_head_record.values())) for opp in losing_teams]
    return total_record_to_pct(np.concatenate(loser_records))

def get_strength_of_schedule(team: Team, team_name_to_team):
    opponents = itemgetter(*list(team.head_to_head_record.keys()))(team_name_to_team)
    opponent_records = [np.concatenate(list(opp.head_to_head_record.values())) for opp in opponents]
    return total_record_to_pct(np.concatenate(opponent_records))


class Season:
    """Representation of an NFL season.

    Currently a thin wrapper; intended to aggregate weeks, teams, and
    provide season-wide operations (scheduling, standings calculation,
    etc.).
    """

    def __init__(self, list_of_games, team_name_to_team):

        self.list_of_games : list[Game] = list_of_games
        # team abbvr to team
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
        for _, team in self.team_name_to_team.items():
            team.strength_of_schedule = get_strength_of_schedule(team, self.team_name_to_team)
            team.strength_of_victory = get_strength_of_victory(team, self.team_name_to_team)

    def rank(self):
        nfc_teams, afc_teams = self.split_teams_into_conferences()

        nfc_north, nfc_south, nfc_east, nfc_west = self.split_conferences_into_divison(nfc_teams)
        afc_north, afc_south, afc_east, afc_west = self.split_conferences_into_divison(afc_teams)

        nfc_north_winner, nfc_north_remaining = self.rank_division(nfc_north)
        nfc_south_winner, nfc_south_remaining = self.rank_division(nfc_south)
        nfc_east_winner, nfc_east_remaining = self.rank_division(nfc_east)
        nfc_west_winner, nfc_west_remaining = self.rank_division(nfc_west)

        afc_north_winner, afc_north_remaining = self.rank_division(afc_north)
        afc_south_winner, afc_south_remaining = self.rank_division(afc_south)
        afc_east_winner, afc_east_remaining = self.rank_division(afc_east)
        afc_west_winner, afc_west_remaining = self.rank_division(afc_west)

        nfc_division_winners_ranked = self.rank_conference_teams([nfc_north_winner, nfc_south_winner, nfc_east_winner, nfc_west_winner])
        afc_division_winners_ranked = self.rank_conference_teams([afc_north_winner, afc_south_winner, afc_east_winner, afc_west_winner])

        nfc_remaining_ranked = self.rank_conference_teams(nfc_north_remaining + nfc_south_remaining + nfc_east_remaining + nfc_west_remaining)
        afc_remaining_ranked = self.rank_conference_teams(afc_north_remaining + afc_south_remaining + afc_east_remaining + afc_west_remaining)

        nfc_ranking = nfc_division_winners_ranked + nfc_remaining_ranked
        afc_ranking = afc_division_winners_ranked + afc_remaining_ranked

        return nfc_ranking, afc_ranking
    
    def print_standings(self, nfc_ranking, afc_ranking):
        print("NFC:")
        for team in nfc_ranking:
            print(team)

        print("-----\n")
        print("AFC:")
        for team in afc_ranking:
            print(team)

    def rank_division(self, division):
        division_wrapped_teams = [DivisionTeamWrapper(t) for t in division]
        division_wrapped_teams.sort(reverse=True)
        ranked_divison_results = [t.team for t in division_wrapped_teams]
        return ranked_divison_results[0], ranked_divison_results[1:]
    
    def rank_conference_teams(self, conference_teams: list[Team]):
        conference_wrapped_teams = [ConferenceTeamWrapper(t) for t in conference_teams]
        conference_wrapped_teams.sort(reverse=True)
        ranked_conference_results = [t.team for t in conference_wrapped_teams]
        return ranked_conference_results

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



