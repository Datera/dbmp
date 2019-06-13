# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division

from dfs_sdk import exceptions as dat_exceptions

ROLES = 'roles'
WEIRD = {'system', 'init'}


def at_url(api, resource):
    parts = [x for x in resource.split("/") if x]
    n = api
    if parts[0] in WEIRD:
        for part in parts:
            n = getattr(n, part)
        n = n.get()
    else:
        for part, resource in zip(parts[::2], parts[1::2]):
            if part:
                try:
                    n = getattr(n, part).get(resource)
                except dat_exceptions.ApiError:
                    return ""
    if parts[0] == ROLES:
        attr = 'role_id'
    else:
        attr = 'name'
    print()
    if len(parts) % 2 == 1 and parts[0] not in WEIRD:
        print('{:<30} {}'.format('Name', 'Path'))
        print('{:<30} {}'.format('--------', '--------'))
        for name, path in sorted([(getattr(elem, attr), elem.path)
                                  for elem in getattr(n, parts[-1]).list()]):
            print('{:<30} {}'.format(name, path))
    elif parts[0] in WEIRD:
        print(resource)
        print('--------')
        print(n)
    else:
        try:
            print(n['name'])
        except KeyError:
            try:
                print(n['id'])
            except KeyError:
                print(n['role_id'])

        print('--------')
        print(n)
    print('--------')
