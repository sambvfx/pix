"""
PIX class factory module.
"""
from typing import TYPE_CHECKING, Mapping, overload

if TYPE_CHECKING:
    from typing import (
        TypeVar, List, Dict, Callable, Iterator, Type, Any, Union, Set, Tuple
    )
    from .api import Session
    from .model import PIXObject

    T = TypeVar('T')


__all__ = [
    'Factory',
]


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
    using any registered base classes (or `pix.model.PIXObject` if there are
    none registered).
    """
    # registered bases
    _registered = {}  # type: Dict[str, List[Type[PIXObject]]]

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
            bases.insert(0, klass)
            cls._registered[name] = bases
            return klass

        return _deco

    @classmethod
    def build(cls, name):
        # type: (str) -> Type[PIXObject]
        """
        Build a pix object class with the given name. Any registered bases
        keyed for `name` will be used as a base class.

        Parameters
        ----------
        name : str
            PIX class name. e.g. 'PIXImage'

        Returns
        -------
        Type[PIXObject]
        """
        # import here avoids circular import errors
        from .model import PIXObject
        # look for registered base classes and if none use the base object
        bases = cls._registered.get(str(name), [])
        # ensure we have at least one PIXObject base class
        if not any(issubclass(x, PIXObject) for x in bases):
            bases.append(PIXObject)
        klass = type(str(name), tuple(bases), {})  # type: Type[PIXObject]
        klass.__name__ = str(name)
        return klass

    @classmethod
    def iter_contents(cls, data):
        # type: (Mapping) -> Iterator[Mapping]
        """
        Iter the immediate contents of `data` and yield any dictionaries.
        Does not recurse.

        Parameters
        ----------
        data : Mapping

        Returns
        -------
        Iterator[Mapping]
        """
        for k, v in data.items():
            if isinstance(v, Mapping):
                yield v
            elif isinstance(v, (list, tuple, set)):
                for l in v:
                    if isinstance(l, Mapping):
                        yield l

    def iter_children(self, data, recursive=True):
        # type: (Mapping, bool) -> Iterator[PIXObject]
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
        Iterator[PIXObject]
        """
        name = data.get('class')
        if name:
            klass = self.build(name)
            yield klass(self, data)
        if recursive:
            for x in self.iter_contents(data):
                for obj in self.iter_children(x):
                    yield obj

    @overload
    def objectfy(self, data):
        # type: (PIXObject) -> PIXObject
        pass

    @overload
    def objectfy(self, data):
        # type: (Mapping[str, T]) -> Union[PIXObject, Mapping[str, Union[T, PIXObject]]]
        pass

    @overload
    def objectfy(self, data):
        # type: (List[T]) -> List[Union[PIXObject, T]]
        pass

    @overload
    def objectfy(self, data):
        # type: (Set[T]) -> Set[Union[PIXObject, T]]
        pass

    @overload
    def objectfy(self, data):
        # type: (Tuple[T, ...]) -> Tuple[Union[PIXObject, T], ...]
        pass

    # @overload
    # def objectfy(self, data):
    #     # type: (T) -> T
    #     pass

    def objectfy(self, data):
        # type: (Any) -> Any
        """
        Replace any viable structures with `PIXObject`.

        Parameters
        ----------
        data : Any
            Can be a variety of types.

        Returns
        -------
        Any
        """
        from .model import PIXObject

        if isinstance(data, PIXObject):
            return data
        elif isinstance(data, Mapping):
            name = data.get('class')
            if name:
                klass = self.build(name)
                return klass(self, data)
            else:
                # Mapping isn't a valid runtime type so data is some subclass.
                # We want to maintain it's original type.
                # NOTE: Hopefully order isn't important?
                return data.__class__(  # type: ignore[call-arg]
                    {k: self.objectfy(v) for k, v in data.items()})
        elif isinstance(data, (list, tuple, set)):
            return data.__class__(self.objectfy(x) for x in data)
        else:
            return data
