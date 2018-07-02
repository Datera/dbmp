from __future__ import unicode_literals, print_function, division

import copy
import io
import json

DEFAULT_PREFIX = 'DBMP'
VOL_DEFAULTS = {'size': 1,
                'prefix': DEFAULT_PREFIX,
                'count': 1,
                'replica': 3,
                'placement_mode': 'hybrid',
                'template': None,
                'qos': {}}


def _is_valid(k):
    if k in VOL_DEFAULTS:
        return True
    if k in {'read_iops_max',
             'write_iops_max',
             'total_iops_max',
             'read_bandwidth_max',
             'write_bandwidth_max',
             'total_bandwidth_max'}:
        return True
    return False


def read_vol_opts(ifile):
    with io.open(ifile, 'r') as f:
        return json.loads(f.read())


def parse_vol_opt(s):
    parts = s.split(',')
    if len(parts) == 1 and '=' not in parts[0]:
        return read_vol_opts(parts[0])
    elif len(parts) < 1:
        return copy.deepcopy(VOL_DEFAULTS)
    opts = copy.deepcopy(VOL_DEFAULTS)
    for p in parts:
        k, v = p.split('=')
        if not _is_valid(k):
            raise EnvironmentError("Volume key: {} is not valid".format(k))
        if 'max' in k:
            opts['qos'][k] = v
        else:
            opts[k] = v
    return opts


def create_volumes(vopt):
    opts = parse_vol_opt(vopt)
    print(opts)
