import pytest

from ifem.parser import IFEMScriptParser
from ifem.namespace import Namespace
from ifem.types import Type, IFEMTypeError
from ifem.AST import *


def typeof(s, namespace):
    parser = IFEMScriptParser()
    semantics = IFEMScriptSemantics()
    return parser.parse(s, rule_name='full', semantics=semantics).type(namespace)


def test_identifier():
    ns = Namespace.simple(
        2, 2, False,
        scl=Type.ScalarField(),
        vec1=Type.VectorField(1),
        vec2=Type.VectorField(2),
        vec3=Type.VectorField(3),
        tens22=Type.TensorField(2,2),
        tens33=Type.TensorField(3,3),
    )

    assert typeof('u', ns) == Type.ScalarField()
    assert typeof('x', ns) == Type.ScalarField()
    assert typeof('scl', ns) == Type.ScalarField()
    for i, v in enumerate(['vec1', 'vec2', 'vec3'], start=1):
        assert typeof(v, ns) == Type.VectorField(i)
    assert typeof('tens22', ns) == Type.TensorField(2,2)
    assert typeof('tens33', ns) == Type.TensorField(3,3)
    for v in ['w', 'z', 't', 'tid', 'lol']:
        with pytest.raises(IFEMUnboundError):
            typeof(v, ns)


def test_number():
    ns = Namespace.simple(2, 2, False)
    assert typeof('1', ns) == Type.ScalarField()


def test_arith():
    ns = Namespace.simple(
        2, 2, False,
        scl=Type.ScalarField(),
        vec1=Type.VectorField(1),
        vec2=Type.VectorField(2),
        vec3=Type.VectorField(3),
        tens22=Type.TensorField(2,2),
        tens33=Type.TensorField(3,3),
    )

    assert typeof('scl + scl', ns) == Type.ScalarField()
    assert typeof('scl * vec1', ns) == Type.VectorField(1)
    assert typeof('vec2 / scl', ns) == Type.VectorField(2)
    assert typeof('vec3 - vec3', ns) == Type.VectorField(3)
    assert typeof('tens22 ** scl', ns) == Type.TensorField(2,2)
    assert typeof('scl * tens33', ns) == Type.TensorField(3,3)

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
        scl=Type.ScalarField(),
        vec1=Type.VectorField(1),
        vec2=Type.VectorField(2),
        vec3=Type.VectorField(3),
        tens22=Type.TensorField(2,2),
        tens33=Type.TensorField(3,3),
        tens52=Type.TensorField(5,2),
    )

    assert typeof('scl[]', ns) == Type.ScalarField()
    assert typeof('vec1[0]', ns) == Type.ScalarField()
    assert typeof('vec1[:]', ns) == Type.VectorField(1)
    assert typeof('vec2[1]', ns) == Type.ScalarField()
    assert typeof('vec3[2]', ns) == Type.ScalarField()
    assert typeof('vec3[:]', ns) == Type.VectorField(3)
    assert typeof('tens22[0,1]', ns) == Type.ScalarField()
    assert typeof('tens33[2,2]', ns) == Type.ScalarField()
    assert typeof('tens52[:,0]', ns) == Type.VectorField(5)
    assert typeof('tens52[0,:]', ns) == Type.VectorField(2)
    assert typeof('tens52[:,:]', ns) == Type.TensorField(5,2)

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
        scl=Type.ScalarField(),
        vec1=Type.VectorField(1),
        vec2=Type.VectorField(2),
        vec3=Type.VectorField(3),
        tens53=Type.TensorField(5,3),
        tens53other=Type.TensorField(5,3),
    )

    assert typeof('[scl, 1, 2]', ns) == Type.VectorField(3)
    assert typeof('[vec2]', ns) == Type.TensorField(1,2)
    assert typeof('[vec2, [1, 2]]', ns) == Type.TensorField(2,2)
    assert typeof('[vec3, [scl, scl, 3], vec3, vec3]', ns) == Type.TensorField(4,3)
    assert typeof('[tens53, tens53other]', ns) == Type.Field(2,5,3)

    with pytest.raises(IFEMTypeError):
        typeof('[scl, vec1]', ns)
    with pytest.raises(IFEMTypeError):
        typeof('[vec1, vec3]', ns)
    with pytest.raises(IFEMTypeError):
        typeof('[tens53, tens53other, vec2]', ns)


def test_range():
    ns = Namespace.simple(2, 2, False)

    assert typeof('0:1:10', ns) == Type.VectorField(11)
    assert typeof('2:0.05:3', ns) == Type.VectorField(21)
    assert typeof('2:0.04:3', ns) == Type.VectorField(26)

    assert typeof('0:10', ns) == Type.VectorField(11)
    assert typeof('3:45', ns) == Type.VectorField(43)

    assert typeof('3.5:5.6', ns) == Type.VectorField(4)


def test_funcall():
    pass


def test_for():
    ns = Namespace.simple(
        3, 3, False,
        scl=Type.ScalarField(),
        vec3=Type.VectorField(3),
        tens52=Type.TensorField(5,2),
        test=Type.Callable(),
    )

    assert typeof('for(i=vec3, i)', ns) == Type.VectorField(3)
    assert typeof('for(i=vec3, [i,i**2])', ns) == Type.TensorField(3,2)
    assert typeof('for(i=tens52, j=vec3, [j])', ns) == Type.Field(5,2,3,1)

    with pytest.raises(IFEMTypeError):
        typeof('for(i<3, i)', ns)
    with pytest.raises(IFEMTypeError):
        typeof('for(i=test, i)', ns)
    with pytest.raises(IFEMTypeError):
        typeof('for(i=vec3, test)', ns)


def test_int():
    ns = Namespace.simple(
        3, 3, False,
        scla=Type.ScalarField(),
        sclb=Type.ScalarField(),
    )

    assert typeof('int(0<u<5, u**2)', ns) == Type.ScalarField()
