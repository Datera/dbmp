from __future__ import unicode_literals, print_function, division

import glob
import os
import time

from dfs_sdk import exceptions as dat_exceptions

from dbmp.volume import ais_from_vols
from dbmp.utils import Parallel, exe, check_install, exe_remote_py

DEV_TEMPLATE = "/dev/disk/by-path/ip-{ip}:3260-iscsi-{iqn}-lun-{lun}"


def mount_volumes_remote(host, vols, multipath, fs, fsargs, directory,
                         workers, login_only):
    check_install(host)
    m = '--multipath' if multipath else ''
    vs = ','.join([v.name for v in vols])
    fa = '"{}"'.format(fsargs)
    lo = '--login-only' if login_only else ''
    exe_remote_py(
        host,
        'mount.py '
        '--vols {} '
        '{} '
        '--fs {} '
        '--fsargs {} '
        '--directory {} '
        '--workers {} '
        '{}'.format(vs, m, fs, fa, directory, workers, lo))


def clean_mounts_remote(host, vols, directory, workers):
    check_install(host)
    exe_remote_py(
        host,
        'clean_mount.py '
        '--vols {} '
        '--directory {} '
        '--workers {}'.format(vols, directory, workers))


def clean_mounts(api, vols, directory, workers):
    ais = ais_from_vols(api, vols)
    funcs, args = [], []
    for ai in ais:
        for si in ai.storage_instances.list():
            iqn = si.access.get('iqn')
            if not iqn:
                continue
            portals = si.access['ips']
            for vol in si.volumes.list():
                _unmount(ai.name, si.name, vol.name, directory)
            funcs.append(_logout)
            args.append((iqn, portals))
    if funcs:
        p = Parallel(funcs, args_list=args)
        p.run_threads()


def _unmount(ai_name, si_name, vol_name, directory):
    folder = get_dirname(directory, ai_name, si_name, vol_name)
    try:
        exe("sudo umount {}".format(folder))
    except EnvironmentError as e:
        print(e)
        return
    exe("sudo rmdir {}".format(folder))


def mount_volumes(api, vols, multipath, fs, fsargs, directory, workers,
                  login_only):
    funcs, args = [], []
    results = []
    for ai in vols:
        funcs.append(_mount_volume)
        args.append((api, ai, multipath, fs, fsargs, directory, login_only,
                     results))
    if funcs:
        p = Parallel(funcs, args_list=args, max_workers=workers)
        p.run_threads()
    return results


def get_dirname(directory, ai_name, si_name, vol_name):
    return os.path.join(directory, "-".join((ai_name, si_name, vol_name)))


def _mount_volume(api, ai, multipath, fs, fsargs, directory, login_only,
                  results):
    _setup_acl(api, ai)
    ai.set(admin_state='online')
    for si in ai.storage_instances.list():
        _si_poll(si)
        si = si.reload()
        ac = si.access
        for i, vol in enumerate(si.volumes.list()):
            path = _login(ac['iqn'], ac['ips'], multipath, i)
            if login_only:
                results.append(path)
            print("Volume device path:", path)
            if not login_only:
                folder = get_dirname(directory, ai.name, si.name, vol.name)
                results.append(folder)
                _format_mount_device(path, fs, fsargs, folder)


def _format_mount_device(path, fs, fsargs, folder):
    timeout = 5
    while True:
        try:
            exe("sudo mkfs.{} {} {} ".format(fs, fsargs, path))
            break
        except EnvironmentError:
            print("Checking for existing filesystem on:", path)
            try:
                out = exe(
                    "sudo blkid {} | grep -Eo '(TYPE=\".*\")'".format(
                        path))
                parts = out.split("=")
                if len(parts) == 2:
                    found_fs = parts[-1].lower().strip().strip('"')
                    if found_fs == fs.lower():
                        print("Found existing filesystem, continuing")
                        break
            except EnvironmentError:
                pass
            print("Failed to format {}. Waiting for device to be ready".format(
                path))
            if not timeout:
                raise
            time.sleep(1)
            timeout -= 1
    exe("sudo mkdir -p /{}".format(folder.strip("/")))
    exe("sudo mount {} {}".format(path, folder))


def _si_poll(si):
    timeout = 10
    while True:
        si = si.reload()
        if si.op_state == 'available':
            break
        if not timeout:
            raise EnvironmentError(
                "Polling ended before storage_instance {} was still "
                "unavailable".format(si.path))
        time.sleep(1)
        timeout -= 1


