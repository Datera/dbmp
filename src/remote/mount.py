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
    mount_volumes(api)
    return SUCCESS


if __name__ == '__main__':
    parser = scaffold.get_argparser()
    args = parser.parse_args()
    sys.exit(main(args))
