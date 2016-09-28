from collections import namedtuple
import enum
from itertools import chain


class BoundedEnum(enum.IntEnum):

    @classmethod
    def max(cls):
        return max(cls)

    @classmethod
    def min(cls):
        return min(cls)


@enum.unique
class Boundness(BoundedEnum):
    unbound = 1                 # Fully unbound names
    restricted = 2              # Names that are unbound but limited to a domain
    dependent = 3               # Names that are bound via other names
    bound = 4                   # Names that are directly bound


def propagate(fn):
    def ret(self):
        try:
            return getattr(self._parent, fn.__name__)
        except AttributeError:
            return fn(self)
    return ret

propertygate = lambda fn: property(propagate(fn))


class IFEMUnbindableError(Exception): pass
class IFEMUnboundError(Exception): pass


class Namespace(object):

    def __init__(self, parent=None):
        self._parent = parent
        self._bindings = {}

        if not parent:
            self._exclusion_rules = {}
            self._restricted = set()
            self._all_metavars = {}
            self._any_metavars = {}

    @classmethod
    def simple(cls, dim, pardim, time, **bindings):
        ns = Namespace()

        param = ['pid'] + list('uvw'[:dim])
        physical = list('xyz'[:pardim])
        for c in param:
            ns.exclude(c, *physical)
        for c in physical:
            ns.exclude(c, *param)

        for c in chain(param, physical):
            ns.restrict(c)

        ns.create_metavar('__param__', 'all', *param)
        ns.create_metavar('__physical__', 'all', *physical)
        ns.create_metavar('__space__', 'any', '__param__', '__physical__')

        if time:
            ns.exclude('t', 'tid')
            ns.exclude('tid', 't')
            ns.restrict('t')
            ns.restrict('tid')
            ns.create_metavar('__time__', 'any', 't', 'tid')

        ns._bind(**bindings)
        return ns

    def _lookup_safe(self, name):
        try:
            return self._bindings[name]
        except KeyError:
            if self._parent:
                return self._parent._lookup_safe(name)
        return None

    def __getitem__(self, name):
        ret = self._lookup_safe(name)
        if ret is None:
            raise IFEMUnboundError('No such binding: {}'.format(name))
        return ret

    def _bind(self, **bindings):
        for name, value in bindings.items():
            if not self.bindable(name):
                raise IFEMUnbindableError('Name {} is unbindable in this context'.format(name))
            self._bindings[name] = value

    @propertygate
    def exclusion_rules(self):
        return self._exclusion_rules

    @propertygate
    def restricted(self):
        return self._restricted

    @propertygate
    def all_metavars(self):
        return self._all_metavars

    @propertygate
    def any_metavars(self):
        return self._any_metavars

    def exclude(self, name, *exclusions):
        self._exclusion_rules.setdefault(name, set()).update(exclusions)

    def restrict(self, name):
        self._restricted.add(name)

    def create_metavar(self, name, kind, *deps):
        if kind == 'all':
            self._all_metavars[name] = set(deps)
        elif kind == 'any':
            self._any_metavars[name] = set(deps)

    def boundness(self, name, ignore=None):
        # If it's bound, it's bound. End of story.
        if self._lookup_safe(name):
            return Boundness.bound

        if ignore is None:
            ignore = set()
        ret = Boundness.min()

        # If it's restricted, it's at least that much.
        if name in self.restricted:
            ret = max(ret, Boundness.restricted)

        # If it's an 'all' metavar, it's at least as bound as the minimally
        # bound member in that metavar, but not more than dependent.
        if name in self.all_metavars:
            member_min = min(self.boundness(dep, ignore) for dep in self.all_metavars[name])
            ret = max(ret, min(Boundness.dependent, member_min))

        # If it's a member of an 'all' metavar, it's at least as bound as the
        # owner, but not more than dependent.
        for owner, deps in self.all_metavars.items():
            if name not in deps: continue
            if owner in ignore: continue
            ret = max(ret, min(Boundness.dependent, self.boundness(owner, ignore | {owner})))

        # If it's an 'any' metavar, it's at least as bound as the maximally
        # bound member in that metavar, but not more than dependent.
        if name in self.any_metavars:
            member_max = max(self.boundness(dep, ignore) for dep in self.any_metavars[name])
            ret = max(ret, min(Boundness.dependent, member_max))

        # If it's a member of an 'any' metavar, it's at least as bound as the
        # maximally bound member in that metavar, but not more than dependent.
        for owner, deps in self.any_metavars.items():
            if name not in deps: continue
            if owner in ignore: continue
            deps = deps | {owner}
            member_max = max(self.boundness(dep, ignore | {owner}) for dep in deps)
            ret = max(ret, min(Boundness.dependent, member_max))

        return ret

    def bindable(self, name):
        # Names that are bound can be rebound.
        if self._lookup_safe(name):
            return True

        # Check the exclusion rules.
        for owner, deps in self.exclusion_rules.items():
            if name in deps and self._lookup_safe(owner):
                return False

        # Metavars can only be indirectly bound.
        if name in self.all_metavars or name in self.any_metavars:
            return False

        return True

    def shadow(self, **bindings):
        ns = Namespace(self)
        ns._bind(**bindings)
        return ns
