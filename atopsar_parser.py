from atop_resource import AtopResource
from atop_processes import AtopProcess
import subprocess
import logging
import sys
import pandas as pd
from atop_constants import *


LOGGER = logging.getLogger()
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


class AtopsarParser:
    @staticmethod
    def __run(cmd):
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

    @staticmethod
    def __parse_general(file, flags, desc, cols):
        import matplotlib.dates as dates
        success, log = AtopsarParser.__run(f'atopsar {flags} -a -r {file}')
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
        cols_dict[ATOP_TIMESTAMP] = 0
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

    @staticmethod
    def __parse_processes(file, flags, desc):
        import matplotlib.dates as dates
        success, log = AtopsarParser.__run(f'atopsar {flags} -r {file}')
        if not success:
            LOGGER.critical(f'Could not obtain {desc} related data')
            exit(-1)
        # third line should be headers
        # david  5.4.0-56-generic  #62-Ubuntu SMP Mon Nov 23 19:20:19 UTC 2020  x86_64  2020/12/10
        # -------------------------- analysis date: 2020/12/02 --------------------------
        # 17:29:24    pid command  mem% |   pid command  mem% |   pid command  mem%_top3_
        data = {}
        for line in log[3:]:
            # first 8 characters are time, the rest is the line
            time = line[:8]
            text = line[8:]
            data[time] = text
        return data

    @staticmethod
    def parse_cpu(file):
        cols = ['cpu', '%usr', '%sys']
        data = AtopsarParser.__parse_general(file, '-c', 'cpu', cols)
        df = pd.DataFrame(data)
        tmp = df[df['cpu'] != 'all']['cpu']
        no_of_cores = (pd.to_numeric(tmp).max() + 1) / 2  # assume multithreading is on, we want physical cores only
        LOGGER.info(f'Detected {no_of_cores} cores (assuming multithreading support)')
        df = df[df['cpu'] == 'all']
        df.rename(columns={'%usr': 'usr', '%sys': 'sys'}, inplace=True)
        df[['usr', 'sys']] = df[['usr', 'sys']].apply(pd.to_numeric) / no_of_cores
        return AtopResource('cpu', '%', df, desc=f'100% means all physical cores are used.\n{no_of_cores} detected.')

    @staticmethod
    def parse_drives(file):
        # 18:05:04 disk busy read/s KB/read writ/s KB/writ avque avserv _dsk_
        cols = ['disk', 'busy', 'read/s', 'KB/read', 'writ/s', 'KB/writ']
        data = AtopsarParser.__parse_general(file, '-d', 'hdd', cols)
        df = pd.DataFrame(data)
        df['busy'] = df['busy'].str.replace('%', '')
        df[cols[1:]] = df[cols[1:]].apply(pd.to_numeric)
        df[cols[1:]] = df[cols[1:]].apply(pd.to_numeric)
        result = []
        for d, data in df.groupby('disk'):
            drive = AtopResource(f'disk: {d}', '%', data[[ATOP_TIMESTAMP, 'busy']])
            data['read'] = data['read/s'] * data['KB/read'] / 1024
            data['write'] = data['writ/s'] * data['KB/writ'] / 1024
            drive.data_opt = data[[ATOP_TIMESTAMP, 'read', 'write']]
            drive.data_opt_unit = 'MB/s'
            result.append(drive)
        return result

    @staticmethod
    def parse_memory(file):
        # 18:05:04  memtotal memfree buffers cached dirty slabmem  swptotal swpfree _mem_
        # 18:05:05    31986M  27272M    111M  1196M    0M    290M    32767M  32767M
        cols = ['memtotal', 'memfree', 'cached', 'buffers', 'swptotal', 'swpfree']
        data = AtopsarParser.__parse_general(file, '-m', 'memory', cols)
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
        df = df[[ATOP_TIMESTAMP, 'allocated', 'cache', 'occupancy', 'swap']]
        return AtopResource('ram', '%', df, desc=f'Detected {mem_total} MB of memory and {swap_total} MB of Swap.')

    @staticmethod
    def parse_gpus(file):
        # 18:05:04     busaddr   gpubusy  membusy  memocc  memtot memuse  gputype   _gpu_
        # 18:05:05   0/0000:01:0      1%       0%     22%   6078M  1378M  rce_GTX_1060
        num_cols = ['gpubusy', 'membusy', 'memocc']
        info_cols = ['busaddr', 'gputype']
        data = AtopsarParser.__parse_general(file, '-g', 'gpu', num_cols + info_cols)
        df = pd.DataFrame(data)
        for c in num_cols:
            df[c] = pd.to_numeric(df[c].str.replace('%', ''))
        df.rename(columns={'gpubusy': 'utilization', 'membusy': 'read/write', 'memocc': 'memused'}, inplace=True)
        result = []
        for g, data in df.groupby('busaddr'):
            gpu_type = data['gputype'][0]
            name = f'{g} {gpu_type}'
            gpu = AtopResource(f'gpu: {name}', '%', data[[ATOP_TIMESTAMP, 'utilization', 'read/write', 'memused']])
            result.append(gpu)
        return result

    @staticmethod
    def parse_processes(file):
        disk_data = AtopsarParser.__parse_processes(file, '-D', 'disk processes')
        cpu_data = AtopsarParser.__parse_processes(file, '-O', 'cpu processes')
        memory_data = AtopsarParser.__parse_processes(file, '-G', 'memory processes')
        # assume times are the same everywhere
        result = []
        for k, v in disk_data.items():
            result.append(AtopProcess(k, disk_data[k], cpu_data[k], memory_data[k]))
        return result
