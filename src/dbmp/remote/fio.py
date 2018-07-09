#!/usr/bin/env python

import os
import sys

from dfs_sdk import scaffold

from dbmp.fio import run_fio_from_file

SUCCESS = 0
FAILURE = 1


def main(args):
    run_fio_from_file(args.fio_workload)
    os.remove(args.fio_workload)
    return SUCCESS


if __name__ == '__main__':
    parser = scaffold.get_argparser()
    parser.add_argument('--fio-workload')
    args = parser.parse_args()
    sys.exit(main(args))
