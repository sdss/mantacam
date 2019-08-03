#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2019-08-03
# @Filename: setup.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# @Last modified by: José Sánchez-Gallego (gallegoj@uw.edu)
# @Last modified time: 2019-08-03 14:34:41

from setuptools import setup

from build import BuildExt, ext_modules


setup(
    ext_modules=ext_modules,
    cmdclass={'build_ext': BuildExt}
)