def _get_initiator():
    file_path = '/etc/iscsi/initiatorname.iscsi'
    try:
        out = exe('sudo cat {}'.format(file_path))
        for line in out.splitlines():
            if line.startswith('InitiatorName='):
                return line.split("=", 1)[-1].strip()
    except EnvironmentError:
        print("Could not find the iSCSI Initiator File %s", file_path)
        raise


def _setup_acl(api, ai):
    initiator = _get_initiator()
    host = exe('hostname').strip()
    initiator_obj = None
    try:
        initiator_obj = api.initiators.get(initiator)
        # Handle case where initiator exists in parent tenant
        # We want to create a new initiator in the case
        tenant = api.context.tenant
        if not tenant:
            tenant = '/root'
        if initiator_obj.tenant != tenant:
            raise dat_exceptions.ApiNotFoundError()
    except dat_exceptions.ApiNotFoundError:
        initiator_obj = api.initiators.create(name=host, id=initiator)
    for si in ai.storage_instances.list():
        try:
            si.acl_policy.initiators.add(initiator_obj)
        except dat_exceptions.ApiConflictError:
            print("ACL already registered for {},{}".format(ai.name, si.name))
    print("Setting up ACLs for {} targets".format(ai.name))


def _get_multipath_disk(path):
    # Follow link to destination directory
    try:
        device_path = os.readlink(path)
    except OSError as e:
        print("Error reading link: {}. error: {}".format(path, e))
        return
    sdevice = os.path.basename(device_path)
    # If destination directory is already identified as a multipath device,
    # just return its path
    if sdevice.startswith("dm-"):
            return path
    # Fallback to iterating through all the entries under /sys/block/dm-* and
    # check to see if any have an entry under /sys/block/dm-*/slaves matching
    # the device the symlink was pointing at
    dmpaths = glob.glob("/sys/block/dm-*")
    for dmpath in dmpaths:
        sdevices = glob.glob(os.path.join(dmpath, "slaves", "*"))
        for spath in sdevices:
            s = os.path.basename(spath)
            if sdevice == s:
                # We've found a matching entry, return the path for the
                # dm-* device it was found under
                p = os.path.join("/dev", os.path.basename(dmpath))
                print("Found matching device: {} under dm-* device path "
                      "{}".format(sdevice, dmpath))
                return p
    raise EnvironmentError(
        "Couldn't find dm-* path for path: {}, found non dm-* path: {}".format(
            path, device_path))


def _set_noop_scheduler(portals, iqn, lun):
    for portal in portals:
        path = DEV_TEMPLATE.format(ip=portal, iqn=iqn, lun=lun)
        device = None
        while True:
            out = exe("ls -l {} | awk '{{print $NF}}'".format(path))
            device = out.split("/")[-1].strip()
            if device:
                break
            print("Waiting for device to be ready:", path)
            time.sleep(1)
        print("Setting noop scheduler for device:", device)
        exe("echo 'noop' | sudo tee /sys/block/{}/queue/scheduler".format(
            device))


def _login(iqn, portals, multipath, lun):
    retries = 10
    if not multipath:
        portals = [portals[0]]
    if lun == 0:
        for portal in portals:
            while True:
                print("Trying to log into target:", portal)
                try:
                    exe("sudo iscsiadm -m discovery -t st -p {}:3260".format(
                        portal))
                    exe("sudo iscsiadm -m node -T {iqn} -p {ip}:3260 "
                        "--login".format(iqn=iqn, ip=portal))
                    break
                except EnvironmentError:
                    retries -= 1
                    if not retries:
                        print("Could not log into portal before end of "
                              "polling period")
                        raise
                    print("Failed to login to portal, retrying")
                    time.sleep(2)
    _set_noop_scheduler(portals, iqn, lun)
    path = DEV_TEMPLATE.format(ip=portals[0], iqn=iqn, lun=lun)
    if multipath:
        print('Sleeping to allow for multipath devices to finish linking')
        time.sleep(2)
        dpath = _get_multipath_disk(path)
    else:
        dpath = path
    return dpath


def _logout(iqn, portals):
    for portal in portals:
        exe("sudo iscsiadm -m node -T {iqn} -p {ip}:3260 --logout".format(
            iqn=iqn, ip=portal), fail_ok=True)
        exe("sudo iscsiadm -m node -T {iqn} -p {ip}:3260 --op delete".format(
            iqn=iqn, ip=portal), fail_ok=True)
        exe("sudo iscsiadm -m discoverydb -p {ip}:3260 --op delete".format(
            ip=portal),
            fail_ok=True)
    exe("sudo iscsiadm -m session --rescan", fail_ok=True)
    exe("sudo multipath -F", fail_ok=True)
    print("Sleeping to wait for logout")
    time.sleep(2)
    print("Logout complete")
