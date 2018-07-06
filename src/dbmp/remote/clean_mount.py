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
    clean_mounts(api, args.vols, args.directory, args.workers)
    return SUCCESS


if __name__ == '__main__':
    parser = scaffold.get_argparser()
    parser.add_argument('--vols')
    parser.add_argument('--directory')
    parser.add_argument('--workers', type=int)
    args = parser.parse_args()
    sys.exit(main(args))
