import pytest
from grako.exceptions import FailedParse

from ifem.parser import IFEMScriptParser
from ifem.AST import *


def parse(s):
    parser = IFEMScriptParser()
    semantics = IFEMScriptSemantics()
    return parser.parse(s, rule_name='full', semantics=semantics)


def test_identifier():
    assert parse('a') == Identifier('a')
    assert parse('A1') == Identifier('A1')
    assert parse('_') == Identifier('_')


def test_number():
    assert parse('1') == Number(1.0)
    assert parse('2.') == Number(2.0)
    assert parse('.2') == Number(0.2)
    assert parse('1e1') == Number(10.0)
    assert parse('2e-2') == Number(0.02)
    with pytest.raises(FailedParse):
        parse('.')
    with pytest.raises(FailedParse):
        parse('1e')


def test_unop():
    assert parse('-a') == UnOp('-', Identifier('a'))
    assert parse('+2') == UnOp('+', Number(2.0))
    assert parse('-3') == UnOp('-', Number(3.0))
    assert parse('-++-+6') == \
        UnOp('-', UnOp('+', UnOp('+', UnOp('-', UnOp('+', Number(6.0))))))


def test_binop():
    assert parse('a+b') == BinOp('+', Identifier('a'), Identifier('b'))
    assert parse('2-bl') == BinOp('-', Number(2.0), Identifier('bl'))
    assert parse('3*x') == BinOp('*', Number(3.0), Identifier('x'))
    assert parse('y/2') == BinOp('/', Identifier('y'), Number(2.0))
    assert parse('e**t') == BinOp('**', Identifier('e'), Identifier('t'))
    assert parse('a+2-u') == BinOp('-', BinOp('+', Identifier('a'), Number(2.0)), Identifier('u'))
    assert parse('a/2*u') == BinOp('*', BinOp('/', Identifier('a'), Number(2.0)), Identifier('u'))
    assert parse('x+y*z') == BinOp('+', Identifier('x'), BinOp('*', Identifier('y'), Identifier('z')))
    assert parse('x/y-z') == BinOp('-', BinOp('/', Identifier('x'), Identifier('y')), Identifier('z'))


def test_subscript():
    assert parse('a[x]') == Subscript(Identifier('a'), [0])
    assert parse('a[1,2,x]') == Subscript(Identifier('a'), [1, 2, 0])
    assert parse('a.x') == Subscript(Identifier('a'), [0])
    assert parse('a[:]') == Subscript(Identifier('a'), [Slice()])
    assert parse('a[xyz]') == Subscript(Identifier('a'), [0, 1, 2])
    assert parse('a.z:') == Subscript(Identifier('a'), [2, Slice()])
    assert parse('a.::') == Subscript(Identifier('a'), [Slice(), Slice()])
    assert parse('a[::]') == Subscript(Identifier('a'), [Slice(), Slice()])
    with pytest.raises(FailedParse):
        parse('a[2.0]')
    with pytest.raises(FailedParse):
        parse('a.3')
    with pytest.raises(FailedParse):
        parse('a[b]')
    with pytest.raises(FailedParse):
        parse('a[1+2]')
    with pytest.raises(FailedParse):
        parse('a[-a]')
    with pytest.raises(FailedParse):
        parse('a[b[x]]')


def test_vector():
    assert parse('[a,b]') == Vector([Identifier('a'), Identifier('b')])
    assert parse('[x**2,1]') == Vector([BinOp('**', Identifier('x'), Number(2.0)), Number(1.0)])
    assert parse('[x,y,z][1]') == Subscript(
        Vector([Identifier('x'), Identifier('y'), Identifier('z')]), [1])


def test_funcall():
    assert parse('f(x=1)') == FunCall(
        Identifier('f'), [BinOp('=', Identifier('x'), Number(1.0))])
    assert parse('f(y<1,x>2)') == FunCall(
        Identifier('f'),
        [BinOp('<', Identifier('y'), Number(1.0)), BinOp('>', Identifier('x'), Number(2.0))])
    assert parse('f(x>=y,x<=z)') == FunCall(
        Identifier('f'),
        [BinOp('>=', Identifier('x'), Identifier('y')), BinOp('<=', Identifier('x'), Identifier('z'))])
    assert parse('f(1<u<=2)') == FunCall(
        Identifier('f'), [DoubleIneq(Identifier('u'), Number(1.0), Number(2.0), True, False)])
    assert parse('[f,g](x=1)') == Vector([
        FunCall(Identifier('f'), [BinOp('=', Identifier('x'), Number(1.0))]),
        FunCall(Identifier('g'), [BinOp('=', Identifier('x'), Number(1.0))])])
    assert parse('int(dom, x**2)') == Int([Identifier('dom')], BinOp('**', Identifier('x'), Number(2.0)))
    assert parse('for(i=0:10, y*i)') == For(
        [BinOp('=', Identifier('i'), Range(Number(0.0), Number(10.0), Number(1.0)))],
        BinOp('*', Identifier('y'), Identifier('i')))

    with pytest.raises(FailedParse):
        parse('u()')
