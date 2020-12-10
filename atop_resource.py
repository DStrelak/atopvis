class AtopResource:
    def __init__(self, name, unit, data, data_opt=None, data_opt_unit=None, desc=None):
        self.name = name
        self.unit = unit
        self.data = data
        self.data_opt = data_opt
        self.data_opt_unit = data_opt_unit
        self.desc = desc

    def __lt__(self, other):
        return self.name < other.name
