from __future__ import unicode_literals, print_function, division

import copy
import io
import json

from dfs_sdk import exceptions as dat_exceptions

from dbmp.utils import Parallel

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

MULTI_VOL_TEMPLATE = {'name': 'app-1',
                      'sis': [
                          {'name': 'storage-1',
                           'vols': [
                               {'name': 'volume-1',
                                'size': 1,
                                'replica': 3,
                                'placement_mode': 'hybrid',
                                'qos': {}},
                               {'name': 'volume-1',
                                'size': 1,
                                'replica': 3,
                                'placement_mode': 'hybrid',
                                'qos': {}}]},
                          {'name': 'storage-2',
                           'vols': [
                               {'name': 'volume-1',
                                'size': 1,
                                'replica': 3,
                                'placement_mode': 'hybrid',
                                'qos': {}},
                               {'name': 'volume-1',
                                'size': 1,
                                'replica': 3,
                                'placement_mode': 'hybrid',
                                'qos': {}}]}]}


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
    opts = copy.deepcopy(VOL_DEFAULTS)
    if len(parts) == 1 and '=' not in parts[0]:
        ropts = read_vol_opts(parts[0])
        for k, v in ropts.items():
            opts[k] = v
        return opts
    elif len(parts) < 1:
        return opts
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


def ais_from_vols(api, vols):
    ais = []
    try:
        opts = parse_vol_opt(vols)
    except Exception:
        for name in vols.split(','):
            ais.append(api.app_instances.get(name))
        return ais
    if 'sis' in opts:
        try:
            ais.append(api.app_instances.get(opts['name']))
        except dat_exceptions.ApiNotFoundError:
            print("No app_instance found matching name: {}".format(
                opts['name']))
        return ais
    for i in range(opts['count']):
        try:
            ai = api.app_instances.get(opts['prefix'] + '-' + str(i))
            ais.append(ai)
        except dat_exceptions.ApiNotFoundError:
            print("No app_instance found matching prefix: {}".format(
                opts['prefix']))
            break
    return ais


def _create_volume(api, opts, i, results):
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
    results.append(ai)


def _create_complex_volume(api, opts):
    ai = api.app_instances.create(name=opts['name'])
    for dsi in opts['sis']:
        si = ai.storage_instances.create(name=dsi['name'])
        for dvol in dsi['vols']:
            tvol = copy.deepcopy(VOL_DEFAULTS)
            tvol.update(**dvol)
            vol = si.volumes.create(
                name=tvol['name'],
                replica_count=tvol['replica'],
                size=tvol['size'],
                placement_mode=tvol['placement_mode'])
            if tvol['qos']:
                vol.performance_policy.create(**tvol['qos'])
    print("Created complex volume:", opts['name'])
    return ai


def create_volumes(api, vopt, workers):
    print("Creating volumes:", vopt)
    opts = parse_vol_opt(vopt)
    ais = ais_from_vols(vopt)
    # If they already exist lets just use them
    if ais:
        return ais
    if 'sis' in opts:
        return [_create_complex_volume(api, opts)]
    funcs, args, results = [], [], []
    for i in range(int(opts['count'])):
        funcs.append(_create_volume)
        args.append((api, opts, i, results))
    p = Parallel(funcs, args_list=args, max_workers=workers)
    p.run_threads()
    return results


def _clean_volume(ai, opts):
    if ai.name.startswith(opts['prefix']):
        print("Cleaning volume:", ai.name)
        ai.set(admin_state='offline', force=True)
        ai.delete(force=True)


def clean_volumes(api, vopt, workers):
    print("Cleaning volumes matching:", vopt)
    opts = parse_vol_opt(vopt)
    if 'sis' in opts:
        opts['prefix'] = opts['name']
    elif 'prefix' not in opts:
        print("No prefix specified, using default, if all volumes should be "
              "cleaned, use --volume name=all")
    funcs, args = [], []
    for ai in api.app_instances.list():
        funcs.append(_clean_volume)
        args.append((ai, opts))
    p = Parallel(funcs, args_list=args, max_workers=workers)
    p.run_threads()
