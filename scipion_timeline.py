
class ScipionTimeline:
    from csv import DictReader
    from datetime import timedelta, datetime
    import matplotlib.dates as mdates

    def __init__(self, file):
        self.file = file
        self.timeline = {}  # {1: [(n, (s, d))...]} == y_value: [(protocol, (start, length))...]
        self.__parse()

    def __parse(self):
        def fix_time(t):
            return self.datetime.combine(self.datetime.now().date(), t.time())
        tmp = []
        # load data to dictionary
        keys = ['protocol_name', 'protocol_start', 'protocol_end']
        with open(self.file) as f:
            reader = self.DictReader(f, delimiter=';')
            for line in reader:
                # we need to hack the time, because the rest of the timeline uses only time
                # which automatically sets day to the day of processing
                d = {'name': line['protocol_name'],
                     's': fix_time(self.datetime.strptime(line['protocol_start'], '%Y-%m-%d %H:%M:%S,%f')),
                     'e': fix_time(self.datetime.strptime(line['protocol_end'], '%Y-%m-%d %H:%M:%S,%f'))}
                tmp.append(d)
        tmp = self.__remove_duplicates(tmp)
        self.__create_timeline(tmp)

    def __create_timeline(self, data):
        end_times = {}
        # find the first 'empty slot'
        for d in sorted(data, key=lambda x: x['s']):
            s = d['s']
            e = d['e']
            n = d['name']
            sn = self.mdates.date2num(s)
            en = self.mdates.date2num(e)
            l = en - sn
            for i in range(0, 10000):
                # this timeslot is currently not occupied
                if end_times.get(i) is None or end_times[i] <= s:
                    end_times[i] = e + self.timedelta(seconds=10)
                    self.timeline.setdefault(i, []).append((n, (sn, l)))
                    break

    @staticmethod
    def __remove_duplicates(data):
        result = []
        seen = set()
        for d in data:
            t = tuple(sorted(d.items()))
            if t not in seen:
                seen.add(t)
                result.append(d)
        return result
