#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division

import argparse
import json
import sys
import textwrap

from dfs_sdk import scaffold

from dbmp.events import clear_alerts, list_alerts, list_events
from dbmp.metrics import get_metrics, write_metrics
from dbmp.mount import mount_volumes, clean_mounts
from dbmp.mount import list_mounts
from dbmp.fio import gen_fio
from dbmp.vdbench import gen_vdb
from dbmp.utils import exe
from dbmp.volume import create_volumes, clean_volumes, list_volumes
from dbmp.volume import list_templates, get_keys, del_keys
from dbmp.placement_policy import create_media_policy, create_placement_policy
from dbmp.placement_policy import list_placement_policies, list_media_policies
from dbmp.placement_policy import delete_placement_policy, delete_media_policy
from dbmp.csi_yaml import udc_envs_from_csi_yaml
from dbmp import show

SUCCESS = 0
FAILURE = 1

METRIC_CHOICES = ('reads', 'writes', 'bytes_read',
                  'bytes_written', 'iops_read', 'iops_write',
                  'thpt_read', 'thpt_write', 'lat_avg_read',
                  'lat_avg_write', 'lat_50_read', 'lat_90_read',
                  'lat_100_read', 'lat_50_write',
                  'lat_90_write', 'lat_100_write')


# Py2/3 compat
try:
    input = raw_input
except NameError:
    pass


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
    if args.csi_yaml:
        udc_envs_from_csi_yaml(args.csi_yaml)
    api = scaffold.get_api()
    print('Using Config:')
    scaffold.print_config()

    if args.health:
        if not run_health(api):
            return FAILURE
        return SUCCESS

    if args.force_initiator_creation:
        resp = input(hf("Forcing initiator creation could result in I/O "
                        "interruption for Volumes connected to the forced "
                        "Initiator being created within this tenant.  Are you "
                        "Sure you want to proceed? Y/n") + "\n")
        if resp != "Y":
            print("Recieved negative confirmation, exiting")
            return FAILURE
        else:
            print("Recieved positive confirmation.  Continuing")

    if args.show_at_url:
        for url in args.show_at_url:
            show.at_url(api, url)
        return SUCCESS

    for arg in args.list:
        detail = 'detail' in arg
        if 'volumes' in arg:
            print("###### VOLUMES {}######".format(
                "DETAIL " if detail else ''))
            for vol in args.volume:
                list_volumes('local', api, vol, detail=detail)
            if not args.volume:
                list_volumes('local', api, 'prefix=all', detail)
        elif 'templates' in arg:
            print("###### TEMPLATES {}######".format(
                "DETAIL " if detail else ''))
            list_templates(api, detail=detail)
        elif 'mounts' in arg:
            print("###### MOUNTS ######".format(
                "DETAIL " if detail else ''))
            for vol in args.volume:
                list_mounts('local', api, vol, detail,
                            not args.no_multipath)
            else:
                list_mounts('local', api, 'prefix=all', detail,
                            not args.no_multipath)
        elif 'alerts' in arg:
            print("###### ALERTS ######")
            list_alerts(api)
        if 'events' in arg:
            print("###### EVENTS ######")
            if 'system' in arg:
                user = 'system'
            if 'user' in arg:
                user = 'user'
            if 'id' in arg:
                user = args.id
            list_events(api, user)
        if 'media-policy' in arg:
            print("###### MEDIA POLICIES ######")
            list_media_policies(api)
        if 'placement-policy' in arg:
            print("###### PLACEMENT POLICIES ######")
            list_placement_policies(api)

    if args.clear_alerts:
        clear_alerts(api)
        return SUCCESS

    if any((args.unmount, args.logout, args.clean)):
        for vol in args.volume:
            del_keys(vol)
            clean_mounts(api, vol, args.directory, args.workers)
            if args.unmount:
                return SUCCESS
    if args.clean:
        for vol in args.volume:
            clean_volumes(api, vol, args.workers)
        for pp in args.placement_policy:
            delete_placement_policy(api, pp)
        for mp in args.media_policy:
            delete_media_policy(api, mp)
        return SUCCESS
    if args.logout:
        return SUCCESS

    # Create placement_policy/media_policy
    for mp in args.media_policy:
        create_media_policy(api, mp)

    for pp in args.placement_policy:
        create_placement_policy(api, pp)

    # Create volumes
    vols = None
    for vol in args.volume:
        vols = create_volumes("local", api, vol, args.workers)

    if args.get_keys:
        for vol in args.volume:
            for n, keys in get_keys(vol):
                print(n, ":", ' '.join(map(str, keys)))

    # Login/mount volumes
    login_only = not args.mount and args.login
    if (args.mount or args.login) and vols:
        dev_or_folders = mount_volumes(
            api, vols, not args.no_multipath, args.fstype, args.fsargs,
            args.directory, args.workers, login_only,
            args.force_initiator_creation)

    # Generate fio/vdbench output
    if args.fio:
        try:
            exe("which fio")
        except EnvironmentError:
            print("FIO is not installed")
    if args.fio and (not args.mount and not args.login):
        print("--mount or --login MUST be specified when using --fio")
    elif args.fio:
        gen_fio(args.fio_workload, dev_or_folders)
    elif args.vdbench:
        gen_vdb(dev_or_folders)

    # Retrieve metrics
    if args.metrics:
        data = None
        try:
            interval, timeout = map(int, args.metrics.split(','))
            if interval < 1 or timeout < 1:
                raise ValueError()
            mtypes = args.metrics_type
            if not args.metrics_type:
                mtypes = ['iops_write']
            data = get_metrics(
                api, mtypes, args.volume, interval, timeout,
                args.metrics_op)
        except ValueError:
            print("--metrics argument must be in format '--metrics i,t' where"
                  "'i' is the interval in seconds and 't' is the timeout in "
                  "seconds.  Both must be positive integers >= 1")
            return FAILURE
        if data:
            write_metrics(data, args.metrics_out_file)
        else:
            print("No data recieved from metrics")
            return FAILURE
    return SUCCESS


