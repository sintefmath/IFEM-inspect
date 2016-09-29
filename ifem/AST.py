from copy import deepcopy
from enum import IntEnum
from grako.exceptions import ParseError
from collections import namedtuple
from itertools import chain
from math import ceil
from six import string_types

from ifem.parser import IFEMScriptSemantics as DefaultSemantics
from ifem.namespace import Boundness, IFEMUnboundError
from ifem.types import Type, IFEMTypeError


class EvalLevel(IntEnum):
    scope = 1
    type = 2
    full = 3


class ASTNode(object):
    def evaluate(self, namespace, level=EvalLevel.scope):
        if level == EvalLevel.scope:
            return self.scope(namespace)
        elif level == EvalLevel.type:
            return self.type(namespace)
        elif level == full:
            return self.eval(namespace)


class Identifier(ASTNode, namedtuple('Identifier', ['name'])):
    def scope(self, namespace):
        if namespace.boundness(self.name) < Boundness.restricted:
            raise IFEMUnboundError('No such binding: {}'.format(self.name))
    def type(self, namespace):
        return namespace[self.name]
    def __repr__(self):
        return '{{id {}}}'.format(self.name)
    def __eq__(self, other):
        return isinstance(other, Identifier) and self.name == other.name


class Number(ASTNode, namedtuple('Number', ['value'])):
    def scope(self, namespace):
        pass
    def type(self, namespace):
        return Type.ScalarField([])
    def __repr__(self):
        return '{{num {}}}'.format(self.value)
    def __eq__(self, other):
        return isinstance(other, Number) and self.value == other.value


class UnOp(ASTNode, namedtuple('UnOp', ['operator', 'operand'])):
    def type(self, namespace):
        subtype = self.operand.type(namespace)
        if not isinstance(subtype, Type.Field):
            raise IFEMTypeError("Operand to '{}' not a field".format(self.operator))
        return self.operand.type(namespace)
    def free_vars(self, namespace):
        return self.operand.free_vars(namespace)
    def __repr__(self):
        return '{{{} {}}}'.format(self.operator, self.operand)
    def __eq__(self, other):
        return (isinstance(other, UnOp) and
                self.operator == other.operator and
                self.operand == other.operand)


class BinOp(ASTNode, namedtuple('BinOp', ['operator', 'l_operand', 'r_operand'])):
    def scope(self, namespace):
        self.l_operand.scope(namespace)
        self.r_operand.scope(namespace)
    def type(self, namespace):
        r_type = self.r_operand.type(namespace)
        if self.operator in {'+', '-', '*', '/', '**'}:
            l_type = self.l_operand.type(namespace)
            if not (isinstance(l_type, Type.Field) and isinstance(r_type, Type.Field)):
                raise IFEMTypeError("Operand '{}' must have field arguments".format(self.operator))
            if self.operator == '**' and r_type.dim > 0:
                raise IFEMTypeError('Exponent must be scalar')
            if l_type.dim > 0 and r_type.dim > 0 and l_type != r_type:
                raise IFEMTypeError("Operands to '{}' have incompatible types".format(self.operator))
            shape = r_type.shape if r_type.dim > 0 else l_type.shape
            deps = l_type.deps | r_type.deps
            return Type.Field(deps, *shape)
        if self.operator == '=':
            return Type.EqCond(r_type)
        if self.operator in {'<', '<=', '>', '>='}:
            return Type.IneqCond()
    def free_vars(self, namespace):
        if self.operator in {'+', '-', '*', '/', '**'}:
            ret = self.l_operand.free_vars(namespace)
            ret |= self.r_operand.free_vars(namespace)
            return ret
        if self.operator in {'=', '<', '<=', '>', '>='}:
            return self.r_operand.free_vars(namespace)
    def __repr__(self):
        return '{{{} {} {}}}'.format(self.operator, self.l_operand, self.r_operand)
    def __eq__(self, other):
        return (isinstance(other, BinOp) and
                self.operator == other.operator and
                self.l_operand == other.l_operand and
                self.r_operand == other.r_operand)


