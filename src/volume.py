from __future__ import unicode_literals, print_function, division

import copy
import io
import json

from utils import Parallel

DEFAULT_PREFIX = 'DBMP'
STORE_NAME = 'storage-1'
VOL_NAME = 'volume-1'
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
            opts['qos'][k] = int(v)
        else:
            try:
                opts[k] = int(v)
            except (TypeError, ValueError):
                opts[k] = v
    return opts


def _create_volume(api, opts, i):
    qos = opts['qos']
    name = opts['prefix'] + '-' + str(i)
    ai = api.app_instances.create(name=name)
    si = ai.storage_instances.create(name=STORE_NAME)
    vol = si.volumes.create(
        name=VOL_NAME,
        replica_count=opts['replica'],
        size=opts['size'],
        placement_mode=opts['placement_mode'])
    if qos:
        vol.performance_policy.create(**qos)
    print("Created volume:", name)


def create_volumes(api, vopt, workers):
    print("Creating volumes:", vopt)
    opts = parse_vol_opt(vopt)
    funcs, args = [], []
    for i in range(int(opts['count'])):
        funcs.append(_create_volume)
        args.append((api, opts, i))
    p = Parallel(funcs, args_list=args, max_workers=workers)
    p.run_threads()


def _clean_volume(ai, opts):
    if ai.name.startswith(opts['prefix']):
        print("Cleaning volume:", ai.name)
        ai.set(admin_state='offline')
        ai.delete(force=True)


def clean_volumes(api, vopt, workers):
    print("Cleaning volumes matching:", vopt)
    opts = parse_vol_opt(vopt)
    if 'prefix' not in opts:
        print("No prefix specified, if all volumes should be cleaned, "
              "use --volume name=all")
        return
    funcs, args = [], []
    for ai in api.app_instances.list():
        funcs.append(_clean_volume)
        args.append((ai, opts))
    p = Parallel(funcs, args_list=args, max_workers=workers)
    p.run_threads()
