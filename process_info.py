import subprocess
import pandas as pd
import logging
import re
from atop_constants import *

LOGGER = logging.getLogger()
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


def __run(cmd):
    LOGGER.debug('__run called')
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
    def __init__(self, pid, name, command, start):
        self.pid = pid
        self.name = name
        self.command = command
        self.start = start  # epoch
        self.end = None  # epoch
        self.records = {}

    def update(self, time, data: dict):
        if time not in self.records:
            self.records[time] = data
        else:
            self.records[time].update(data)

    def set_end(self, end):
        self.end = end

    def __repr__(self):
        return str(vars(self))


def get_token(t, tokens, fields, with_brackets):
    index = list(fields.keys()).index(t)
    val = tokens[index]
    if t in with_brackets:
        val = val.replace('(', '').replace(')', '')
    return fields[t](val)


def parse_general(file, label):
    success, log = __run(f'atop -r {file} -P {label}')
    if not success:
        LOGGER.critical(f'Could not obtain process data for file {file} and label {label}')
        exit(-1)
    # split on space, except when it's between brackets
    pattern = re.compile(r'\s+(?=[^()]*(?:\(|$))')
    #pattern = re.compile(r'\s+|(\(.*?\))')
    first_sep_found = False
    for line in log:
        # data till first separator contain data since boot (which we don't want)
        if not first_sep_found:
            if line.startswith(SEP):
                first_sep_found = True
            continue
        if line.startswith(SEP) or line.startswith(RESET):
            continue
        tokens = pattern.split(line)
        yield tokens


def parse_prg(file):
    def get(t):
        return get_token(t, tokens, PRG_FIELDS, PRG_FIELDS_BETWEEN_BRACKETS)
    processes = {}
    for tokens in parse_general(file, 'PRG'):
        pid = get('pid')
        process = processes.setdefault(pid, ProcessInfo(pid, get('name'), get('command'), get('start')))
        state = get('state')
        if 'E' in state:
            process.set_end(get('epoch'))
    return processes


def update_general(file, processes, label, fields, all_fields, fields_between_brackets):
    def get(t):
        return get_token(t, tokens, all_fields, fields_between_brackets)

    def kv(k):
        return k, get(k)
    for tokens in parse_general(file, label):
        process = processes[get('pid')]
        process.update(get('epoch'), dict(map(kv, fields)))


def update_prc(file, processes):
    LOGGER.debug('update prc started')
    update_general(file, processes, 'PRC', ['clock-ticks', 'cpu-usr', 'cpu-sys'],
                   PRC_FIELDS, PRC_FIELDS_BETWEEN_BRACKETS)
    LOGGER.debug('update prc done')


def update_prm(file, processes):
    LOGGER.debug('update prm done')
    update_general(file, processes, 'PRM', ['data-size-kbytes', 'swap-kbytes'],
                   PRM_FIELDS, PRM_FIELDS_BETWEEN_BRACKETS)
    LOGGER.debug('update prm done')


def update_pre(file, processes):
    update_general(file, processes, 'PRE', ['busy', 'mem-busy', 'mem-util-kb'],
                   PRE_FIELDS, PRE_FIELDS_BETWEEN_BRACKETS)


def update_prd(file, processes):
    update_general(file, processes, 'PRD', ['read-sectors', 'write-sectors'],
                   PRD_FIELDS, PRD_FIELDS_BETWEEN_BRACKETS)


def get_statistics(processes):
    for k, v in processes.items():
        LOGGER.debug(f'Computing statistics for pid {k}')
        data = v.records
        if data:  # skip empty data
            df = pd.DataFrame.from_dict(data, orient='index')
            for field, records in df.describe().items():
                for metric, value in records.items():
                    setattr(v, f'{field}_{metric}', value)

    def to_dict(r):
        d = vars(r)
        d.pop('records')
        return d
    LOGGER.debug(f'Converting to excel')
    df = pd.DataFrame.from_dict([to_dict(p) for p in processes.values()])
    df.to_excel('test.xls')


def main(args):
    file = args.atop
    processes = parse_prg(file)
    update_prc(file, processes)
    update_prm(file, processes)
    update_pre(file, processes)
    update_prd(file, processes)
    get_statistics(processes)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-atop', help='path to the atop file')
    input_group.add_argument('-pickle', help='path to pickle file')

    parser.add_argument('-to_png', help='path to the png file')
    parser.add_argument('-to_pickle', help='path to pickle')
    parser.add_argument('-i', '--interactive', help='open interactive plot', action='store_true')

    return parser.parse_args()


if __name__ == '__main__':
    import cProfile
    #cProfile.run('
    main(parse_args())
