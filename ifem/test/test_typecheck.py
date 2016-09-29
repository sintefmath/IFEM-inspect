import pytest

from ifem.parser import IFEMScriptParser
from ifem.namespace import Namespace
from ifem.typing import Type, IFEMTypeError
from ifem.AST import *


def typeof(s, namespace):
    parser = IFEMScriptParser()
    semantics = IFEMScriptSemantics()
    return parser.parse(s, rule_name='full', semantics=semantics).type(namespace)


def test_identifier():
    ns = Namespace.simple(
        2, 2, False,
        scl=Type.ScalarField(['test']),
        vec1=Type.VectorField(['__space__'], 1),
        vec2=Type.VectorField(['__space__'], 2),
        vec3=Type.VectorField(['__space__'], 3),
        tens22=Type.TensorField(['__space__'], 2, 2),
        tens33=Type.TensorField(['__space__'], 3, 3),
    )

    assert typeof('u', ns) == Type.ScalarField(['__space__'])
    assert typeof('x', ns) == Type.ScalarField(['__space__'])
    assert typeof('scl', ns) == Type.ScalarField(['test'])
    for i, v in enumerate(['vec1', 'vec2', 'vec3'], start=1):
        assert typeof(v, ns) == Type.VectorField(['__space__'], i)
    assert typeof('tens22', ns) == Type.TensorField(['__space__'], 2, 2)
    assert typeof('tens33', ns) == Type.TensorField(['__space__'], 3, 3)
    for v in ['w', 'z', 't', 'tid', 'lol']:
        with pytest.raises(IFEMUnboundError):
            typeof(v, ns)


def test_number():
    ns = Namespace.simple(2, 2, False)
    assert typeof('1', ns) == Type.ScalarField([])


def test_arith():
    ns = Namespace.simple(
        2, 2, False,
        scl=Type.ScalarField(['a']),
        vec1=Type.VectorField(['b'], 1),
        vec2=Type.VectorField(['c'], 2),
        vec3=Type.VectorField(['d'], 3),
        tens22=Type.TensorField(['e'], 2, 2),
        tens33=Type.TensorField(['f'], 3, 3),
    )

    assert typeof('scl + scl', ns) == Type.ScalarField(['a'])
    assert typeof('scl * vec1', ns) == Type.VectorField(['a', 'b'], 1)
    assert typeof('vec2 / scl', ns) == Type.VectorField(['a', 'c'], 2)
    assert typeof('vec3 - vec3', ns) == Type.VectorField(['d'], 3)
    assert typeof('tens22 ** scl', ns) == Type.TensorField(['a', 'e'], 2, 2)
    assert typeof('scl * tens33', ns) == Type.TensorField(['a', 'f'], 3, 3)

    with pytest.raises(IFEMTypeError):
        typeof('vec1 + vec2', ns)
    with pytest.raises(IFEMTypeError):
        typeof('vec3 / vec2', ns)
    with pytest.raises(IFEMTypeError):
        typeof('scl ** vec2', ns)
    with pytest.raises(IFEMTypeError):
        typeof('tens22 * vec3', ns)
    with pytest.raises(IFEMTypeError):
        typeof('tens22 - tens33', ns)


def test_subscript():
    ns = Namespace.simple(
        3, 3, False,
        scl=Type.ScalarField(['a']),
        vec1=Type.VectorField(['b'], 1),
        vec2=Type.VectorField(['c'], 2),
        vec3=Type.VectorField(['d'], 3),
        tens22=Type.TensorField(['e'], 2, 2),
        tens33=Type.TensorField(['f'], 3, 3),
        tens52=Type.TensorField(['g'], 5, 2),
    )

    assert typeof('scl[]', ns) == Type.ScalarField(['a'])
    assert typeof('vec1[0]', ns) == Type.ScalarField(['b'])
    assert typeof('vec1[:]', ns) == Type.VectorField(['b'], 1)
    assert typeof('vec2[1]', ns) == Type.ScalarField(['c'])
    assert typeof('vec3[2]', ns) == Type.ScalarField(['d'])
    assert typeof('vec3[:]', ns) == Type.VectorField(['d'], 3)
    assert typeof('tens22[0,1]', ns) == Type.ScalarField(['e'])
    assert typeof('tens33[2,2]', ns) == Type.ScalarField(['f'])
    assert typeof('tens52[:,0]', ns) == Type.VectorField(['g'], 5)
    assert typeof('tens52[0,:]', ns) == Type.VectorField(['g'], 2)
    assert typeof('tens52[:,:]', ns) == Type.TensorField(['g'], 5, 2)

    with pytest.raises(IFEMTypeError):
        typeof('vec1[1]', ns)
    with pytest.raises(IFEMTypeError):
        typeof('vec1.y', ns)
    with pytest.raises(IFEMTypeError):
        typeof('vec1[z]', ns)
    with pytest.raises(IFEMTypeError):
        typeof('vec2.z', ns)
    with pytest.raises(IFEMTypeError):
        typeof('vec2[10]', ns)
    with pytest.raises(IFEMTypeError):
        typeof('vec3[x,x]', ns)
    with pytest.raises(IFEMTypeError):
        typeof('tens52[5,1]', ns)


