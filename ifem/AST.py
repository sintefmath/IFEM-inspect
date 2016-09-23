from copy import deepcopy
from grako.exceptions import ParseError
from collections import namedtuple
from ifem.parser import IFEMScriptSemantics as DefaultSemantics


class ASTNode:
    pass


class Identifier(ASTNode, namedtuple('Identifier', ['name'])):
    def __repr__(self):
        return '{{id {}}}'.format(self.name)
    def __eq__(self, other):
        return isinstance(other, Identifier) and self.name == other.name


class Number(ASTNode, namedtuple('Number', ['value'])):
    def __repr__(self):
        return '{{num {}}}'.format(self.value)
    def __eq__(self, other):
        return isinstance(other, Number) and self.value == other.value


class UnOp(ASTNode, namedtuple('UnOp', ['operator', 'operand'])):
    def __repr__(self):
        return '{{{} {}}}'.format(self.operator, self.operand)
    def __eq__(self, other):
        return (isinstance(other, UnOp) and
                self.operator == other.operator and
                self.operand == other.operand)


class BinOp(ASTNode, namedtuple('BinOp', ['operator', 'l_operand', 'r_operand'])):
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
    def __repr__(self):
        return '{{fnc {} {}}}'.format(self.func, self.args)
    def __eq__(self, other):
        return (isinstance(other, FunCall) and
                self.func == other.func and
                self.args == other.args)


class For(ASTNode, namedtuple('For', ['bindings', 'expr'])):
    def __repr__(self):
        return '{{for {} {}}}'.format(self.bindings, self.expr)
    def __eq__(self, other):
        return (isinstance(other, For) and
                self.bindings == other.bindings and
                self.expr == other.expr)


class Int(ASTNode, namedtuple('Int', ['domain', 'expr'])):
    def __repr__(self):
        return '{{int {} {}}}'.format(self.domain, self.expr)
    def __eq__(self, other):
        return (isinstance(other, Int) and
                self.domain == other.domain and
                self.expr == other.expr)


class Vector(ASTNode, namedtuple('Vector', ['components'])):
    def __repr__(self):
        return '{{vec {}}}'.format(self.components)
    def __eq__(self, other):
        return isinstance(other, Vector) and self.components == other.components


class Range(ASTNode, namedtuple('Range', ['start', 'stop', 'step'])):
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
                if len(raw_inds) == 1 and isinstance(raw_inds[0], str):
                    inds = [char_to_num(i) for i in raw_inds[0]]
                else:
                    inds = [char_to_num(i) if isinstance(i, str) else i
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
