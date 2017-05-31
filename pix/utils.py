"""
Utilities
"""
import os
import sys
import six


def iter_modules(paths):
    """
    Get filepaths for all valid python modules from `paths`.
    
    Parameters
    ----------
    paths : Union[str, Iterable[str]]
        Supports various path separation methods: e.g.
            '/project/package/mymodule.py'
            '/project/package'
            '/project/package:project/package/mymodule.py'
            ['/project/package']

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
            yield obj.__file__
        else:
            path = os.path.abspath(path)
            if os.path.isfile(path) and path.endswith('py'):
                yield path
            for base, directories, filenames in os.walk(path):
                for filename in filenames:
                    if filename.endswith('py'):
                        yield os.path.join(base, filename)


def import_modules(paths):
    """
    Import modules from `paths`.

    Parameters
    ----------
    paths : Union[str, Iterable[str]]

    Returns
    -------
    List[module]
    """
    import imp
    import uuid

    modules = set(iter_modules(paths))

    results = []
    for mod in modules:
        results.append(imp.load_source(uuid.uuid4().hex, mod))
    return results


class ExpandedPath(object):
    """
    Context manager for temporarily expanding the python path.
    """
    def __init__(self, paths=None):
        self.paths = paths
        self.orig_paths = None

    def __enter__(self):
        if self.paths:
            self.orig_paths = sys.path
            sys.path.extend(self.paths)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.orig_paths is not None:
            sys.path = self.orig_paths
