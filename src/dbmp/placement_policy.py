# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division


# Example --placement-policy "name=all-flash,max=all-flash,min=all-flash"
# Example `--placement-policy \
# "name=flash-write-optimized,max=all-flash;all-flash,min=all-flash;hybrid"`

def parse_ppolicy_opts(p):
    opts = parse_csv_equals(p)
    if 'name' not in opts:
        raise ValueError("--placement-policy requires 'name' argument")
    if 'max' not in opts:
        raise ValueError("--placement-policy requires 'max' argument")
    if not opts.get('min', None):
        opts['min'] = opts['max']
    opts['max'] = ['/media_policy/{}'.format(x)
                   for x in opts['max'].split(';')]
    opts['min'] = ['/media_policy/{}'.format(x)
                   for x in opts['min'].split(';')]
    return opts


def parse_mpolicy_opts(m):
    return parse_csv_equals(m)


def parse_csv_equals(s):
    opts = {}
    parts = s.split(',')
    for part in parts:
        k, v = part.split("=")
        opts[k] = v
    return opts


def create_placement_policy(api, placement_policy):
    opts = parse_ppolicy_opts(placement_policy)
    print("Creating placement policy:", opts['name'])
    pp = api.placement_policies.create(**opts)
    return pp


def delete_placement_policy(api, placement_policy):
    opts = parse_csv_equals(placement_policy)
    pp = api.placement_policies.get(opts['name'])
    return pp.delete()


def list_placement_policies(api):
    pps = api.placement_policies.list()
    for pp in pps:
        print("-------")
        print(pp.name)
        print("\tMax:", ", ".join(pp.max))
        print("\tMin:", ", ".join(pp.min))


def create_media_policy(api, media_policy):
    opts = parse_mpolicy_opts(media_policy)
    print("Creating media policy:", opts['name'])
    mp = api.media_policies.create(**opts)
    return mp


def delete_media_policy(api, media_policy):
    opts = parse_csv_equals(media_policy)
    mp = api.media_policies.get(opts['name'])
    return mp.delete()


def list_media_policies(api):
    mps = api.media_policies.list()
    for mp in mps:
        print("-------")
        print(mp.name)
        print("\tPriority:", mp.priority)
