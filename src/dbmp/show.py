# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division

from dfs_sdk import exceptions as dat_exceptions


def at_url(api, resource):
    parts = [x for x in resource.split("/") if x]
    n = api
    for part, resource in zip(parts[::2], parts[1::2]):
        if part:
            try:
                n = getattr(n, part).get(resource)
            except dat_exceptions.ApiError:
                return ""
    print('--------')
    if len(parts) % 2 == 1:
        for name, path in sorted([(elem.name, elem.path)
                                  for elem in getattr(n, parts[-1]).list()]):
            print('{:<30} {}'.format(name, path))
    else:
        print(n)
    print('--------')
