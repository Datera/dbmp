from __future__ import unicode_literals, print_function, division

import glob
import os
import time
import sys
import re

from dfs_sdk import exceptions as dat_exceptions

from dbmp.volume import ais_from_vols, parse_vol_opt
from dbmp.utils import Parallel, exe
from dbmp.utils import get_hostname, dprint, locker

DEV_TEMPLATE = "/dev/disk/by-path/ip-{ip}:3260-iscsi-{iqn}-lun-{lun}"

# Py 2/3 compat
try:
    input = raw_input
except NameError:
    pass


def clean_mounts(api, vols, directory, workers):
    ais = ais_from_vols(api, vols)
    funcs, args = [], []
    for ai in ais:
        for si in ai.storage_instances.list():
            iqn = si.access.get('iqn')
            dprint("Cleaning {},{} portals {}, iqn {}".format(
                ai.name, si.name, si.access['ips'], si.access.get('iqn')))
            if not iqn:
                dprint("{},{} did not have an iqn field".format(
                    ai.name, si.name))
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
        dprint(e)
        return
    exe("sudo rmdir {}".format(folder))


def mount_volumes(api, vols, multipath, fs, fsargs, directory, workers,
                  login_only, force_init, initiator_path):
    funcs, args = [], []
    results = []
    for ai in vols:
        funcs.append(_mount_volume)
        args.append((api, ai, multipath, fs, fsargs, directory, login_only,
                     results, force_init, initiator_path))
    if funcs:
        p = Parallel(funcs, args_list=args, max_workers=workers)
        p.run_threads()
    return results


def get_dirname(directory, ai_name, si_name, vol_name):
    return os.path.join(directory, "-".join((ai_name, si_name, vol_name)))


def _mount_volume(api, ai, multipath, fs, fsargs, directory, login_only,
                  results, force_init, initiator_path):
    _setup_acl(api, ai, force_init, initiator_path)
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
            dprint("Checking for existing filesystem on:", path)
            try:
                out = exe(
                    "sudo blkid {} | grep -Eo '(TYPE=\".*\")'".format(
                        path))
                parts = out.split("=")
                if len(parts) == 2:
                    found_fs = parts[-1].lower().strip().strip('"')
                    if found_fs == fs.lower():
                        dprint("Found existing filesystem, continuing")
                        break
            except EnvironmentError:
                pass
            dprint("Failed to format {}. Waiting for device to be "
                   "ready".format(path))
            if not timeout:
                raise
            time.sleep(1)
            timeout -= 1
    exe("sudo mkdir -p /{}".format(folder.strip("/")))
    exe("sudo mount {} {}".format(path, folder))
    print("Volume mount:", folder)


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
        dprint("Could not find the iSCSI Initiator File %s", file_path)
        raise


@locker
def _setup_initiator(api, force):
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
            raise dat_exceptions.ApiNotFoundError(msg="Non matching tenant")
    except dat_exceptions.ApiNotFoundError:
        try:
            initiator_obj = api.initiators.create(
                name=host, id=initiator, force=force)
        except dat_exceptions.ApiInvalidRequestError:
            try:
                initiator_obj = api.initiators.create(name=host, id=initiator)
            except dat_exceptions.ApiInvalidRequestError as e:
                if "override this warning" in str(e) and not force:
                    out = input(
                            "First initiator within a tenant needs to be "
                            "force created. Would you like to do so? "
                            "[Y/n]: ").strip()
                    if out in ("Y", "y"):
                        initiator_obj = api.initiators.create(
                            name=host, id=initiator, force=True)
                    else:
                        print("Exiting due to failed initiator creation")
                        sys.exit(1)
                else:
                    raise
    return initiator_obj


def _setup_acl(api, ai, force_init, initiator_path):
    if initiator_path == 'local':
        initiatorObj = _setup_initiator(api, force_init)
	      initiator = initiatorObj.path
    else:
        initiator = initiator_path
    #Check to see if the initiator is group to use the right api call
    if re.match(".*groups.*",initiator):
        for si in ai.storage_instances.list():
            try:
                si.acl_policy.initiator_groups.add(initiator)
            except dat_exceptions.ApiConflictError:
                dprint("ACL Group already registered for {},{}".format(ai.name, si.name))
    else:
        for si in ai.storage_instances.list():
            try:
                si.acl_policy.initiators.add(initiator)
            except dat_exceptions.ApiConflictError:
                dprint("ACL already registered for {},{}".format(ai.name, si.name))
        dprint("Setting up ACLs for {} targets".format(ai.name))



