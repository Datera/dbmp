from __future__ import unicode_literals, print_function, division

import io
import os
import tempfile
from StringIO import StringIO

from dbmp.utils import ASSETS, exe, putf_remote, rand_file_name, check_install
from dbmp.utils import exe_remote_py

FIO_DEFAULT = os.path.join(ASSETS, 'fiotemplate.fio')


def gen_fio(fiofile, dev_or_folders):
    fio = _setup(fiofile, dev_or_folders)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(fio)
        tf.flush()
        print("Generating FIO job: {}".format(tf.name))
        print("------------------")
        print(fio)


def run_fio_from_file(fiofile):
    print("Running FIO job")
    print(fiofile)
    exe("sudo fio {}".format(fiofile))


def gen_fio_remote(host, vols, fiofile, directory):
    fio = _setup(vols, fiofile, directory)
    fname = rand_file_name('/tmp')
    putf_remote(host, StringIO(fio), fname)
    check_install(host)
    exe_remote_py(
        host,
        'fio.py '
        '--fio-workload {}'.format(fname))


def _setup(fiofile, dev_or_folders):
    fiobase = None
    if not fiofile:
        fiofile = FIO_DEFAULT
    with io.open(fiofile, 'r') as f:
        fiobase = f.readlines()
    found_size = False
    for line in fiobase:
        if 'size' in line:
            found_size = True
            break
    if not found_size:
        fiobase.append('size=1G')
    for df in dev_or_folders:
        fiobase.append('[fio-job]')
        _add_directory(fiobase, df)
    return '\n'.join((elem.strip() for elem in fiobase)) + '\n'


def _add_directory(fiobase, folder):
    if '/dev' in folder:
        fiobase.append('filename=/{}'.format(folder.strip('/')))
    else:
        fiobase.append('directory=/{}'.format(folder.strip('/')))
