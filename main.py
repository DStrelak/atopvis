import matplotlib.pyplot as plt
import subprocess
import pandas as pd
import logging
from functools import reduce
import sys
from collections import ChainMap
from statistics import median
from os.path import join as join_path

LOGGER = logging.getLogger()
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
TIMESTAMP = 'timestamp'


def onpick(event):
    thisline = event.artist
    xdata = thisline.get_xdata()
    ydata = thisline.get_ydata()
    ind = event.ind
    points = tuple(zip(xdata[ind], ydata[ind]))
    print('onpick points:', points)


def run(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    log = []
    while True:
        output = p.stdout.readline().decode("utf-8").rstrip('\n')
        if output == '' and p.poll() is not None:
            break
        if '' == output:
            continue
        log.append(output)
    return 0 == p.poll(), log


def parse_general(file, flags, desc, cols):
    import matplotlib.dates as dates
    success, log = run(f'atopsar {flags} -r {file}')
    if not success:
        LOGGER.critical(f'Could not obtain {desc} related data')
        exit(-1)
    # third line should be headers
    # david  5.4.0-56-generic  #62-Ubuntu SMP Mon Nov 23 19:20:19 UTC 2020  x86_64  2020/12/04
    # -------------------------- analysis date: 2020/12/02 --------------------------
    # 18:05:04  memtotal memfree buffers cached dirty slabmem  swptotal swpfree _mem_
    headers = log[2].split()
    cols_dict = {c: headers.index(c) for c in cols}
    max_inx = max(cols_dict.values())
    cols_dict[TIMESTAMP] = 0
    timestamp = headers[0]
    data = []
    for line in log[3:]:
        tokens = line.split()
        if ':' in tokens[0]:
            timestamp = dates.datestr2num(tokens[0])
            tokens[0] = timestamp
        else:
            tokens.insert(0, timestamp)
        if len(tokens) >= max_inx:  # in case of missing records
            data.append({k: tokens[v] for k, v in cols_dict.items()})
    return data


def parse_cpu(file):
    cols = ['cpu', '%usr', '%sys']
    data = parse_general(file, '-c', 'cpu', cols)
    df = pd.DataFrame(data)
    tmp = df[df['cpu'] != 'all']['cpu']
    no_of_cores = (pd.to_numeric(tmp).max() + 1) / 2  # assume multithreading is on, we want physical cores only
    LOGGER.info(f'Detected {no_of_cores} cores (assuming multithreading support)')
    df = df[df['cpu'] == 'all']
    df.rename(columns={'%usr': 'usr', '%sys': 'sys'}, inplace=True)
    df[['usr', 'sys']] = df[['usr', 'sys']].apply(pd.to_numeric) / no_of_cores
    return {'cpu': df}


def parse_hdd(file):
    # 18:05:04 disk busy read/s KB/read writ/s KB/writ avque avserv _dsk_
    cols = ['disk', 'busy', 'read/s', 'KB/read', 'writ/s', 'KB/writ']
    data = parse_general(file, '-d', 'hdd', cols)
    df = pd.DataFrame(data)
    df['busy'] = df['busy'].str.replace('%', '')
    df[cols[1:]] = df[cols[1:]].apply(pd.to_numeric)
    df[cols[1:]] = df[cols[1:]].apply(pd.to_numeric)
    result = {}
    for d, data in df.groupby('disk'):
        result[d] = data[[TIMESTAMP, 'busy']]
        data['read'] = data['read/s'] * data['KB/read'] / 1024
        data['write'] = data['writ/s'] * data['KB/writ'] / 1024
        result[f'{d} IO (MB/s)'] = data[[TIMESTAMP, 'read', 'write']]
    # remove records with too few hits (we're probably not interested in them)
    med = median([len(d) for d in result.values()])
    result = {k: v for k, v in result.items() if len(v) > (med / 10)}
    return result


def parse_memory(file):
    # 18:05:04  memtotal memfree buffers cached dirty slabmem  swptotal swpfree _mem_
    # 18:05:05    31986M  27272M    111M  1196M    0M    290M    32767M  32767M
    cols = ['memtotal', 'memfree', 'cached', 'buffers', 'swptotal', 'swpfree']
    data = parse_general(file, '-m', 'memory', cols)
    df = pd.DataFrame(data)
    for c in cols:
        df[c] = df[c].str.replace('M', '')
    df[cols] = df[cols].apply(pd.to_numeric)
    # get memory usage
    mem_total = df['memtotal'][0]
    LOGGER.info(f'Detected {mem_total} MB of memory')
    df['allocated'] = (df['memtotal'] - df['cached'] - df['memfree'] - df['buffers']) / mem_total * 100
    df['cache'] = (df['cached'] + df['buffers']) / mem_total * 100
    df['occupancy'] = (df['memtotal'] - df['memfree']) / mem_total * 100
    # get swap usage
    swap_total = df['swptotal'][0]
    LOGGER.info(f'Detected {mem_total} MB of swap')
    df['swap'] = (df['swptotal'] - df['swpfree']) / swap_total * 100
    # prepare result
    df = df[[TIMESTAMP, 'allocated', 'cache', 'occupancy', 'swap']]
    return {'ram': df}


def parse_gpu(file):
    # 18:05:04     busaddr   gpubusy  membusy  memocc  memtot memuse  gputype   _gpu_
    # 18:05:05   0/0000:01:0      1%       0%     22%   6078M  1378M  rce_GTX_1060
    num_cols = ['gpubusy', 'membusy', 'memocc']
    info_cols = ['busaddr', 'gputype']
    data = parse_general(file, '-g', 'gpu', num_cols + info_cols)
    df = pd.DataFrame(data)
    for c in num_cols:
        df[c] = pd.to_numeric(df[c].str.replace('%', ''))
    df.rename(columns={'gpubusy': 'utilization', 'membusy': 'read/write', 'memocc': 'memused'}, inplace=True)
    result = {}
    for g, data in df.groupby('busaddr'):
        gpu = data['gputype'][0]
        name = f'{g} {gpu}'
        result[name] = data[[TIMESTAMP, 'utilization', 'read/write', 'memused']]
    return result


def plot_all(data):
    df = reduce(lambda left, right: pd.merge(left, right), data)
    df[TIMESTAMP] = pd.to_datetime(df[TIMESTAMP], format='%Y %H:%M:%S')
    df.plot(kind='line', x=TIMESTAMP)
    plt.show()


def plot_subplot(title, data, destination, interactive):
    from matplotlib.ticker import AutoMinorLocator
    import matplotlib.dates as mdates
    fig, axes = plt.subplots(nrows=len(data), ncols=1, sharex='col')
    fig.suptitle(title)
    for i, k in enumerate(sorted(data)):
        ax = axes[i]
        data[k].set_index(TIMESTAMP).plot(ax=ax)
        ax.set_title(k, loc='left')
        ax.grid(True, which='major')
        ax.grid(True, which='minor', alpha=0.2)
        ax.tick_params(axis="x", which="both", rotation=75)  # rotate labels
        ax.xaxis.set_minor_locator(AutoMinorLocator(10))  # create subgrid, divided in 5 pieces
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # fix formatting
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%H:%M:%S'))  # show tick labels for minors too
    fig.set_size_inches(20, len(data) * 2.5)
    if destination:
        plt.savefig(destination, dpi=300, bbox_inches='tight')
    if interactive:
        plt.show()


def parse_atop(file):
    cpu = parse_cpu(file)
    mem = parse_memory(file)
    gpus = parse_gpu(file)
    drives = parse_hdd(file)
    all_metrics = dict(ChainMap({}, drives, cpu, gpus, mem))
    return all_metrics


def export_metrics(destination, metrics):
    from pathlib import Path
    Path(destination).mkdir(parents=True, exist_ok=True)
    for k, v in metrics.items():
        path = join_path(destination, ''.join(x for x in k if x.isalnum() or x in "._- ") + '.csv')
        LOGGER.info(f'exporting {path}')
        v.to_csv(path, index=False)


def import_metrics(directory):
    import glob
    from pathlib import Path
    result = {}
    for f in glob.glob(join_path(directory, '*.csv')):
        p = Path(f)
        LOGGER.info(f'loading {p}')
        result[p.stem] = pd.read_csv(p)
    return result


def load_metrics(args):
    atop_file = args.from_atop
    if atop_file:
        return atop_file, parse_atop(atop_file)
    csv_dir = args.from_csv
    if csv_dir:
        return csv_dir, import_metrics(csv_dir)


def main(args):
    name, metrics = load_metrics(args)
    if args.to_csv:
        export_metrics(args.to_csv, metrics)
    if args.to_png or args.interactive:
        plot_subplot(name, metrics, args.to_png, args.interactive)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-from_atop', help='path to the atop file')
    input_group.add_argument('-from_csv', help='path to directory with csv files')

    parser.add_argument('-to_png', help='path to the png file')
    parser.add_argument('-to_csv', help='path to directory with csv files')
    parser.add_argument('-i', '--interactive', help='open interactive plot', action='store_true')

    return parser.parse_args()


if __name__ == '__main__':
    main(parse_args())
