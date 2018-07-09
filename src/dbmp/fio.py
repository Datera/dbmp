from __future__ import unicode_literals, print_function, division

import io
import os

from dbmp.mount import get_dirname
from dbmp.utils import ASSETS

FIO_DEFAULT = os.path.join(ASSETS, 'fiotemplate.fio')


def run_fio(vols, fiofile, directory):
    fio = _setup(vols, fiofile, directory)
    print(fio)


def run_fio_remote(vols, fiofile, directory):
    fio = _setup(vols, fiofile, directory)
    print(fio)


def _setup(vols, fiofile, directory):
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
    for ai in vols:
        for si in ai.storage_instance.list():
            for vol in si.volumes.list():
                folder = get_dirname(directory, ai.name, si.name, vol.name)
                _add_directory(fiobase, folder)
    return '\n'.join((elem.strip() for elem in fiobase))


def _add_directory(fiobase, folder, i):
    fiobase.append('\n')
    fiobase.append('[job-{}]'.format(str(i)))
    fiobase.append('directory=/{}'.format(folder.strip('/')))