class DoubleIneq(ASTNode,
                 namedtuple('DoubleIneq',
                            ['identifier', 'lower', 'upper', 'lower_strict', 'upper_strict'])):
    def type(self, namespace):
        return Type.DoubleIneqCond()
    def free_vars(self, namespace):
        ret = self.lower.free_vars(namespace)
        ret |= self.upper.free_vars(namespace)
        return ret
    def __repr__(self):
        return '{{dineq {} {} {} {} {}}}'.format(
            self.lower, '<' if self.lower_strict else '<=', self.identifier,
            '<' if self.upper_strict else '<=', self.upper
        )
    def __eq__(self, other):
        return (isinstance(other, DoubleIneq) and
                self.identifier == other.identifier and
                self.lower == other.lower and
                self.lower_strict == other.lower_strict and
                self.upper == other.upper and
                self.upper_strict == other.upper_strict)


class Subscript(ASTNode, namedtuple('Subscript', ['root', 'indices'])):
    def type(self, namespace):
        r_type = self.root.type(namespace)
        if not isinstance(r_type, Type.Field):
            raise IFEMTypeError('Subscripting a non-field')
        if len(self.indices) != r_type.dim:
            raise IFEMTypeError('Expected {} indices but found {}'.format(
                r_type.dim, len(self.indices)
            ))
        resulting = []
        for i, dim in zip(self.indices, r_type.shape):
            if isinstance(i, int) and i >= dim:
                raise IFEMTypeError('Index out of bounds')
            elif isinstance(i, Slice):
                resulting.append(dim)
        return Type.Field(r_type.deps, *resulting)
    def free_vars(self, namespace):
        return self.root.free_vars(namespace)
    def __repr__(self):
        return '{{sub {} {}}}'.format(self.root, self.indices)
    def __eq__(self, other):
        return (isinstance(other, Subscript) and
                self.root == other.root and
                self.indices == other.indices)


class Slice(ASTNode):
    def __repr__(self):
        return '{slc}'
    def __eq__(self, other):
        return isinstance(other, Slice)


class FunCall(ASTNode, namedtuple('FunCall', ['func', 'args'])):
    def type(self, namespace):
        func_type = self.func.type(namespace)
        if not isinstance(func_type, Type.Callable):
            raise IFEMTypeError('Object not callable')
        arg_types = [arg.type(namespace) for arg in self.args]
        return func_type.restype(*arg_types)
    def free_vars(self, namespace):
        ret = self.func.free_vars(namespace)
        ret.update(*(arg.free_vars(namespace) for arg in self.args))
        return ret
    def __repr__(self):
        return '{{fnc {} {}}}'.format(self.func, self.args)
    def __eq__(self, other):
        return (isinstance(other, FunCall) and
                self.func == other.func and
                self.args == other.args)


class For(ASTNode, namedtuple('For', ['bindings', 'expr'])):
    def type(self, namespace):
        b_types = [b.type(namespace) for b in self.bindings]
        if any(not isinstance(t, Type.EqCond) for t in b_types):
            raise IFEMTypeError("'for' must be called with '='-arguments")
        if any(not isinstance(t.rtype, Type.Field) for t in b_types):
            raise IFEMTypeError("'for' must have field ranges")
        sub_namespace = namespace.shadow(**{
            b.l_operand.name: Type.ScalarField(t.rtype.deps)
            for b, t in zip(self.bindings, b_types)
        })
        sub_type = self.expr.type(sub_namespace)
        if not isinstance(sub_type, Type.Field):
            raise IFEMTypeError("'for' must have a field expression")
        dims = []
        for b_type in b_types:
            dims.extend(b_type.rtype.shape)
        dims.extend(sub_type.shape)
        ret_type = Type.Field(sub_type.deps, *dims)
        return sub_namespace.remove_bound_deps(ret_type)
    def __repr__(self):
        return '{{for {} {}}}'.format(self.bindings, self.expr)
    def __eq__(self, other):
        return (isinstance(other, For) and
                self.bindings == other.bindings and
                self.expr == other.expr)


