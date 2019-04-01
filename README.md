# DBMP (Datera Bare-Metal Provisioner)

## What For?

When running workloads against the Datera system, it often takes many steps and
familiarity with the Datera interface to get a simple volume up and running
with a workload.  If you live your life in the CLI and don't want to memorize
the REST API calls necessary to get this done or don't feel like rolling your
own with our Python-SDK (wink-wink, nudge-nudge :) ), then this package was
made for you!

## What Do?

* Install prerequistes
    - Install ``python``
    - Install ``git``
    - Install ``open-iscsi`` (we need ``iscsiadm``)
    - Install ``multipath-tools`` (or whatever it is on your system)
    - Install ``mkfs.<your_favorite_format>``
    - Install ``fio`` (make sure it's accessible via $PATH)
* Clone the repository
    - ``git clone http://github.com/Datera/dbmp``
    - ``cd dbmp``
* Install
    - ``./install.py``
* Create Datera Universal Config File
    - ``vi datera-config.json``
    ```json
    {
        "username": "your_user",
        "password": "your_password",
        "tenant": "/root",
        "mgmt_ip": "1.1.1.1",
        "api_version": "2.2"
    }
    ```
* Use
    - ``./dbmp --help``

## What Really Do?

Functionality can be broken down into a few categories

* Health Check
* List Resources
* Simple Creation
* Complex Creation
* Deletion
* Login/Logout
* Mount/Unmount
* Load Generation
* Metrics

### Creation

DBMP can create and delete Datera volumes via a simple CLI interface.

Example:

```bash
$ ./dbmp --volume size=5,prefix=my-vol,placement_mode=single_flash,replica=2,count=3,read_iops_max=500
```
In the above example we are requesting a set of volumes with the following
attributes:

* Size In GB (size=5)
* Name Prefix (prefix=my-vol)
* Volume Placement Mode (placement\_mode=single\_flash) (choices hybrid|single\_flash|all\_flash)
* Number Of Replicas (replicas=2)
* Total Number Of Volumes (count=3)
* QoS Read IOPS Max (read\_iops\_max=500)


This will give us the following App Instances on the Datera side each with a
single Storage Instance with a single Volume

* my-vol-1
* my-vol-2
* my-vol-3

All attributes are optional and have the following default values:

* size=1
* prefix=$(hostname)
* count=1
* replica=3
* placement\_mode=hybrid
* placement\_policy=None (This references the name attribute of the policy, eg: `all-flash`)
* template=None
* read\_iops\_max=0
* write\_iops\_max=0
* total\_iops\_max=0
* read\_bw\_max=0
* write\_bw\_max=0
* total\_bw\_max=0

**NOTE: placement\_policy will override placement\_mode**

### Complex Creation

Complex App Instance creation is accessed via a JSON file with the following
structure:

```json
{
    "name": "complex-app",
    "sis": [
        {"name": "storage-1",
         "vols": [
             {"name": "volume-1",
              "size": 5,
              "replica": 3,
              "placement_mode": "hybrid",
              "qos": {}},
             {"name": "volume-2",
              "size": 10,
              "replica": 3,
              "placement_mode": "hybrid",
              "qos": {}}
         ]},
        {"name": "storage-2",
         "vols": [
             {"name": "volume-3",
              "size": 15,
              "replica": 2,
              "placement_mode": "hybrid",
              "qos": {"total_iops_max": 300}},
             {"name": "volume-4",
              "size": 20,
              "replica": 2,
              "placement_mode": "hybrid",
              "qos": {"total_iops_max": 500}}
         ]}
    ]
}
```

In the above example I've specified an App Instance with the following:
    * An App Instance with the name "complex-app"
    * 2 Storage Instances (storage-1 and storage-2)
    * 4 Volumes / 2 per Storage Instance (volume-1, volume-2, volume-3, volume-4)
    * Differing attributes for each volume

Once the JSON file is constructed you can create the complex volume like this:

```bash
$ ./dbmp --volume my-complex-vol.json
```

### Deletion

Removal of the above volumes is even simpler

```bash
$ ./dbmp --volume prefix=my-vol --clean
```

Or in the case of a complex volume

```bash
$ ./dbmp --volume my-complex-vol.json --clean
```
### Login/Logout

Login and Logout is the same as creation/deletion but you add the `--login``
and ``--logout`` flags (``-clean`` implies logout, and ``--mount/--unmount``
implies login/logout)

When logging in without ``--mount``, all operations afterwards (such as FIO)
will be referring to the raw device directly.  No filesystem will be created
and the device will not be mounted.

### Mount/Unmount

Mounting and Unmounting is the same as creation/deletion but you add the
``--mount`` and ``--unmount`` flags (``--clean`` implies unmount)

The Directory under which mounts should live is specified via the
``--directory`` flag

Volumes will be mounted under the following name scheme:
``/<directory>/<ai_name>/<si_name>/<vol_name>`` which means a normal CLI
specified volume with ``prefix=my-vol`` and ``--directory=/mnt`` will be
located at ``/mnt/my-vol-storage-1-volume-1``

Complex Volumes will follow the same scheme, but as their Storage Instance
and Volume names are customizeable, you'll need to consult their JSON schemas
to determine their mount locations.  The complex volume example shown above
would have mounts in the following locations

* /mnt/complex-app-storage-1-volume-1
* /mnt/complex-app-storage-1-volume-2
* /mnt/complex-app-storage-2-volume-3
* /mnt/complex-app-storage-2-volume-4


### Load Generation

You can have DBMP generate an FIO file against all created mounts (or devices)
via by adding ``--fio`` to the invocation.

```bash
$ ./dbmp --volume my-complex-vol.json --mount --fio
```

The default FIO profile is the following:

```
[global]
randrepeat=0
ioengine=libaio
iodepth=16
direct=1
numjobs=4
runtime=3600
group_reporting
time_based
size=1G

[job-1]
directory=/your_mount
```

An entry for every mount created will be placed under [job-1].  The complex
volume example above would have the following FIO job generated:

```
[global]
randrepeat=0
ioengine=libaio
iodepth=16
direct=1
numjobs=4
runtime=3600
group_reporting
time_based
size=1G

[job-1]
directory=/mnt/complex-app-storage-1-volume-1
[job-1]
directory=/mnt/complex-app-storage-1-volume-2
[job-1]
directory=/mnt/complex-app-storage-2-volume-3
[job-1]
directory=/mnt/complex-app-storage-2-volume-4
```

If the ``--mount`` flag has not been passed in, then instead of "directory",
"filename" will be used with the device

To specify your own FIO workload, use the ``--fio-workload`` flag.  Your
workload MUST only have a [global] section

### Metrics

Metrics can be viewed for any volume created by DBMP using the following
invocation

```bash
$ ./dbmp --volume prefix=my-vol,count=1 --metrics 5,20
```

Example Output:

```json
{
    "test-vol-0": {
        "iops_write": [
            {
                "value": 110,
                "time": 1532722856000
            },
            {
                "value": 88,
                "time": 1532722860000
            },
            {
                "value": 102,
                "time": 1532722866000
            },
            {
                "value": 101,
                "time": 1532722870000
            }
        ]
    }
}
```

The ``--metrics`` flag takes two comma separated values: ``interval,timeout``
which correspond to the interval between metric update calls and the timeout
before metric calls should end respectively.

By default the metric will be ``iops_write``, but you can change this using
the ``--metrics-type`` flag.  The available choices are below:

* reads
* writes
* bytes\_read,
* bytes\_written
* iops\_read
* iops\_write,
* thpt\_read
* thpt\_write
* lat\_avg\_read,
* lat\_avg\_write
* lat\_50\_read
* lat\_90\_read,
* lat\_100\_read
* lat\_50\_write,
* lat\_90\_write
* lat\_100\_write

Multiple of these can be specified by repeating the ``--metrics-type`` flag

Output can be controlled via the ``--metrics-out-file`` flag.  This just takes
a string specifying where the metrics should be saved.  The default is
``metrics-out.json``.  Use the string ``'stdout'`` to force metrics to be
printed to STDOUT instead of a file.

Basic operations can be performed on the data via the ``--metrics-op`` flag.
The following operations are currently supported (on a per-metric basis)

* None
* average
* max
* min
* total-average (for all app\_instances)
* total-max (for all app\_instances)
* total-min (for all app\_instances)

The output format will change depending on the operation and the original data
is NOT preserved.


## What Problem?

* File an issue on the github page
* Contact us at support@datera.io

## What Interactive?

NOTE: This is a WIP

```bash
$ ./dbmp --interactive
```
In every screen you can press SHIFT-down to submit the prompt contents.
Multiline prompts do not accept ENTER as a submission key because it instead
inserts a newline.

Interactive mode builds a dbmp command to run with vanilla dbmp.  If you would
like to see the command it constructs, add the `--dry-run` argument.

```bash
$ ./dbmp --interactive --dry-run
```
