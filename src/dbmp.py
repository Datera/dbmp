#!/usr/bin/env python

from __future__ import unicode_literals, print_function, division

import argparse
import sys
import textwrap

from dfs_sdk import scaffold

from volume import DEFAULT_PREFIX, create_volumes, clean_volumes
from topology import get_topology

SUCCESS = 0
FAILURE = 1


def hf(txt):
    return textwrap.fill(txt)


def main(args):
    api = scaffold.get_api()
    print('Using Config:')
    get_topology(args.host, args.topology_file)
    scaffold.print_config()

    if args.clean:
        for vol in args.volume:
            clean_volumes(api, vol)
        return SUCCESS

    for vol in args.volume:
        create_volumes(api, vol)
    return SUCCESS


if __name__ == '__main__':
    tparser = scaffold.get_argparser(add_help=False)
    parser = argparse.ArgumentParser(
        parents=[tparser], formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-s', '--host', default='local',
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
    parser.add_argument('-c', '--clean', action='store_true',
                        help='Clean instead of create')
    args = parser.parse_args()
    sys.exit(main(args))