class Int(ASTNode, namedtuple('Int', ['domain', 'expr'])):
    def type(self, namespace):
        new_bindings = {}
        for b in self.domain:
            t = b.type(namespace)
            if isinstance(t, Type.EqCond):
                new_bindings[b.l_operand.name] = t.rtype
            elif isinstance(t, Type.DoubleIneqCond):
                l_type = b.lower.type(namespace)
                r_type = b.upper.type(namespace)
                if not (isinstance(l_type, Type.Field) and isinstance(r_type, Type.Field)):
                    raise IFEMTypeError('Bounds must be fields')
                if not (l_type.dim == 0 and r_type.dim == 0):
                    raise IFEMTypeError('Bounds must be scalars')
                new_bindings[b.identifier.name] = Type.ScalarField(l_type.deps | r_type.deps)
            else:
                raise IFEMTypeError("'int' must be called with '=' or '<..<'-arguments")
        sub_namespace = namespace.shadow(**new_bindings)
        sub_type = self.expr.type(sub_namespace)
        return sub_namespace.remove_bound_deps(sub_type)
    def __repr__(self):
        return '{{int {} {}}}'.format(self.domain, self.expr)
    def __eq__(self, other):
        return (isinstance(other, Int) and
                self.domain == other.domain and
                self.expr == other.expr)


class Vector(ASTNode, namedtuple('Vector', ['components'])):
    def type(self, namespace):
        subtypes = [c.type(namespace) for c in self.components]
        if not isinstance(subtypes[0], Type.Field):
            raise IFEMTypeError('Vectors must contain fields')
        if not all(x.shape == subtypes[0].shape for x in subtypes):
            raise IFEMTypeError('Vectors must have elements of same shape')
        deps = set(chain.from_iterable(x.deps for x in subtypes))
        dims = [len(self.components)] + subtypes[0].shape
        return Type.Field(deps, *dims)
    def free_vars(self, namespace):
        ret = set()
        ret.update(*(comp.free_vars(namespace) for comp in self.components))
        return ret
    def __repr__(self):
        return '{{vec {}}}'.format(self.components)
    def __eq__(self, other):
        return isinstance(other, Vector) and self.components == other.components


class Range(ASTNode, namedtuple('Range', ['start', 'stop', 'step'])):
    def type(self, namespace):
        npts = (self.stop.value - self.start.value) / self.step.value + 1
        return Type.VectorField([], int(ceil(npts)))
    def free_vars(self, namespace):
        return set()
    def __repr__(self):
        return '{{rng {}:{}:{}}}'.format(self.start, self.step, self.stop)
    def __eq__(self, other):
        return (isinstance(other, Range) and
                self.start == other.start and
                self.step == other.step and
                self.stop == other.stop)


class IFEMScriptSemantics(DefaultSemantics):

    def identifier(self, name):
        return Identifier(name)

    def index_uint(self, value):
        return int(value)

    def number(self, value):
        return Number(float(value))

    def power(self, args):
        if len(args) == 2:
            return BinOp('**', *args)
        return args[0]

    def factor(self, args):
        if isinstance(args, ASTNode):
            return args
        elif len(args) == 1:
            return args[0]
        return UnOp(*args)

    def term(self, args):
        init, rest = args
        if not rest:
            return init
        for operator, operand in rest:
            init = BinOp(operator, init, operand)
        return init

    arith = term

    def trailer_expr(self, args):
        root, trailers = args
        for trailer in trailers:
            if trailer[0] in '.[':
                if trailer[0] == '.':
                    raw_inds = [trailer[1]]
                else:
                    raw_inds = trailer[1]
                char_to_num = lambda c: Slice() if c == ':' else 'xyz'.index(c)
                if len(raw_inds) == 1 and isinstance(raw_inds[0], string_types):
                    inds = [char_to_num(i) for i in raw_inds[0]]
                else:
                    inds = [char_to_num(i) if isinstance(i, string_types) else i
                            for i in raw_inds]
                return Subscript(root, inds)
            elif trailer[0] == '(':
                if isinstance(root, Vector):
                    root = Vector([FunCall(comp, deepcopy(trailer[1]))
                                   for comp in root.components])
                elif isinstance(root, Identifier) and root.name == 'for':
                    root = For(trailer[1][:-1], trailer[1][-1])
                elif isinstance(root, Identifier) and root.name == 'int':
                    root = Int(trailer[1][:-1], trailer[1][-1])
                else:
                    root = FunCall(root, trailer[1])
        return root

    def single_arg(self, args):
        name, oper, value = args
        return BinOp(oper, name, value)

    def double_arg(self, args):
        lower, l_ineq, identifier, u_ineq, upper = args
        return DoubleIneq(identifier, lower, upper, l_ineq == '<', u_ineq == '<')

    def vector_lit(self, args):
        return Vector(args)

    def range_lit(self, args):
        if len(args) == 2:
            start, stop = args
            step = Number(1.0)
        else:
            start, step, stop = args
        return Range(start, stop, step)