def test_vector():
    ns = Namespace.simple(
        3, 3, False,
        scl=Type.ScalarField(['a']),
        vec1=Type.VectorField(['b'], 1),
        vec2=Type.VectorField(['c'], 2),
        vec3=Type.VectorField(['d'], 3),
        tens53=Type.TensorField(['e'], 5, 3),
        tens53other=Type.TensorField(['f'], 5, 3),
    )

    assert typeof('[scl, 1, 2]', ns) == Type.VectorField(['a'], 3)
    assert typeof('[vec2]', ns) == Type.TensorField(['c'], 1, 2)
    assert typeof('[vec2, [1, 2]]', ns) == Type.TensorField(['c'], 2, 2)
    assert typeof('[vec3, [scl, scl, 3], vec3, vec3]', ns) == Type.TensorField(['a', 'd'], 4, 3)
    assert typeof('[tens53, tens53other]', ns) == Type.Field(['e', 'f'], 2, 5, 3)

    with pytest.raises(IFEMTypeError):
        typeof('[scl, vec1]', ns)
    with pytest.raises(IFEMTypeError):
        typeof('[vec1, vec3]', ns)
    with pytest.raises(IFEMTypeError):
        typeof('[tens53, tens53other, vec2]', ns)


def test_range():
    ns = Namespace.simple(2, 2, False)

    assert typeof('0:1:10', ns) == Type.VectorField([], 11)
    assert typeof('2:0.05:3', ns) == Type.VectorField([], 21)
    assert typeof('2:0.04:3', ns) == Type.VectorField([], 26)

    assert typeof('0:10', ns) == Type.VectorField([], 11)
    assert typeof('3:45', ns) == Type.VectorField([], 43)

    assert typeof('3.5:5.6', ns) == Type.VectorField([], 4)


def test_funcall():
    pass


def test_for():
    ns = Namespace.simple(
        3, 3, False,
        scl=Type.ScalarField(['a']),
        vec3=Type.VectorField(['b'], 3),
        tens52=Type.TensorField(['c'], 5, 2),
        test=Type.Callable(),
    )

    assert typeof('for(i=vec3, i)', ns) == Type.VectorField(['b'], 3)
    assert typeof('for(i=vec3, [i, i**2])', ns) == Type.TensorField(['b'], 3, 2)
    assert typeof('for(i=tens52, j=vec3, [j])', ns) == Type.Field(['b'], 5, 2, 3, 1)
    assert typeof('for(i=tens52, j=vec3, [i, j])', ns) == Type.Field(['b', 'c'], 5, 2, 3, 2)

    with pytest.raises(IFEMTypeError):
        typeof('for(i<3, i)', ns)
    with pytest.raises(IFEMTypeError):
        typeof('for(i=test, i)', ns)
    with pytest.raises(IFEMTypeError):
        typeof('for(i=vec3, test)', ns)


def test_int():
    ns = Namespace.simple(
        3, 3, False,
        scla=Type.ScalarField(['a']),
        sclb=Type.ScalarField(['__space__']),
    )

    assert typeof('int(0<j<5, j**2)', ns) == Type.ScalarField([])
    assert typeof('int(0<j<5, u*j**2)', ns) == Type.ScalarField(['__space__'])
    assert typeof('int(0<u<1, sclb)', ns) == Type.ScalarField(['__space__'])
    assert typeof('int(pid=1, 0<u<1, 0<v<1, 0<w<1, sclb)', ns) == Type.ScalarField([])
