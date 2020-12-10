class AtopProcess:
    header = 'res    pid command  util |   pid command  util |   pid command  util'

    def __init__(self, time, disk, cpu, memory):
        self.time = time
        self.disk = disk
        self.cpu = cpu
        self.memory = memory

    def __lt__(self, other):
        return self.time < other.time

    def __str__(self):
        return '\n'.join([self.header,
                          'dsk' + self.disk,
                          'cpu' + self.cpu,
                          'ram' + self.memory])

    def __repr__(self):
        return str(self)
