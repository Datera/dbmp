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
INTERACTIVEPY = os.path.join(DIR, "src", "dbmp", "interactive.py")
DBMPPY = os.path.join(DIR, "src", "dbmp", "main.py")
CONFIG = os.path.join(DIR, "datera-config.json")
DBMP_TEMPLATE = """
#!/bin/bash

if [[ $1 =~ .*interactive.* ]]
then
    # dbmp interactive needs to know which python
    # virtualenv to use
    shift
    {python} {interactive} "{python} {dbmp}" $@
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


def install_packages():
    # Install prereqs Ubuntu
    try:
        exe("sudo apt-get install python-virtualenv python-dev "
            "libffi-dev libssl-dev gcc -y")
    # Install prereqs Centos
    except subprocess.CalledProcessError as e:
        vprint(e)
        print("Ubuntu packages failed, trying RHEL packages")
        try:
            exe("sudo yum install python-virtualenv python-devel "
                "libffi-devel openssl-devel gcc -y")
        except subprocess.CalledProcessError as e:
            vprint(e)
            print("RHEL packages failed, trying SUSE packages")
            try:
                exe("sudo zypper install -y python-setuptools libffi-devel "
                    "python-curses gcc")
                # For some reason this has to be a separate call
                exe("sudo zypper install -y python-devel")
            except subprocess.CalledProcessError as e:
                vprint(e)
                print("SUSE packages failed")
                print("Could not install prereqs")
                return 1


def install_virtualenv_from_source():
    if not os.path.exists("pypa-virtualenv-3272f7b"):
        exe("curl --location --output virtualenv-16.4.3.tar.gz "
            "https://github.com/pypa/virtualenv/tarball/16.4.3")
        exe("tar zxvf virtualenv-16.4.3.tar.gz")
    exe("python pypa-virtualenv-3272f7b/virtualenv.py .dbmp")


def main(args):
    global VERBOSE
    VERBOSE = not args.quiet
    try:
        exe("which virtualenv")
    except subprocess.CalledProcessError:
        if install_packages() == 1:
            return 1
    if not os.path.isdir(VENV):
        try:
            exe("virtualenv {}".format(VENV))
        except subprocess.CalledProcessError:
            # Sometimes this fails because python-setuptools isn't installed
            # this almost always happens on SUSE, but we'll install all
            # necessary packages just to be safe.
            if install_packages() == 1:
                return 1
            install_virtualenv_from_source()
    exe_pip("install -U pip")
    exe_pip("install -U -r {}".format(REQUIREMENTS))
    exe_pip("install -e {}".format(DIR))

    if not os.path.isfile(DBMP):
        # Create dbmp executable
        with io.open(DBMP, 'w+') as f:
            f.write(DBMP_TEMPLATE.format(
                python=PYTHON,
                dbmp=DBMPPY,
                interactive=INTERACTIVEPY))
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
        print("DBMP is now installed.  Use '{dbmp}' to run DBMP."
              "If you would like to run DBMP in 'interactive' mode, use"
              "'{dbmp} --interactive' with no other arguments".format(
                  dbmp=DBMP))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--gen-config",
                        help="Generate Datera Universal Config file after "
                             "install")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()
    sys.exit(main(args))
