import sys
ATOP_TIMESTAMP = 'timestamp'

# since Python 3.6, dicts keep insertion order
assert sys.version_info >= (3, 6)

# copied (and slightly altered) from man
COMMON_FIELDS = {'label': str, 'host': str, 'epoch': int, 'date': str, 'time': str, 'interval': str}
SEP = 'SEP'
RESET = 'RESET'
PRG_FIELDS = {**COMMON_FIELDS, **{'pid': int, 'name': str, 'state': str, 'uid-real': int, 'gid-real': int, 'tgid': int,
                                  'threads-count': int, 'exit-code': int, 'start': int, 'command': str, 'ppid': int,
                                  'threads-r': int, 'threads-s': int, 'threads-d': int, 'uid-effective': int,
                                  'gid-effective': int, 'uid-saved': int, 'gid-saved': int, 'uid-filesystem': int,
                                  'gid-filesystem': int, 'elapsed-time': int, 'is-process': str, 'vpid': int,
                                  'ctid': int, 'cid': int}}
PRG_FIELDS_BETWEEN_BRACKETS = ['name', 'command']

PRC_FIELDS = {**COMMON_FIELDS, **{'pid': int, 'name': str, 'state': str, 'clock-ticks': int, 'cpu-usr': int,
                                  'cpu-sys': int, 'nice': int, 'priority': int, 'priority-realtime': int,
                                  'scheduling': int, 'cpu-cur': int, 'sleep-avg': int, 'tgid': int, 'is-process': str}}
PRC_FIELDS_BETWEEN_BRACKETS = ['name']

PRM_FIELDS = {**COMMON_FIELDS, **{'pid': int, 'name': str, 'state': str, 'page-bytes': int, 'mem-virt-kbytes': int,
                                  'mem-res-kbytes': int, 'mem-shared-text-kbytes': int, 'mem-virt-growth-kbytes': int,
                                  'mem-res-growth-kbytes': int, 'page-faults-minor': int, 'page-faults-major': int,
                                  'exec-size-kbytes': int, 'data-size-kbytes': int, 'stack-size-kbytes': int,
                                  'swap-kbytes': int, 'tgid': int, 'is-process': str, 'set-size-kbytes': int}}
PRM_FIELDS_BETWEEN_BRACKETS = ['name']

PRE_FIELDS = {**COMMON_FIELDS, **{'pid': int, 'name': str, 'state': str, 'gpu-state': str, 'gpus-used': int,
                                  'bitlist': int, 'busy': int, 'mem-busy': int, 'mem-util-curr-kb': int,
                                  'mem-util-kb': int, 'samples': int}}
PRE_FIELDS_BETWEEN_BRACKETS = ['name']

PRD_FIELDS = {**COMMON_FIELDS, **{'pid': int, 'name': str, 'state': str, 'obsolete-kernel': str, 'std-stat-used': str,
                                  'reads': int, 'read-sectors': int, 'writes': int, 'write-sectors': int,
                                  'write-cancelled': int, 'tgid': int, 'is-process': str}}
PRD_FIELDS_BETWEEN_BRACKETS = ['name']
