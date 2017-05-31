import pytest
from mock import patch
import pix.api
import pix.factory


def test_plugin_paths1():
    pix.factory.Factory._registered = {}
    with patch.object(pix.api.Session, 'login'):
        session = pix.api.Session()

    with pytest.raises(KeyError):
        bases = session.factory._registered['PIXTestObj']


def test_plugin_paths2():
    pix.factory.Factory._registered = {}
    with patch.object(pix.api.Session, 'login'):
        session = pix.api.Session(plugin_paths='tests/mymodels.py')

    assert 'PIXTestObj' in session.factory._registered
    assert 'PIXTestChildObj' in session.factory._registered


def test_plugin_paths3():
    pix.factory.Factory._registered = {}
    with patch.object(pix.api.Session, 'login'):
        session = pix.api.Session(plugin_paths=['tests/mymodels.py'])

    assert 'PIXTestObj' in session.factory._registered
    assert 'PIXTestChildObj' in session.factory._registered


def test_plugin_paths4():
    import os
    import pix.utils

    pix.factory.Factory._registered = {}
    with patch.object(pix.api.Session, 'login'):
        with pix.utils.ExpandedPath([os.path.dirname(__file__)]):
            session = pix.api.Session(plugin_paths='foo/bar:mymodels.py')

    assert 'PIXTestObj' in session.factory._registered
    assert 'PIXTestChildObj' in session.factory._registered


def test_plugin_paths5():
    pix.factory.Factory._registered = {}
    with patch.object(pix.api.Session, 'login'):
        session = pix.api.Session(plugin_paths='tests.mymodels')

    assert 'PIXTestObj' in session.factory._registered
    assert 'PIXTestChildObj' in session.factory._registered
