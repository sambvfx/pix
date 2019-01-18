"""
PIX class factory module.
"""
from typing import *


if TYPE_CHECKING:
    from .api import Session
    from .model import PIXObject


T = TypeVar('T')


class Factory(object):
    """
    A Factory is repsonsible for dynamically building dict-like objects from
    the data returned from the PIX endpoints. Additionally these dynamically
    built objects can have base class(es) registered for them that can supply
    additional helper methods or behaviors. This allows for a more
    object-oriented interface and reduces the complexity of the large data
    structures returned from PIX.

    A base class for a given PIX class can be registered via the `register`
    method given the PIX class name. Any structure returned from a PIX request
    that contains dictionaries with a key 'class' is premoted to an object
    using any registered base classes (or ``pix.model.PIXObject`` if there are
    none registered).
    """
    # registered bases
    _registered = {}  # type: Dict[str, PIXObject]

    def __init__(self, session):
        # type: (Session) -> None
        """
        Parameters
        ----------
        session : Session
        """
        self.session = session

    @classmethod
    def register(cls, name):
        # type: (str) -> Callable
        """
        Decorator for registering an new PIX base class.

        Parameters
        ----------
        name : str
            PIX class name. e.g. 'PIXImage'

        Returns
        -------
        Callable
        """
        def _deco(klass):
            bases = cls._registered.get(name, [])
            bases = [x for x in bases if not issubclass(klass, x)]
            bases.append(klass)
            cls._registered[name] = bases
            return klass

        return _deco

    @classmethod
    def build(cls, name):
        # type: (str) -> type
        """
        Build a pix object class with the given name. Any registered bases
        keyed for `name` will be used or the base ``pix.model.PIXObject``
        class.

        Parameters
        ----------
        name : str
            PIX class name. e.g. 'PIXImage'

        Returns
        -------
        type
            Type[PIXObject]
        """
        # import here avoids circular import errors
        from .model import PIXObject
        # look for registered base classes and if none use the base object
        bases = cls._registered.get(str(name), [PIXObject])
        obj = type(str(name), tuple(bases), {})
        obj.__name__ = str(name)
        return obj

    @classmethod
    def iter_contents(cls, data):
        # type: (Mapping) -> Generator[Mapping]
        """
        Iter the immediate contents of `data` and yield any dictionaries.
        Does not recurse.

        Parameters
        ----------
        data : Mapping

        Returns
        -------
        Generator[Mapping]
        """
        for k, v in data.items():
            if isinstance(v, Mapping):
                yield v
            elif isinstance(v, (list, tuple, set)):
                for l in v:
                    if isinstance(l, Mapping):
                        yield l

    def iter_children(self, data, recursive=True):
        # type: (Mapping, bool) -> Generator[PIXObject]
        """
        Iterate over the children objects of `data`.

        Parameters
        ----------
        data : Mapping
        recursive : bool
            Recursively look into generated objects and include their children
            too.

        Returns
        -------
        Generator[PIXObject]
        """
        name = data.get('class')
        if name:
            obj = self.build(name)
            yield obj(self, data)
        if recursive:
            for x in self.iter_contents(data):
                for obj in self.iter_children(x):
                    yield obj

    def objectfy(self, data):
        # type: (T) -> Union[PIXObject, T]
        """
        Replace any viable structures with `PIXObject`.

        Parameters
        ----------
        data : T

        Returns
        -------
        Union[PIXObject, T]
        """
        if isinstance(data, MutableMapping):
            name = data.get('class')
            if name:
                obj = self.build(name)
                return obj(self, data)
            else:
                return data.__class__(
                    {k: self.objectfy(v) for k, v in data.items()})
        elif isinstance(data, (list, tuple, set)):
            return data.__class__(self.objectfy(x) for x in data)
        else:
            return data


# expose to make registration easier
register = Factory.register
