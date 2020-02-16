"""
Tests for the pix factory.
"""
import inspect

import mock
import pytest
import six

import pix
import pix.factory


@pytest.fixture()
def factory():
    orig = pix.factory.Factory._registered.copy()
    yield pix.factory.Factory(mock.MagicMock())
    pix.factory.Factory._registered = orig


def test_build_inherit_pixobject(factory):

    @pix.register('A')
    class A(pix.PIXObject):
        pass

    cls = factory.build('A')
    assert issubclass(cls, A)
    assert issubclass(cls, pix.PIXObject)


def test_build_inherit_object(factory):

    @pix.register('A')
    class A(object):
        def foo(self):
            pass

    cls = factory.build('A')
    assert issubclass(cls, A)
    assert issubclass(cls, pix.PIXObject)
    assert hasattr(cls, 'foo')


@pytest.mark.skipif(not six.PY3, reason='python 3 style class')
def test_build_no_inherit(factory):

    @pix.register('A')
    class A:
        def foo(self):
            pass

    cls = factory.build('A')
    assert issubclass(cls, A)
    assert issubclass(cls, pix.PIXObject)
    assert hasattr(cls, 'foo')


def test_build_multi_register(factory):

    @pix.register('A')
    class A1(object):
        @classmethod
        def foo(cls):
            return 1

    @pix.register('A')
    class A2(object):
        @classmethod
        def foo(cls):
            return 2

    cls = factory.build('A')  # type: A2
    assert issubclass(cls, A2)
    assert issubclass(cls, A1)
    assert issubclass(cls, pix.PIXObject)

    mro = inspect.getmro(cls)
    assert mro[1] is A2
    assert mro[2] is A1
    assert mro[3] is pix.PIXObject

    assert hasattr(cls, 'foo')

    # test order that they're registered is the mro order
    assert cls.foo() == 2


def test_objectfy(factory):

    @pix.register('A')
    class A(object):
        pass

    obj = factory.objectfy({'class': 'A'})
    assert isinstance(obj, A)


@pytest.mark.parametrize('obj', (
        '42',
        42,
        42.0,
        [42],
        (42,),
        {42},
))
def test_objectfy_passthru(factory, obj):
    # testing type: (T) -> T behavior of objectfy
    assert obj == factory.objectfy(obj)


def test_objectfy_pixobject(factory):
    # testing type: (T) -> T behavior of objectfy
    class TestObj(pix.PIXObject):
        pass

    obj = TestObj(mock.MagicMock())
    assert obj == factory.objectfy(obj)


@pytest.mark.parametrize('obj', (
    [{'class': 'A', 'id': 1}],
    ({'class': 'A', 'id': 1},),
))
def test_objectfy_seq(factory, obj):

    @pix.register('A')
    class A(object):
        pass

    seq = factory.objectfy(obj)
    assert isinstance(seq[0], A)


def test_objectfy_children(factory):

    @pix.register('A')
    class A(object):
        pass

    @pix.register('B')
    class B(object):
        pass

    obj = factory.objectfy({
        'class': 'A',
        'id': 1,
        'attr': 'foo',
        'child': {
            'class': 'B',
            'id': 2,
            'attr': 'bar',
        },
    })

    assert isinstance(obj, A)
    assert obj['attr'] == 'foo'
    assert isinstance(obj['child'], B)
    assert obj['child']['attr'] == 'bar'


def test_children(factory):

    @pix.register('A')
    class A(object):
        pass

    @pix.register('B')
    class B(object):
        pass

    obj = factory.objectfy({
        'class': 'A',
        'id': 0,
        'child1': {
            'class': 'B',
            'id': 1,
        },
        'child2': {
            'class': 'B',
            'id': 2,
        },
        'child3-4': [
            {
                'class': 'B',
                'id': 3,
            },
            {
                'class': 'B',
                'id': 4,
            },
        ],
        'not-a-child': 42,
        'also-not-a-child': {'k': ['v']}
    })

    children = obj.children()
    assert len(children) == 4
    for child in children:
        assert isinstance(child, B)
