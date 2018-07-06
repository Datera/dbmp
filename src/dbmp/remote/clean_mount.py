#!/usr/bin/env python

import sys

from dfs_sdk import scaffold

from dbmp.mount import clean_mounts

SUCCESS = 0
FAILURE = 1


def main(args):
    api = scaffold.get_api()
    print('Using Config:')
    scaffold.print_config()
    ais = []
    for v in args.vols.split(','):
        ais.append(api.app_instances.get(v))
    clean_mounts(api, ais, args.workers)
    return SUCCESS


if __name__ == '__main__':
    parser = scaffold.get_argparser()
    parser.add_argument('--vols')
    parser.add_argument('--workers', type=int)
    args = parser.parse_args()
    sys.exit(main(args))
