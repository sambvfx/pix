"""
Tests for the pix Session object.
"""
import os
import sys

import pytest

import pix.api
import pix.factory
import pix.utils
import pix.exc
import pix.model


_testdir = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture(params=[
    # fullpath
    os.path.join(_testdir, 'mymodels.py'),
    # import path
    'tests.mymodels',
    # directory that is crawled
    _testdir,
])
def plugin_path(request):
    return request.param


@pytest.fixture(params=[
    'foobar.module',
    '/tmp/file/that/doesnotexist.py'
])
def invalid_plugin_path(request):
    return request.param


def test_valid_plugin_paths(plugin_path):
    """
    Test plugin paths properly register to the factory.
    """
    if 'mymodels' in sys.modules:
        sys.modules.pop('mymodels')

    pix.factory.Factory._registered = {}

    session = pix.api.Session(plugin_paths=[plugin_path])

    assert 'PIXTestObj' in session.factory._registered
    assert 'PIXTestChildObj' in session.factory._registered


def test_invalid_plugin_paths(invalid_plugin_path):
    """
    Test invalid plugin paths error.
    """
    with pytest.raises(pix.exc.PIXPluginPathError):
        pix.api.Session(plugin_paths=[invalid_plugin_path])


def test_project_load():
    """
    Tests projects load and become the active project
    """
    session = pix.api.Session()

    # make a bogus project
    project = pix.model.PIXProject(session.factory, id='foo')

    session.load_project(project)

    assert session.active_project == project
