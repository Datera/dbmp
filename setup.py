#!/usr/bin/env

from setuptools import setup

setup(
    name='dbmp',
    version='0.1.0',
    description='Datera Bare Metal Provisioner',
    long_description='Install Instructions: sudo python setup.py install',
    author='Datera Ecosystem Team',
    author_email='support@datera.io',
    packages=['dbmp'],
    package_dir={'': 'src'},
    # package_data={'dfs_sdk': ['log_cfg/*.json']},
    # include_package_data=True,
    install_requires=[],
    scripts=[],
    url='https://github.com/Datera/dbmp/',
)
