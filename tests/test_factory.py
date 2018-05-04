"""
Tests for the pix factory.
"""
import pytest
import mock

import pix.factory
import pix.model

from tests.mymodels import PIXTestObj, PIXTestChildObj


@pytest.fixture()
@mock.patch('pix.api.Session')
def factory(session):
    return pix.factory.Factory(session)


@pytest.fixture()
def payload():
    return {
        'class': 'PIXTestObj',
        'name': 'parent',
        'tests': [
            {
                'class': 'PIXTestChildObj',
                'name': 'foo'
            },
            {
                'class': 'PIXTestChildObj',
                'name': 'bar'
            },
        ]
    }


def test_register(factory):
    assert PIXTestObj in factory._registered['PIXTestObj']
    assert PIXTestChildObj in factory._registered['PIXTestChildObj']


def test_build(factory):
    cls = factory.build('PIXTestObj')
    assert issubclass(cls, PIXTestObj)
    cls = factory.build('PIXTestChildObj')
    assert issubclass(cls, PIXTestChildObj)


def test_objectfy(factory, payload):
    obj = factory.objectfy(payload)
    assert obj['name'] == 'parent'
    assert hasattr(obj, 'get_one')
    assert len(obj['tests']) == 2
    for child in obj['tests']:
        assert isinstance(child, PIXTestChildObj)


def test_children(factory, payload):
    obj = factory.objectfy(payload)
    children = obj.children()
    assert len(children) == 2
    for child in children:
        assert isinstance(child, PIXTestChildObj)
