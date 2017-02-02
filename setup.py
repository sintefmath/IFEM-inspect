#!/usr/bin/env python3

from distutils.core import setup


setup(
    name='IFEM-Inspect',
    version='0.1.0',
    description='Inspect IFEM result files',
    author='Eivind Fonn',
    author_email='eivind.fonn@sintef.no',
    license='GPL3',
    url='https://github.com/sintefmath/IFEM-inspect',
    py_packages=['ifem'],
    install_requires=[
        'click',
        'h5py',
        'ipython',
        'Splipy',
    ],
    entry_points={
        'console_scripts': ['ifem-inspect=ifem.__main__:main'],
    },
)
