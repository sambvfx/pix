"""
Utilities
"""
import sys
import os
import six
import uuid

from .exc import PIXError

from typing import *


ModuleType = type(sys)


def iter_modules(paths):
    # type: (Union[str, Iterable[str]]) -> List[str]
    """
    Get filepaths for all valid python modules from `paths`.
    
    Parameters
    ----------
    paths : Union[str, Iterable[str]]
        Supports various path separation methods: e.g.
           - '/project/package/mymodule.py'
           - '/project/package'
           - '/project/package:project/package/mymodule.py'
           - ['/project/package']

    Returns
    -------
    List[str]
    """
    import pydoc

    if isinstance(paths, six.string_types):
        paths = paths.split(os.pathsep)

    for path in paths:
        path = os.path.expanduser(os.path.expandvars(path))
        # ignore empty paths
        path = path.strip()
        if not path:
            continue

        obj = pydoc.locate(path)
        if obj:
            if obj.__file__.endswith('pyc'):
                yield obj.__file__[:-1]
            else:
                yield obj.__file__
        else:
            if os.path.isfile(path) and path.endswith('py'):
                yield path
            elif os.path.isdir(path):
                for base, directories, filenames in os.walk(path):
                    for filename in filenames:
                        if filename.endswith('py'):
                            yield os.path.join(base, filename)
            else:
                raise PIXError(
                    'Cannot locate plugin path {!r}'.format(path))


def import_modules(paths):
    # type: (Union[str, Iterable[str]]) -> List[ModuleType]
    """
    Import modules from `paths`.

    Parameters
    ----------
    paths : Union[str, Iterable[str]]

    Returns
    -------
    List[ModuleType]
    """

    def _py2_import(name, path):
        # import modules for python 2
        import imp
        return imp.load_source(name, path)

    def _py33_to_34_import(name, path):
        # import modules for python 3.3 and 3.4
        from importlib.machinery import SourceFileLoader
        return SourceFileLoader(name, path).load_module()

    def _py35plus_import(name, path):
        # import modules for python 3.5+
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, path)
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)
        return foo

    if sys.version_info[0] == 3 and sys.version_info[1] in (3, 4):
        loader = _py33_to_34_import
    elif sys.version_info[0] == 3 and sys.version_info[1] >= 5:
        loader = _py35plus_import
    else:
        loader = _py2_import

    return [loader(uuid.uuid4().hex, mod) for mod in set(iter_modules(paths))]
