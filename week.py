from game import Game

class Week():
    def __init__(self):
        self.list_of_games : list[Game] = []

    def add_game(self, game : Game):
        self.list_of_games.append(game)

    def simulate_games(self):
        assert (len(self.list_of_games) > 13) # Check the actual minimum number of games
        for game in self.list_of_games:
            game.simulate()