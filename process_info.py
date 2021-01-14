import subprocess
import pandas as pd
import logging
import re
import uuid
from atop_constants import *

# since Python 3.6, dicts keep insertion order
assert sys.version_info >= (3, 6)

LOGGER = logging.getLogger()
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def __run(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    log = []
    while True:
        line = p.stdout.readline()
        try:
            output = line.decode("utf-8").rstrip('\n')
            if output == '' and p.poll() is not None:
                break
            if '' == output:
                continue
            log.append(output)
        except UnicodeError as e:
            LOGGER.error(f'Error parsing line. Line will be skipped: {line}\nReason: {e}')
            continue

    return 0 == p.poll(), log


class ProcessInfo:
    __ids = {}

    @staticmethod
    def create_id(pid, start, time):
        v = ProcessInfo.__ids.setdefault(pid, {})
        # sometimes there might be discrepancy between the current time and the start time, example:
        #                V                                                             V
        # PRG david 1606905905 2020/12/02 11:45:05 1 4066 (atopgpud) S 0 0 996 1 0 1606905906 () 1 0 1 0 0 0 0 0 0 0 0 n 0 0 -
        t = start
        if start > time:
            LOGGER.warning(f'start time {start} for pid {pid} is later than the current time {time}')
            t = time
        v[t] = uuid.uuid4()
        # store start times sorted from the newest (biggest) to smallest
        # keep insertion order
        ProcessInfo.__ids[pid] = dict(sorted(v.items(), key=lambda item: item[0], reverse=True))
        return v[t]

    @staticmethod
    def get_id(pid, time):
        start_times = ProcessInfo.__ids.get(pid, {})
        if not start_times:
            return None
        # find the most recent start time before the current time
        start = next(t for t in start_times.keys() if time >= t)
        return ProcessInfo.__ids[pid][start]

    def __init__(self, pid, name, command, start, tgid):
        self.pid = pid
        self.name = name
        self.command = command
        self.start = start  # epoch
        self.end = None  # epoch
        self.records = {}
        self.tgid = tgid

    def update(self, time, data: dict):
        if time not in self.records:
            self.records[time] = data
        else:
            self.records[time].update(data)

    def set_end(self, end):
        self.end = end

    def get_end(self):
        if self.end:
            return self.end
        # assume process finished after last record
        return max(self.records.keys()) + 1

    def __repr__(self):
        return str(vars(self))


def get_tokens(t, tokens, fields, with_brackets):
    res = {}
    keys = list(fields.keys())
    for i in t:
        index = keys.index(i)
        val = tokens[index]
        if t in with_brackets:
            val = val.replace('(', '').replace(')', '')
        res[i] = fields[i](val)  # cast to proper type
    return res


def parse_general(file, label):
    success, log = __run(f'atop -r {file} -P {label}')
    if not success:
        LOGGER.critical(f'Could not obtain process data for file {file} and label {label}')
        exit(-1)
    # split on space, except when it's between brackets
    pattern = re.compile(r'\s+(?=[^()]*(?:\(|$))')
    first_sep_found = False
    for line in log:
        # data till first separator contain data since boot (which we don't want)
        if not first_sep_found:
            if line.startswith(SEP):
                first_sep_found = True
            continue
        if line.startswith(SEP) or line.startswith(RESET):
            continue
        if not line.startswith(label):
            LOGGER.error(f'Unexpected line format in file {file}: label \'{label}\' expected '
                         f'as a first token, instead got \'{line}\'')
            continue
        tokens = pattern.split(line)
        yield tokens


def parse_prg(file):
    processes = {}
    for tokens in parse_general(file, 'PRG'):
        t = get_tokens(['pid', 'start', 'epoch', 'name', 'command', 'tgid', 'state'], tokens, PRG_FIELDS, PRG_FIELDS_BETWEEN_BRACKETS)
        puuid = ProcessInfo.get_id(t['pid'], t['epoch']) or ProcessInfo.create_id(t['pid'], t['start'], t['epoch'])
        process = processes.setdefault(puuid, ProcessInfo(t['pid'], t['name'], t['command'], t['start'], t['tgid']))
        if 'E' in t['state']:
            process.set_end(t['epoch'])
    LOGGER.debug(f'Detected {len(processes)} processes')
    return processes


def update_general(file, processes, label, fields, all_fields, fields_between_brackets):
    def kv(k):
        return k, data[k]
    fields_to_extract = fields + ['epoch', 'pid']
    for tokens in parse_general(file, label):
        data = get_tokens(fields_to_extract, tokens, all_fields, fields_between_brackets)
        pid = data['pid']
        epoch = data['epoch']
        processes.get(ProcessInfo.get_id(pid, epoch)).update(epoch, dict(map(kv, fields)))


def update_prc(file, processes):
    LOGGER.debug('update prc started')
    update_general(file, processes, 'PRC', ['clock-ticks', 'cpu-usr', 'cpu-sys', 'sleep-avg'],
                   PRC_FIELDS, PRC_FIELDS_BETWEEN_BRACKETS)
    LOGGER.debug('update prc done')


def update_prm(file, processes):
    LOGGER.debug('update prm done')
    update_general(file, processes, 'PRM', ['mem-virt-kbytes', 'mem-res-kbytes',
                                            'mem-virt-growth-kbytes', 'mem-res-growth-kbytes',
                                            'page-faults-minor', 'page-faults-major',
                                            'data-size-kbytes', 'swap-kbytes'],
                   PRM_FIELDS, PRM_FIELDS_BETWEEN_BRACKETS)
    LOGGER.debug('update prm done')


def update_pre(file, processes):
    update_general(file, processes, 'PRE', ['busy', 'mem-busy', 'mem-util-kb'],
                   PRE_FIELDS, PRE_FIELDS_BETWEEN_BRACKETS)


def update_prd(file, processes):
    update_general(file, processes, 'PRD', ['read-sectors', 'write-sectors', 'write-cancelled'],
                   PRD_FIELDS, PRD_FIELDS_BETWEEN_BRACKETS)


def get_statistics(processes, dest):
    import numpy as np
    def store(d, metric):
        if type(d) is pd.DataFrame or type(d) is pd.Series:
            for field, value in d.items():
                setattr(v, f'{field}-{metric}', value)
        else:
            setattr(v, f'{metric}', d)

    LOGGER.debug(f'Computing statistics')
    for k, v in processes.items():
        data = v.records
        if data:  # skip empty data
            df = pd.DataFrame.from_dict(data, orient='index')
            # CPU part
            store(df[['cpu-usr', 'cpu-sys']].values.sum(), 'cpu-sum')
            store(df[['cpu-usr', 'cpu-sys']].count(), 'intervals')
            store(df[['cpu-usr', 'cpu-sys', 'sleep-avg']].sum(), 'sum')

            # RAM part
            store(df[['mem-virt-kbytes', 'mem-res-kbytes', 'swap-kbytes', 'data-size-kbytes',
                      'page-faults-minor', 'page-faults-major']].max(), 'max')
            store(df[['mem-virt-kbytes', 'mem-res-kbytes', 'swap-kbytes', 'data-size-kbytes',
                      'page-faults-minor', 'page-faults-major']].sum(), 'sum')

            store(df[['mem-virt-growth-kbytes', 'mem-res-growth-kbytes']].abs().sum(), '(de)allocation-sum')
            store(df[['mem-virt-growth-kbytes', 'mem-res-growth-kbytes']].abs().mean(), '(de)allocation-mean')
            tmp = df[['mem-virt-growth-kbytes', 'mem-res-growth-kbytes']]
            store(tmp[(tmp['mem-virt-growth-kbytes'] > 0)
                      | (tmp['mem-res-growth-kbytes'] > 0)].sum(), 'allocation-sum')
            store(tmp[(tmp['mem-virt-growth-kbytes'] < 0)
                      | (tmp['mem-res-growth-kbytes'] < 0)].sum(), 'deallocation-sum')

            # HDD part
            store(df[['read-sectors', 'write-sectors', 'write-cancelled']].sum(), 'sum')

            # GPU part
            store(df[['busy', 'mem-busy', 'mem-util-kb']].sum(), 'sum')
            store(df[['mem-util-kb']].max(), 'max')

    def to_dict(r):
        d = vars(r)
        d['probable-duration'] = r.get_end() - r.start
        d.pop('records')
        return d
    LOGGER.debug(f'Converting to excel')
    df = pd.DataFrame.from_dict(to_dict(p) for p in processes.values())
    aggfunc = {'probable-duration': sum}
    for c in df.columns.values:
        if '-sum' in c:
            aggfunc[c] = np.sum
        if '-max' in c:
            aggfunc[c] = np.max
        if '-mean' in c:
            aggfunc[c] = np.mean
    table = pd.pivot_table(df, index=['name'], aggfunc=aggfunc)
    with pd.ExcelWriter(dest) as writer:
        table.to_excel(writer, sheet_name='overview')
        df.to_excel(writer, sheet_name='processes')


def main(args):
    file = args.atop
    destination = args.dest
    processes = parse_prg(file)
    update_prc(file, processes)
    update_prm(file, processes)
    update_pre(file, processes)
    update_prd(file, processes)
    get_statistics(processes, destination)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-atop', help='path to the atop file', required=True)
    parser.add_argument('-dest', help='path to resulting xml file', required=True)

    return parser.parse_args()


if __name__ == '__main__':
    import cProfile
    #cProfile.run('
    main(parse_args())