def _get_multipath_disk(path):
    # Follow link to destination directory
    try:
        device_path = os.readlink(path)
    except OSError as e:
        dprint("Error reading link: {}. error: {}".format(path, e))
        return
    sdevice = os.path.basename(device_path)
    # If destination directory is already identified as a multipath device,
    # just return its path
    if sdevice.startswith("dm-"):
        return path
    # Fallback to iterating through all the entries under /sys/block/dm-* and
    # check to see if any have an entry under /sys/block/dm-*/slaves matching
    # the device the symlink was pointing at
    timeout = 10
    while timeout > 0:
        dmpaths = glob.glob("/sys/block/dm-*")
        for dmpath in dmpaths:
            sdevices = glob.glob(os.path.join(dmpath, "slaves", "*"))
            for spath in sdevices:
                s = os.path.basename(spath)
                if sdevice == s:
                    # We've found a matching entry, return the path for the
                    # dm-* device it was found under
                    p = os.path.join("/dev", os.path.basename(dmpath))
                    dprint("Found matching device: {} under dm-* device path "
                           "{}".format(sdevice, dmpath))
                    return p
        timeout -= 1
        time.sleep(1)
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
            dprint("Waiting for device to be ready:", path)
            time.sleep(1)
        dprint("Setting noop scheduler for device:", device)
        exe("echo 'noop' | sudo tee /sys/block/{}/queue/scheduler".format(
            device))


def _login(iqn, portals, multipath, lun):
    retries = 10
    if not multipath:
        portals = [portals[0]]
    if lun == 0:
        for portal in portals:
            while True:
                dprint("Trying to log into target:", portal)
                try:
                    exe("sudo iscsiadm -m discovery -t st -p {}:3260".format(
                        portal))
                    exe("sudo iscsiadm -m node -T {iqn} -p {ip}:3260 "
                        "--login".format(iqn=iqn, ip=portal))
                    break
                except EnvironmentError as e:
                    if 'returned non-zero exit status 15' in str(e):
                        break
                    retries -= 1
                    if not retries:
                        dprint("Could not log into portal before end of "
                               "polling period")
                        raise
                    dprint("Failed to login to portal, retrying")
                    time.sleep(2)
    _set_noop_scheduler(portals, iqn, lun)
    path = DEV_TEMPLATE.format(ip=portals[0], iqn=iqn, lun=lun)
    if multipath:
        dprint('Sleeping to allow for multipath devices to finish linking')
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
    dprint("Sleeping to wait for logout")
    time.sleep(2)
    dprint("Logout complete")


def list_mounts(host, api, vopt, detail, multipath):
    opts = parse_vol_opt(vopt)
    hostname = get_hostname(host)
    if detail:
        print("\nMOUNTS-DETAIL")
        print("-------------")
    else:
        print("\nMOUNTS")
        print("------")
    for ai in sorted(api.app_instances.list(), key=lambda x: x.name):
        if (opts.get('prefix') == 'all' or
                opts.get('name') == ai.name or
                ai.name.startswith(opts.get('prefix', hostname))):
            for si in ai.storage_instances.list():
                for i, vol in enumerate(si.volumes.list()):
                    mount, path, device = _find_mount(ai, si, i, multipath)
                    if mount and detail:
                        print(",".join((ai.name, si.name, vol.name)),
                              ":", mount, ":", path, ":", device)
                    elif mount:
                        print(",".join((ai.name, si.name, vol.name)),
                              ":", mount)


def _find_mount(ai, si, lun, multipath):
    ip = si.access['ips'][0]
    iqn = si.access['iqn']
    path = DEV_TEMPLATE.format(ip=ip, iqn=iqn, lun=lun)
    if multipath:
        path = _get_multipath_disk(path)
    out = exe("ls -l {} | awk '{{print $NF}}'".format(path))
    device = out.split("/")[-1].strip()
    if not device:
        return None, path, device
    mount = exe("cat /proc/mounts | grep {} | awk '{{print $2}}'".format(
        device))
    return mount.strip(), path, device
