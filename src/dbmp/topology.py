from __future__ import unicode_literals, print_function, division

import io
import json

from dfs_sdk import scaffold

_TOPOLOGY = {}
TFILE = 'dbmp-topology.json'


def read_topology_file(tfile):
    with io.open(tfile) as f:
        return json.loads(f.read())


def get_topology(host):
    global _TOPOLOGY
    if host == 'local':
        return 'local'
    if not _TOPOLOGY:
        config = scaffold.get_config()
        if 'topology' in config:
            _TOPOLOGY = config['topology']
        elif host != 'local':
            _TOPOLOGY = read_topology_file(TFILE)
    if host != 'local' and not _TOPOLOGY:
        raise EnvironmentError(
            "Non-local host specified, but no topology file found")
    if host not in _TOPOLOGY:
        raise EnvironmentError(
            "Unrecognized host: {}.  Check topology file".format(host))
    top = _TOPOLOGY[host]
    user, back = top.split('@')
    ip, creds = back.split(':')
    return user, ip, creds


def print_hosts():
    for h, p in _TOPOLOGY.items():
        p = ":".join(p.split(":")[0], "********")
        print(h, "-->", p)
