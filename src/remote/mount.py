#!/usr/bin/env python

import sys

from dfs_sdk import scaffold

from mount import mount_volumes

SUCCESS = 0
FAILURE = 1


def main(args):
    api = scaffold.get_api()
    print('Using Config:')
    scaffold.print_config()
    ais = []
    for v in args.vols.split(','):
        ais.append(api.app_instances.get(v))
    mount_volumes(api, args.vols, args.multipath, args.fs, args.fsargs,
                  args.directory, args.workers)
    return SUCCESS


if __name__ == '__main__':
    parser = scaffold.get_argparser()
    parser.add_argument('--vols')
    parser.add_argument('--multipath')
    parser.add_argument('--fs')
    parser.add_argument('--fsargs')
    parser.add_argument('--directory')
    parser.add_argument('--workers')
    args = parser.parse_args()
    sys.exit(main(args))
