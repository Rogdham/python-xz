#!/usr/bin/env python

from setuptools import setup

setup(
    use_scm_version={
        "write_to": "src/xz/_version.py",
        "write_to_template": '__version__ = "{version}"\n',
    }
)
