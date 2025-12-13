"""Team representation and record utilities.

This module provides the :class:`Team` class which stores a team's
identity and its season record as a numpy array with the layout
[wins, losses, ties].
"""

import numpy as np


class Team:
    """Model of an NFL team.

    Attributes:
        name (str): Team name.
        record (np.ndarray): Shape (1, 3) array for [wins, losses, ties].
        conference (str): Conference name.
        division (str): Division name.
    """

    def __init__(self, name : str, record : np.ndarray, conference : str, division : str):

        # Ensure Record is of the proper type and shape
        assert (type(record) == np.ndarray)
        assert (record.shape == (1, 3))

        self.name : str = name
        self.record : np.ndarray = record
        self.conference : str = conference
        self.division : str = division

    def update_record(self, delta: np.ndarray) -> None:
        """Apply an increment to the team's record.

        Args:
            delta: A numpy array of shape (1, 3) representing the
                increments to add to `[wins, losses, ties]`.

        The operation mutates ``self.record`` in place.
        """

        self.record += delta