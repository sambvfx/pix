"""
PIX class factory module.
"""
from typing import TYPE_CHECKING, Type, Iterator, Dict


if TYPE_CHECKING:
    import pix.api
    import pix.model


class Factory(object):
    """
    A Factory is repsonsible for dynamically building dict-like objects from
    the data returned from the PIX endpoints. Additionally these dynamically
    built objects can have base class(es) registered for them that can supply
    additional helper methods or behaviors. This allows for a more
    object-oriented interface and reduces the complexity of the large data
    structures returned from PIX.

    A base class for a given PIX class can be registered via the `register`
    method given the PIX class name. Any structure (dict) returned from a PIX
    request that contains a key 'class' is premoted to an object using any
    registered base classes (or ``pix.model.PIXObject`` if there are none
    registered).
    """
    # registered bases
    _registered = {}

    def __init__(self, session):
        """
        Parameters
        ----------
        session : pix.api.Session
        """
        self.session = session

    @classmethod
    def register(cls, name):
        """
        Decorator for registering an new PIX base class.

        Parameters
        ----------
        name : str
            PIX class name. e.g. 'PIXImage'
        """
        def _deco(klass):
            bases = cls._registered.get(name, [])
            bases.append(klass)
            cls._registered[name] = bases
            return klass

        return _deco

    @classmethod
    def build_obj(cls, name):
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
        Type[pix.model.PIXObject]
        """
        import pix.model
        # look for registered base classes and if none use the base object
        bases = cls._registered.get(str(name), [pix.model.PIXObject])
        obj = type(str(name), tuple(bases), {})
        obj.__name__ = str(name)
        return obj

    @classmethod
    def iter_contents(cls, data):
        """
        Iter the immediate contents of `data` and yield any dictionaries.
        Does not recurse.

        Parameters
        ----------
        data : dict

        Returns
        -------
        Iterator[dict]
        """
        for k, v in data.items():
            if isinstance(v, dict):
                yield v
            elif isinstance(v, (set, list, tuple)):
                for l in v:
                    if isinstance(l, dict):
                        yield l

    def iter_children(self, data, recursive=True):
        """
        Iterate over the children objects of `data`.

        Parameters
        ----------
        data : dict
        recursive : bool
            Recursively look into generated objects and include their children
            too.

        Returns
        -------
        Iterator[pix.model.PIXObject]
        """
        name = data.get('class')
        if name:
            obj = self.build_obj(name)
            yield obj(self, data)
        if recursive:
            for x in self.iter_contents(data):
                for obj in self.iter_children(x):
                    yield obj

    def objectfy(self, data):
        """
        Replace any viable structures with `pix.model.PIXObject`.
        
        Parameters
        ----------
        data : Union[Dict[str, Any], Any]
        
        Returns
        -------
        Union[pix.model.PIXObject, Dict[str, Any], Any]
        """
        if isinstance(data, dict):
            name = data.get('class')
            if name:
                obj = self.build_obj(name)
                return obj(self, data)
            else:
                return {k: self.objectfy(v) for k, v in data.items()}
        elif isinstance(data, (tuple, list, set)):
            results = [self.objectfy(x) for x in data]
            if isinstance(data, tuple):
                results = tuple(results)
            elif isinstance(data, set):
                results = set(results)
            return results
        else:
            return data


# to make registration easier...
register = Factory.register
