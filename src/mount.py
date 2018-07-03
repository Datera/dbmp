from __future__ import unicode_literals, print_function, division

import time

from os_brick.initiator import connector as os_conn
from os_brick import exception as brick_exception

from utils import Parallel


def clean_mounts():
    pass


def clean_mounts_remote(host):
    pass


def mount_volumes(api, vols, multipath):
    funcs, args = [], []
    for ai in vols:
        if len(ai.storage_instances.list()) > 1:
            _mount_complex_volume(ai, multipath)
        else:
            funcs.append(_mount_volume)
            args.append((ai, multipath))
    if funcs:
        p = Parallel(funcs, args_list=args)
        p.run_threads()


def mount_volumes_remote(host, vols, multipath):
    pass


def _mount_complex_volume(ai, multipath):
    pass


def _mount_volume(ai, initiator, multipath):
    ai.set(admin_state='online')
    si = ai.storage_instances.list()[0]
    ac = si.access
    path = login(ac['iqn'], ac['portals'], multipath)
    print("Volume device path:", path)


def setup_acl(api):
    pass


def login(iqn, portals, multipath):
    root_helper = "sudo"
    if not multipath:
        conn = {'driver_volume_type': 'iscsi',
                'data': {
                    'target_discovered': False,
                    'target_iqn': iqn,
                    'target_portal': portals[0],
                    'target_lun': 0}}
    else:
        conn = {'driver_volume_type': 'iscsi',
                'data': {
                    'target_discovered': False,
                    'target_iqns': [iqn, iqn],
                    'target_portals': portals,
                    'target_lun': 0}}
    connector = os_conn.InitiatorConnector.factory(
        'iscsi',
        root_helper,
        use_multipath=multipath,
        enforce_multipath=multipath,
        device_scan_attempts=10,
        conn=conn)
    attach_info = conn['data']
    # Attach Target
    retries = 10
    while True:
        try:
            attach_info.update(
                connector.connect_volume(conn['data']))
            break
        except brick_exception.FailedISCSITargetPortalLogin:
            retries -= 1
            if not retries:
                print("Could not log into portal before end of polling period")
                raise
            print("Failed to login to portal, retrying")
            time.sleep(2)
    return attach_info['device_path']


def logout(iqn, portal, lun):
    root_helper = "sudo"
    conn = {'driver_volume_type': 'iscsi',
            'data': {
                'target_discovered': False,
                'target_iqn': iqn,
                'target_portal': portal,
                'target_lun': lun}}
    connector = os_conn.InitiatorConnector.factory(
        'iscsi',
        root_helper,
        use_multipath=True,
        enforce_multipath=False,
        device_scan_attempts=10,
        conn=conn)
    attach_info = conn['data']
    connector.disconnect_volume(attach_info, attach_info)
