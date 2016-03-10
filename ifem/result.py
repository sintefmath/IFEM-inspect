from io import StringIO
from itertools import chain
import tempfile
import xml.etree.ElementTree as xml

import numpy as np
import h5py

from splipy.io import G2


class G2Object(G2):

    def __init__(self, fstream):
        self.fstream = fstream
        super(G2Object, self).__init__('')

    def __enter__(self):
        self.onlywrite = False
        return self


class Time:

    def __init__(self, level, group):
        self.level = level
        self.group = group

    @property
    def t(self):
        return self.group['timeinfo']['SIMbase-1'][0]


class Basis:

    def __init__(self, name, group):
        self.name = name
        self.group = group
        self.fields = []

        self.patches = []
        for i in range(1, self.npatches + 1):
            g2data = StringIO(group[str(i)][:].tobytes().decode('utf-8'))
            with G2Object(g2data) as g:
                self.patches.append(g.read()[0])

    @property
    def npatches(self):
        return len(self.group)

    @property
    def ncoefs(self):
        return sum(len(p) for p in self.patches)

    @property
    def type(self):
        return type(self.patches[0])

    @property
    def pardim(self):
        return self.patches[0].pardim

    @property
    def order(self):
        return self.patches[0].order('u')


class Field:

    def __init__(self, name, basis, components, result):
        self.name = name
        self.basis = basis
        self.components = components
        self.result = result
        basis.fields.append(self)

    @property
    def type(self):
        if self.components == 1:
            return 'scalar'
        if self.components == self.basis.pardim:
            return 'vector'
        return '{}-dim'.format(self.components)

    def geometry(self, patchid):
        return self.basis.patches[patchid - 1].clone()

    def patch(self, level, patchid):
        patch = self.basis.patches[patchid - 1].clone()
        patch.set_dimension(self.components)

        coefs = self.result.hdf[str(level)][str(patchid)][self.name][:]
        shape = [b.num_functions() for b in patch.bases[::-1]] + [self.components]
        coefs = np.reshape(coefs, shape)

        spec = tuple(list(range(patch.pardim))[::-1] + [patch.pardim])
        coefs = coefs.transpose(spec)
        patch.controlpoints = coefs

        return patch


class Result:

    def __init__(self, filename):
        self.filename = filename

    def __enter__(self):
        self.hdf = h5py.File(self.filename + '.hdf5', 'r')
        self._cached_bases = {}

        self.xml = xml.parse(self.filename + '.xml')
        self.fields = {}
        for child in self.xml.getroot():
            if child.tag == 'levels':
                self.ntimes = int(child.text) + 1
            elif child.tag == 'timestep':
                self.dt = float(child.text)
            elif child.tag == 'entry':
                if child.attrib['description'] == 'primary' and \
                   child.attrib['type'] == 'field':
                    name = child.attrib['name']
                    basis = self.basis(child.attrib['basis'])
                    components = int(child.attrib['components'])
                    self.fields[name] = Field(name, basis, components, self)

        return self

    def __exit__(self, *args):
        self.hdf.close()

    def time(self, n):
        if n < 0:
            n += self.ntimes
        return Time(n, self.hdf[str(n)])

    def level(self, t):
        closest = self.time(0)
        diff = abs(t - closest.t)
        for i in range(1, self.ntimes):
            test_time = self.time(i)
            test_diff = abs(t - test_time.t)
            if test_diff < diff:
                diff = test_diff
                closest = test_time
        return closest

    @property
    def nbases(self):
        return len(self.hdf['0']['basis'])

    def bases(self):
        for i in range(self.nbases):
            yield self.basis(i)

    def basis(self, n):
        try:
            return self._cached_bases[n]
        except KeyError:
            names = list(self.hdf['0']['basis'])

            if isinstance(n, str):
                name = n
                index = names.index(n)
            else:
                name = names[n]
                index = n

            basis = Basis(name, self.hdf['0']['basis'][name])
            self._cached_bases[name] = basis
            self._cached_bases[index] = basis
            return basis

    def field(self, name):
        candidates = set()
        for k, f in self.fields.items():
            if f.name.lower().startswith(name.lower()):
                candidates.add(f)
        if len(candidates) == 1:
            return next(iter(candidates))
        raise KeyError
