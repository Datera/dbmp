from __future__ import (unicode_literals, print_function, absolute_import,
                        division)

import io
import json
import sys
import time

from dbmp.volume import ais_from_vols
from dbmp.utils import Parallel, dprint

# Python 2/3 compat
try:
    unicode("")
except NameError:
    unicode = str


def get_metrics(api, metrics, vols, interval, timeout, op):
    ais = []
    for vol in vols:
        ais.extend(ais_from_vols(api, vol))
    results = {ai.name: {metric: [] for metric in metrics} for ai in ais}
    args = [(api, results, ai, metrics, interval, timeout) for ai in ais]
    funcs = [_get_metric for _ in ais]
    p = Parallel(funcs, args_list=args, max_workers=len(funcs))
    p.run_threads()
    if op == 'average':
        _do_average(results)
    elif op == 'max':
        _do_max(results)
    elif op == 'min':
        _do_min(results)
    elif op == 'total-average':
        _do_total_average(results)
    elif op == 'total-max':
        _do_total_max(results)
    elif op == 'total-min':
        _do_total_min(results)
    return results


def write_metrics(data, outfile):
    print("Writing metrics data to:", outfile)
    if outfile == 'stdout':
        f = sys.stdout
        f.write(unicode(json.dumps(data, indent=4)))
    else:
        with io.open(outfile, 'w+', encoding='utf-8') as f:
            f.write(unicode(json.dumps(data, indent=4)))


def _get_metric(api, results, ai, metrics, interval, timeout):
    eps = [(getattr(api.metrics.io, metric), metric) for metric in metrics]
    while timeout > 0:
        for ep, metric in eps:
            dprint("Getting metric {} data from ai {}".format(metric, ai.name))
            data = ep.latest.get(uuid=ai.id)[0]['point']
            results[ai.name][metric].append(data)
        time.sleep(interval)
        timeout -= interval


def _do_average(results):
    _func_helper(results, _average)


def _do_max(results):
    _func_helper(results, max)


def _do_min(results):
    _func_helper(results, min)


def _do_total_average(results):
    _total_helper(results, _average)


def _do_total_max(results):
    _total_helper(results, max)


def _do_total_min(results):
    _total_helper(results, min)


def _average(v):
    return int(sum(v) / len(v))


def _func_helper(results, func):
    for name, v1 in results.items():
        for m, v2 in v1.items():
            v = [elem['value'] for elem in v2]
            results[name][m] = func(v)


def _total_helper(results, func):
    newr = {}
    for name, v1 in results.items():
        for m, v2 in v1.items():
            name = 'total_min_{}'.format(m)
            if name not in results:
                newr[name] = []
            newr[name].extend([elem['value'] for elem in v2])
    for k, v in newr.items():
        newr[k] = func(v)
    for k in results.keys():
        del results[k]
    results.update(newr)
