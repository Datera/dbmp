#!/usr/bin/env python3

from __future__ import unicode_literals, print_function, division

import argparse
import io
import os
import stat
import subprocess
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(DIR, ".dbmp")
PYTHON = os.path.join(VENV, "bin", "python")
PIP = os.path.join(VENV, "bin", "pip")
REQUIREMENTS = os.path.join(DIR, "requirements.txt")
DBMP = os.path.join(DIR, "dbmp")
DBMPPY = os.path.join(DIR, "src", "dbmp", "main.py")
CONFIG = os.path.join(DIR, "datera-config.json")
DBMP_TEMPLATE = """
#!/bin/bash

if [[ $1 =~ .*interactive.* ]]
then
    # dbmp interactive needs to know which python
    # virtualenv to use
    {python} {interactive} "{python} {dbmp}"
else
    {python} {dbmp} $@
fi
"""

VERBOSE = False


def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


def exe(cmd):
    vprint("Running cmd:", cmd)
    return subprocess.check_output(cmd, shell=True)


def exe_pip(cmd):
    vprint("Running pip cmd:", cmd)
    cmd = " ".join((PIP, cmd))
    return subprocess.check_output(cmd, shell=True)


def exe_python(cmd):
    vprint("Running python cmd:", cmd)
    cmd = " ".join((PYTHON, cmd))
    return subprocess.check_output(cmd, shell=True)


def main(args):
    global VERBOSE
    VERBOSE = not args.quiet
    try:
        exe("which virtualenv")
    except subprocess.CalledProcessError:
        # Install prereqs Ubuntu
        try:
            exe("sudo apt-get update")
            exe("sudo apt-get install python-virtualenv python-dev "
                "libffi-dev libssl-dev -y")
        # Install prereqs Centos
        except subprocess.CalledProcessError as e:
            vprint(e)
            print("Ubuntu packages failed, trying RHEL packages")
            try:
                exe("sudo yum install python-virtualenv python-devel "
                    "libffi-devel openssl-devel -y")
            except subprocess.CalledProcessError as e:
                print(e)
                print("RHEL packages failed")
                print("Could not install prereqs")
                return 1
    if not os.path.isdir(VENV):
        exe("virtualenv {}".format(VENV))
    exe_pip("install -U pip")
    exe_pip("install -U -r {}".format(REQUIREMENTS))
    exe_pip("install -e {}".format(DIR))

    if not os.path.isfile(DBMP):
        # Create dbmp executable
        with io.open(DBMP, 'w+') as f:
            f.write(DBMP_TEMPLATE.format(
                python=PYTHON,
                dbmp=DBMPPY))
        # Ensure it is executable
        st = os.stat(DBMP)
        os.chmod(DBMP, st.st_mode | stat.S_IEXEC)

    if not os.path.isfile(CONFIG) and args.gen_config:
        exe("cd {} && {} --gen-config json".format(DIR, DBMP))
        print("DBMP is now installed.  Use '{}' to run DBMP."
              "\nThe generated config file is located at '{}'. "
              "\nIf an existing universal datera config file should be "
              "used, remove the generated config file".format(
                  DBMP, CONFIG))
    else:
        print("DBMP is now installed.  Use '{}' to run DBMP.".format(DBMP))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--gen-config",
                        help="Generate Datera Universal Config file after "
                             "install")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()
    sys.exit(main(args))
