class IFEMTypeError(Exception): pass

class Type(object):

    class TypeBase:

        def __init__(self):
            self.args = []

        def __repr__(self):
            if self.args:
                return '{}({})'.format(self.__class__.__name__,
                                       ','.join(str(a) for a in self.args))
            return self.__class__.__name__

        def __eq__(self, other):
            return self.__class__ == other.__class__ and self.args == other.args

        def __ne__(self, other):
            return not self == other

    class Callable(TypeBase):

        def restype(self, *intypes):
            raise NotImplementedError('restype() not implemented for this callable')

    class Field(Callable):

        def __init__(self, deps, *args):
            self.args = [set(deps)] + list(args)
            self.dim = len(args)

        def restype(self, *intypes):
            if any(not isinstance(t, Type.EqCond) for t in intypes):
                raise IFEMTypeError("Fields must be called with '='-arguments")
            return self

        @property
        def shape(self):
            return self.args[1:]

        @property
        def deps(self):
            return self.args[0]

    @classmethod
    def ScalarField(cls, deps):
        return cls.Field(deps)

    @classmethod
    def VectorField(cls, deps, n):
        return cls.Field(deps, n)

    @classmethod
    def TensorField(cls, deps, m, n):
        return cls.Field(deps, m, n)

    class Cond(TypeBase): pass

    class EqCond(Cond):

        def __init__(self, rtype):
            self.args = [rtype]

        @property
        def rtype(self):
            return self.args[0]

    class IneqCond(Cond): pass

    class DoubleIneqCond(Cond): pass
