#!/usr/bin/env python

from __future__ import unicode_literals, print_function, division

import sys

from dfs_sdk import scaffold

SUCCESS = 0
FAILURE = 1


def main(args):
    # config = scaffold.get_config()
    print("Using Config:")
    scaffold.print_config()
    return SUCCESS


if __name__ == '__main__':
    parser = scaffold.get_argparser()
    args = parser.parse_args()
    sys.exit(main(args))
