from itertools import chain
import pytest

from ifem.namespace import *


def test_composition():
    ns = Namespace.simple(3, 3, True)

    nss = ns.shadow(t=True)
    for c in ['pid', 'u', 'v', 'w', 'x', 'y', 'z']:
        assert nss.boundness(c) == Boundness.restricted
        assert nss.bindable(c)
    for c in ['__param__', '__physical__', '__space__']:
        assert nss.boundness(c) == Boundness.restricted
        assert not nss.bindable(c)
    assert nss.boundness('t') == Boundness.bound
    assert nss.bindable('t')
    for c in ['tid', '__time__']:
        assert nss.boundness(c) == Boundness.dependent
        assert not nss.bindable(c)

    nss = ns.shadow(tid=True)
    for c in ['pid', 'u', 'v', 'w', 'x', 'y', 'z']:
        assert nss.boundness(c) == Boundness.restricted
        assert nss.bindable(c)
    for c in ['__param__', '__physical__', '__space__']:
        assert nss.boundness(c) == Boundness.restricted
        assert not nss.bindable(c)
    assert nss.boundness('tid') == Boundness.bound
    assert nss.bindable('tid')
    for c in ['t', '__time__']:
        assert nss.boundness(c) == Boundness.dependent
        assert not nss.bindable(c)

    nss = ns.shadow(pid=True, u=True)
    for c in ['pid', 'u']:
        assert nss.boundness(c) == Boundness.bound
        assert nss.bindable(c)
    for c in ['v', 'w', 't', 'tid']:
        assert nss.boundness(c) == Boundness.restricted
        assert nss.bindable(c)
    for c in ['x', 'y', 'z', '__param__', '__physical__', '__space__', '__time__']:
        assert nss.boundness(c) == Boundness.restricted
        assert not nss.bindable(c)

    nss = ns.shadow(pid=True, u=True, v=True, w=True)
    for c in ['tid', 't']:
        assert nss.boundness(c) == Boundness.restricted
        assert nss.bindable(c)
    assert nss.boundness('__time__') == Boundness.restricted
    assert not nss.bindable('__time__')
    for c in ['pid', 'u', 'v', 'w']:
        assert nss.boundness(c) == Boundness.bound
        assert nss.bindable(c)
    for c in ['x', 'y', 'z', '__param__', '__physical__', '__space__']:
        assert nss.boundness(c) == Boundness.dependent
        assert not nss.bindable(c)

    nss = ns.shadow(x=True)
    assert nss.boundness('x') == Boundness.bound
    assert nss.bindable('x')
    for c in ['y', 'z', 't', 'tid']:
        assert nss.boundness(c) == Boundness.restricted
        assert nss.bindable(c)
    for c in ['pid', 'u', 'v', 'w']:
        assert nss.boundness(c) == Boundness.restricted
        assert not nss.bindable(c)
    for c in ['__param__', '__physical__', '__space__', '__time__']:
        assert nss.boundness(c) == Boundness.restricted
        assert not nss.bindable(c)

    nss = nss.shadow(y=True, z=True)
    for c in ['x', 'y', 'z']:
        assert nss.boundness(c) == Boundness.bound
        assert nss.bindable(c)
    for c in ['t', 'tid']:
        assert nss.boundness(c) == Boundness.restricted
        assert nss.bindable(c)
    assert nss.boundness('__time__') == Boundness.restricted
    assert not nss.bindable('__time__')
    for c in ['pid', 'u', 'v', 'w', '__param__', '__physical__', '__space__']:
        assert nss.boundness(c) == Boundness.dependent
        assert not nss.bindable(c)
