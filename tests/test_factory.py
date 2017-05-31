"""
`pix.factory.Factory` testing module
"""
from pytest import fixture
from mock import patch
import pix.model
import pix.factory


@pix.factory.register('PIXTestObj')
class PIXTestObj(pix.model.PIXObject):
    def get_one(self):
        return 1


@pix.factory.register('PIXTestChildObj')
class PIXTestChildObj(pix.model.PIXObject):
    pass


@fixture()
@patch('pix.api.Session')
def factory(session):
    return pix.factory.Factory(session)


@fixture()
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


def test_build_obj(factory):
    cls = factory.build_obj('PIXTestObj')
    assert issubclass(cls, PIXTestObj)
    cls = factory.build_obj('PIXTestChildObj')
    assert issubclass(cls, PIXTestChildObj)


def test_objectfy(factory, payload):
    obj = factory.objectfy(payload)
    assert obj.name == 'parent'
    assert obj['name'] == 'parent'
    assert len(obj.tests) == 2
    for child in obj.tests:
        assert isinstance(child, PIXTestChildObj)


def test_children(factory, payload):
    obj = factory.objectfy(payload)
    children = obj.children()
    assert len(children) == 2
    for child in children:
        assert isinstance(child, PIXTestChildObj)
