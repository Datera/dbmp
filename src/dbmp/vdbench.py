from __future__ import unicode_literals, print_function, division

import os
import tempfile

TEMPL = "sd={i},lun={path},size=2g,openflags=directio"


def gen_vdb(dev_or_folders):
    vdb = _setup(dev_or_folders)
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(vdb)
        tf.flush()
        print()
        print("Generating vdbench job: {}".format(tf.name))
        print("------------------")
        print(vdb)


def _setup(dev_or_folders):
    entries = []
    for i, d in enumerate(dev_or_folders):
        tfile = os.path.join(d, "testfile.img")
        entries.append(TEMPL.format(i=i+1, path=tfile))
    return "\n".join(entries)
