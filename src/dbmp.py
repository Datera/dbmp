#!/usr/bin/env python

from __future__ import unicode_literals, print_function, division

import argparse
import io
import json
import sys
import textwrap

from dfs_sdk import scaffold

from volume import DEFAULT_PREFIX, create_volumes

SUCCESS = 0
FAILURE = 1

_TOPOLOGY = None


def hf(txt):
    return textwrap.fill(txt)


def read_topology_file(tfile):
    with io.open(tfile) as f:
        return json.loads(f.read())


def get_topology(host, tfile):
    global _TOPOLOGY
    if not _TOPOLOGY:
        config = scaffold.get_config()
        if 'topology' in config:
            _TOPOLOGY = config['topology']
        elif host != 'local':
            _TOPOLOGY = read_topology_file(tfile)
    if host != 'local' and not _TOPOLOGY:
        raise EnvironmentError(
            "Non-local host specified, but no topology file found")
    return _TOPOLOGY


def main(args):
    scaffold.get_api()
    print('Using Config:')
    get_topology(args.host, args.topology_file)
    scaffold.print_config()

    for vol in args.volume:
        create_volumes(vol)
    return SUCCESS


if __name__ == '__main__':
    tparser = scaffold.get_argparser(add_help=False)
    parser = argparse.ArgumentParser(
        parents=[tparser], formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-c', '--host', default='local',
                        help=hf('Host on which targets should be logged in.'
                                ' This value will be a key in your '
                                '"dbmp-topology.json" file. Use "local" for'
                                'the current host'))
    parser.add_argument('-t', '--topology-file', default='dbmp-topology.json')
    parser.add_argument('--volume', action='append', default=[],
                        help='Supports the following comma separated params:\n'
                             ' \n'
                             '* prefix, default={}\n'
                             '* count (num created), default=1\n'
                             '* size (GB), default=1\n'
                             '* replica, default=3\n'
                             '* <any supported qos param, eg: read_iops_max>\n'
                             '* placement_mode, default=hybrid\n'
                             '* template, default=None\n \n'
                             'Example: prefix=test,size=2,replica=2\n \n'
                             'Alternatively a json file with the above\n'
                             'parameters can be specified'.format(
                                 DEFAULT_PREFIX))
    parser.add_argument('-m', '--mount', action='store_true',
                        help='Mount volumes')
    args = parser.parse_args()
    sys.exit(main(args))
