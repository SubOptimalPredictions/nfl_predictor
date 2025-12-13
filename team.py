import numpy as np

class Team():
    def __init__(self, city : str, name : str, record : np.ndarray, conference : str, division : str):

        # Ensure Record is of the proper type and shape
        assert (type(record) == np.ndarray)
        assert (record.shape == (1, 3))

        self.city : str = city
        self.name : str = name
        self.record : np.ndarray = record
        self.conference : str = conference
        self.division : str = division

    def update_record(self, delta : np.ndarray):
        self.record += delta