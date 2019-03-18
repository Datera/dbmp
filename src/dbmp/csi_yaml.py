from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import io
import os

import ruamel.yaml as yaml

from dbmp.utils import exe


def _get_from_secret(entry):
    name = entry['valueFrom']['secretKeyRef']['name']
    k = entry['valueFrom']['secretKeyRef']['key']
    value = exe("kubectl get secrets --namespace kube-system {} --template "
                "{{{{.data.{}}}}} | base64 --decode".format(name, k))
    return value


def _process_entries(entries):
    d = {}
    for entry in entries:
        if 'valueFrom' in entry:
            d[entry['name']] = _get_from_secret(entry)
        else:
            d[entry['name']] = entry['value']
    return d


def get_csi_yaml(yaml_file):
    found = {}
    with io.open(yaml_file) as f:
        for d in list(yaml.safe_load_all(f.read())):
            if d.get('kind') == 'DaemonSet':
                for cont in d['spec']['template']['spec']['containers']:
                    if cont.get('name') == 'dat-csi-plugin-node':
                        found['nodes'] = _process_entries(cont['env'])
            if d.get('kind') == 'StatefulSet':
                for cont in d['spec']['template']['spec']['containers']:
                    if cont.get('name') == 'dat-csi-plugin-controller':
                        found['controller'] = _process_entries(cont['env'])
    return found


def udc_envs_from_csi_yaml(yaml_file):
    entries = get_csi_yaml(yaml_file)
    if 'controller' not in entries:
        raise ValueError("Could not parse UDC config from provided yaml "
                         "file: {}".format(yaml_file))
    cont = entries['controller']
    for env in ('DAT_MGMT', 'DAT_USER', 'DAT_PASS', 'DAT_API', 'DAT_TENANT',
                'DAT_LDAP'):
        os.environ[env] = cont.get(env, '')
