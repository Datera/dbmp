#!/usr/bin/env python

from __future__ import unicode_literals, print_function, division

import argparse
import sys
import textwrap

from dfs_sdk import scaffold

from volume import DEFAULT_PREFIX, create_volumes, clean_volumes
from topology import get_topology
from mount import mount_volumes, mount_volumes_remote, clean_mounts
from mount import clean_mounts_remote

SUCCESS = 0
FAILURE = 1


def hf(txt):
    return textwrap.fill(txt)


def main(args):
    api = scaffold.get_api()
    get_topology(args.host, args.topology_file)
    print('Using Config:')
    scaffold.print_config()

    if args.clean:
        if args.host == 'local':
            for vol in args.volume:
                clean_mounts(api, vol, args.directory, args.workers)
        else:
            clean_mounts_remote(args.host)
        for vol in args.volume:
            clean_volumes(api, vol, args.workers)
        return SUCCESS

    vols = None
    for vol in args.volume:
        vols = create_volumes(api, vol, args.workers)

    if args.mount and vols and args.host == 'local':
        mount_volumes(api, vols, not args.no_multipath, args.fstype,
                      args.fsargs, args.directory, args.workers)
    elif args.mount and vols and args.host != 'local':
        mount_volumes_remote(args.host, vols, not args.no_multipath,
                             args.fstype, args.fsargs, args.directory,
                             args.workers)
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
    parser.add_argument('-w', '--workers', default=5,
                        help='Number of worker threads for this action')
    parser.add_argument('-n', '--no-multipath', action='store_true')
    parser.add_argument('-f', '--fstype', default='xfs',
                        help='Filesystem to use when formatting devices')
    parser.add_argument('-a', '--fsargs', default='',
                        help='Extra args to give formatter, eg "-E '
                             'lazy_table_init=1".  Make sure fstype matches '
                             'the args you are passing in')
    parser.add_argument('-d', '--directory', default='/mnt',
                        help='Directory under which to mount devices')
    args = parser.parse_args()
    sys.exit(main(args))
