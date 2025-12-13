"""Week container for a collection of :class:`Game` objects.

This module holds the :class:`Week` class which aggregates games for a
given week and can simulate them in sequence.
"""

from game import Game


class Week:
    """Collection of games for a single NFL week.

    Attributes:
        list_of_games (list[Game]): Games scheduled for the week.
    """

    def __init__(self):
        self.list_of_games : list[Game] = []

    def add_game(self, game : Game) -> None:
        """Append a :class:`Game` to the week's schedule.

        Args:
            game: The game to add.
        """

        self.list_of_games.append(game)

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