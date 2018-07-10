#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division

import argparse
import sys
import textwrap

from dfs_sdk import scaffold
# from dfs_sdk import exceptions as dexceptions

from dbmp.volume import create_volumes, clean_volumes, list_volumes
from dbmp.volume import list_templates
from dbmp.mount import mount_volumes, mount_volumes_remote, clean_mounts
from dbmp.mount import clean_mounts_remote
from dbmp.fio import run_fio, run_fio_remote
from dbmp.utils import exe

SUCCESS = 0
FAILURE = 1


def hf(txt):
    return textwrap.fill(txt)


def run_health(api):
    config = scaffold.get_config()
    try:
        exe('ping -c 1 -w 1 {}'.format(config['mgmt_ip']))
    except EnvironmentError:
        print('Could not ping mgmt_ip:', config['mgmt_ip'])
        return False
    try:
        api.app_instances.list()
    except Exception as e:
        print("Could not connect to cluster", e)
        return False
    npass = True
    av = api.system.network.access_vip.get()
    for np in av['network_paths']:
        ip = np.get('ip')
        if ip:
            try:
                exe('ping -c 1 -w 1 {}'.format(ip))
            except EnvironmentError:
                print('Could not ping: {} {}'.format(np.get('name'), ip))
                npass = False
    if not npass:
        return False
    print("Health Check Completed Successfully")
    return True


def main(args):
    api = scaffold.get_api()
    print('Using Config:')
    scaffold.print_config()

    if args.health:
        if not run_health(api):
            return FAILURE
        return SUCCESS

    if 'volumes' in args.list:
        for vol in args.volume:
            list_volumes(args.run_host, api, vol, detail='detail' in args.list)
        return SUCCESS
    elif 'templates' in args.list:
        list_templates(api, detail='detail' in args.list)
        return SUCCESS

    if args.unmount or args.clean:
        for vol in args.volume:
            if args.run_host == 'local':
                clean_mounts(api, vol, args.directory, args.workers)
            else:
                clean_mounts_remote(
                    args.run_host, vol, args.directory, args.workers)
            if args.unmount:
                return SUCCESS
    if args.clean:
        for vol in args.volume:
            clean_volumes(api, vol, args.workers)
        return SUCCESS

    vols = None
    for vol in args.volume:
        vols = create_volumes(args.run_host, api, vol, args.workers)

    if args.mount and vols and args.run_host == 'local':
        mount_volumes(api, vols, not args.no_multipath, args.fstype,
                      args.fsargs, args.directory, args.workers)
    elif args.mount and vols and args.run_host != 'local':
        mount_volumes_remote(args.run_host, vols, not args.no_multipath,
                             args.fstype, args.fsargs, args.directory,
                             args.workers)

    if args.fio:
        try:
            exe("which fio")
        except EnvironmentError:
            print("FIO is not installed")
    if args.fio and not args.mount:
        print("--mount MUST be specified when using --fio")
    elif args.fio and args.run_host == 'local':
        run_fio(vols, args.fio_workload, args.directory)
    elif args.fio and args.run_host != 'local':
        run_fio_remote(args.run_host, vols, args.fio_workload, args.directory)
    return SUCCESS


if __name__ == '__main__':
    tparser = scaffold.get_argparser(add_help=False)
    parser = argparse.ArgumentParser(
        parents=[tparser], formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-s', '--run-host', default='local',
                        help=hf('Host on which targets should be logged in.'
                                ' This value will be a key in your '
                                '"dbmp-topology.json" file. Use "local" for'
                                'the current host'))
    parser.add_argument('--health', action='store_true',
                        help='Run a quick health check')
    parser.add_argument('--list', choices=('volumes', 'volumes-detail',
                                           'templates', 'templates-detail'),
                        default='',
                        help='List accessible Datera Resources')
    parser.add_argument('--volume', action='append', default=[],
                        help='Supports the following comma separated params:\n'
                             ' \n'
                             '* prefix, default=--run-default hostname\n'
                             '* count (num created), default=1\n'
                             '* size (GB), default=1\n'
                             '* replica, default=3\n'
                             '* <any supported qos param, eg: read_iops_max>\n'
                             '* placement_mode, default=hybrid\n'
                             '      choices: hybrid|single_flash|all_flash\n'
                             '* template, default=None\n \n'
                             'Example: prefix=test,size=2,replica=2\n \n'
                             'Alternatively a json file with the above\n'
                             'parameters can be specified')
    parser.add_argument('-m', '--mount', action='store_true',
                        help='Mount volumes')
    parser.add_argument('-u', '--unmount', action='store_true',
                        help='Unmount volumes only.  Does not delete volume')
    parser.add_argument('-c', '--clean', action='store_true',
                        help='Will both unmount and delete volumes')
    parser.add_argument('-w', '--workers', default=5,
                        help='Number of worker threads for this action')
    parser.add_argument('-n', '--no-multipath', action='store_true')
    parser.add_argument('-f', '--fstype', default='xfs',
                        help='Filesystem to use when formatting devices')
    parser.add_argument('-a', '--fsargs', default='',
                        help=hf('Extra args to give formatter, eg "-E '
                                'lazy_table_init=1".  Make sure fstype matches'
                                ' the args you are passing in'))
    parser.add_argument('-d', '--directory', default='/mnt',
                        help='Directory under which to mount devices')
    parser.add_argument('-i', '--fio', action='store_true',
                        help='Run fio workload against mounted volumes')
    parser.add_argument('-l', '--fio-workload',
                        help='Fio workload file to use.  If not specified, '
                             'default workload will be used')
    args = parser.parse_args()
    sys.exit(main(args))