if __name__ == '__main__':
    tparser = scaffold.get_argparser(add_help=False)
    parser = argparse.ArgumentParser(
        parents=[tparser], formatter_class=argparse.RawTextHelpFormatter)

    # Health Check
    parser.add_argument('--health', action='store_true',
                        help='Run a quick health check')

    # System Inspection
    parser.add_argument('--show-at-url', action='append', default=[],
                        help='Show resource located at url.  Not for use'
                             'with events and alerts.  Use --list for those')
    parser.add_argument('--list', choices=('volumes', 'volumes-detail',
                                           'templates', 'templates-detail',
                                           'mounts', 'mounts-detail', 'alerts',
                                           'events-system', 'events-user',
                                           'events-id', 'placement-policy',
                                           'media-policy'),
                        action='append', default=[],
                        help='List accessible Datera Resources')
    parser.add_argument('--clear-alerts', action='store_true')

    # This is only used with --list events-id
    parser.add_argument('id', nargs='?')

    # Resource Creation
    parser.add_argument('--volume', action='append', default=[],
                        help='Supports the following comma separated params:\n'
                             ' \n'
                             '* prefix, default=--run-default hostname\n'
                             '* count (num created), default=1\n'
                             '* size (GB), default=1\n'
                             '* replica, default=3\n'
                             '* <any supported qos param, eg: read_iops_max>\n'
                             '* placement_mode, default=hybrid\n'
                             '    choices: hybrid|single_flash|all_flash\n'
                             '* template, default=None\n'
                             '* object, default=False\n'
                             'Example: prefix=test,size=2,replica=2\n \n'
                             'Alternatively a json file with the above\n'
                             'parameters can be specified')
    parser.add_argument('--placement-policy', action='append', default=[],
                        help='Supports the following comma separated params:\n'
                             '\n'
                             '* name, required\n'
                             '* max, required, semicolon separated '
                             'media_policy names\n'
                             '* min, semicolon separated media_policy names\n'
                             '* desc')
    parser.add_argument('--media-policy', action='append', default=[],
                        help='Supports the following comma separated params\n'
                             '\n'
                             '* name, required\n'
                             '* priority, required, integer\n'
                             '* descr\n')

    # Resource access
    parser.add_argument('--login', action='store_true',
                        help='Login volumes (implied by --mount)')
    parser.add_argument('--mount', action='store_true',
                        help='Mount volumes, (implies --login)')
    parser.add_argument('--force-initiator-creation', action='store_true',
                        help='Force initiator creation. WARNING: This might'
                             ' result in I/O interruption to volumes attached'
                             ' to inherited initiator')
    parser.add_argument('--fstype', default='xfs',
                        help='Filesystem to use when formatting devices')
    parser.add_argument('--fsargs', default='',
                        help=hf('Extra args to give formatter, eg "-E '
                                'lazy_table_init=1".  Make sure fstype matches'
                                ' the args you are passing in'))
    parser.add_argument('--directory', default='/mnt',
                        help='Directory under which to mount devices')
    parser.add_argument('--no-multipath', action='store_true')

    # Resource removal
    parser.add_argument('--logout', action='store_true',
                        help='Logout volumes (implied by --unmount)')
    parser.add_argument('--unmount', action='store_true',
                        help='Unmount volumes only.  Does not delete volume')
    parser.add_argument('--clean', action='store_true',
                        help='Deletes volumes (implies --unmount and '
                             '--logout)')

    # Load generation (no load is run, just load gen config file creation)
    parser.add_argument('--fio', action='store_true',
                        help='Generate fio workload for mounted/logged-in '
                             'volumes')
    parser.add_argument('--fio-workload',
                        help='Fio workload file to use.  If not specified, '
                             'default workload will be used')
    parser.add_argument('--vdbench', action='store_true',
                        help='Generated vdbench workload for mounted/logged-in'
                             ' volumes')

    # Metrics
    parser.add_argument('--metrics', help=hf(
                        'Run metrics with specified report interval and '
                        'timeout in seconds --metrics 5,60 would get metrics '
                        'every 5 seconds for 60 seconds'))
    parser.add_argument('--metrics-type',
                        metavar='',
                        action='append',
                        default=[],
                        choices=METRIC_CHOICES,
                        help=hf('Metric to retrieve.  Choices: {}'.format(
                                json.dumps(METRIC_CHOICES))))
    parser.add_argument('--metrics-op',
                        choices=(None, 'average', 'max', 'min',
                                 'total-average', 'total-max', 'total-min'),
                        help='Operation to perform on metrics data.  For '
                             'example: Averaging the results')
    parser.add_argument('--metrics-out-file', default='metrics-out.json',
                        help='Output file for metrics report.  Use "stdout" to'
                        ' print metrics to STDOUT')

    # Object store helpers
    parser.add_argument('--get-keys', action='store_true',
                        help='Get the object keys for the specified volumes')

    # UDC helpers
    parser.add_argument('--csi-yaml',
                        help='Get UDC config from CSI yaml file.  This makes'
                             ' an assumption that you are running on a k8s'
                             ' master node if the CSI yaml file contains'
                             ' secrets')

    # Misc
    parser.add_argument('--workers', default=5, type=int,
                        help='Number of worker threads for this action')

    args = parser.parse_args()
    sys.exit(main(args))
