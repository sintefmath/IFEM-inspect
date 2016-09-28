from collections import namedtuple
from io import StringIO
from itertools import chain
import xml.etree.ElementTree as xml

import numpy as np
import h5py

from splipy.io import G2

from ifem.namespace import Namespace
from ifem.AST import Type


Field = namedtuple('Field', ['components', 'basis'])


class G2Object(G2):

    def __init__(self, fstream):
        self.fstream = fstream
        super(G2Object, self).__init__('')

    def __enter__(self):
        self.onlywrite = False
        return self


class Basis:

    def __init__(self, group):
        npatches = len(group)
        patches = []
        for i in range(1, len(group)+1):
            g2data = StringIO(group[str(i)][:].tobytes().decode('utf-8'))
            with G2Object(g2data) as g2:
                patches.append(g2.read()[0])
        self.patches = patches

    @property
    def dim(self):
        return self.patches[0].dimension

    @property
    def pardim(self):
        return self.patches[0].pardim


class Result:

    def __init__(self, basename):
        self.basename = basename

    def __enter__(self):
        self.hdf = h5py.File(self.basename + '.hdf5', 'r')
        self.xml = xml.parse(self.basename + '.xml')

        self.fields = {}
        for child in self.xml.getroot():
            if child.tag == 'levels':
                self.ntimes = int(child.text) + 1
            elif child.tag == 'entry':
                if child.attrib['type'] == 'field':
                    self.fields[child.attrib['name']] = Field(
                        components=int(child.attrib['components']),
                        basis=child.attrib['basis']
                    )

        bases = {}
        for basisname in self.hdf['0']['basis']:
            bases[basisname] = Basis(self.hdf['0']['basis'][basisname])
        self.bases = bases

        return self

    def __exit__(self, *args):
        self.hdf.close()

    def namespace(self):
        ns = Namespace.simple(self.dim, self.pardim, self.ntimes > 1)

        deps = ['__space__']
        if self.ntimes > 1:
            deps.append('__time__')

        for fieldname, field in self.fields.items():
            if field.components > 1:
                type = Type.VectorField(deps, field.components)
            else:
                type = Type.ScalarField(deps)
            ns.restrict(fieldname, type)

        return ns

    @property
    def dim(self):
        return next(iter(self.bases.values())).dim

    @property
    def pardim(self):
        return next(iter(self.bases.values())).pardim
