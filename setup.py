#!/usr/bin/env python3

from distutils.core import setup

setup(
    name='IFEM-Inspect',
    version='0.0.1',
    description='Inspect IFEM result files',
    author='Eivind Fonn',
    author_email='eivind.fonn@sintef.no',
    license='GPL3',
    url='https://github.com/sintefmath/IFEM-inspect',
    py_modules=['ifem'],
    install_requires=[
        'Splipy',
        'six',
        'enum34',
        'click',
        'grako',
        'h5py',
        'numpy',
    ],
    entry_points={
        'console_scripts': ['ifem-inspect=ifem.__main__:main']
    }
)
