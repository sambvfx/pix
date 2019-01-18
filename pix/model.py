"""
A collection of pre-built PIX object/models.
"""
import functools
import six
import collections

from typing import *

from .factory import Factory
from .exc import PIXError


class PIXObject(collections.MutableMapping):
    """
    The base PIX object.
    """
    def __init__(self, factory, *args, **kwargs):
        # type: (Factory, *Any, **Any) -> None
        """
        Parameters
        ----------
        factory : Factory
            The factory used to generate this instance.
        args : *Any
        kwargs : **Any
        """
        self.factory = factory
        self.session = factory.session

        self._store = {k: self.factory.objectfy(v)
                       for k, v in dict(*args, **kwargs).items()}

    def __repr__(self):
        return '<{0}({1!r})>'.format(
            self.__class__.__name__, str(self.identifier))

    def __getitem__(self, key):
        return self._store[key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self):
        return len(self._store)

    def __delitem__(self, key):
        del self._store[key]

    def __setitem__(self, key, value):
        self._store[key] = value

    @property
    def identifier(self):
        # type: () -> str
        """
        Returns
        -------
        str
        """
        return self.get('label') or self['id']

    def children(self):
        # type: () -> List[PIXObject]
        """
        Find all children downstream of self.

        Returns
        -------
        List[PIXObject]
        """
        results = []
        # iter contents first so we don't include ourselves
        for data in self.factory.iter_contents(self):
            for child in self.factory.iter_children(data, recursive=True):
                results.append(child)
        return results


class _ActiveProject(GenericMeta):
    """
    Metaclass that wraps all instance methods to first ensure that the project 
    is the active project in the session.
    
    The use of a metaclass (rather than a decorator for example) has
    advantages of also affecting instance methods on sub-classes of
    `PIXProject`.
    """
    @staticmethod
    def activate_project(func):
        # type: (Callable) -> Callable
        """
        Simple decorator for `PIXProject` methods that issue API calls to
        insures the project is set as the active project in the current 
        session.

        Parameters
        ----------
        func : Callable

        Returns
        -------
        Callable
        """
        @functools.wraps(func)
        def _wrap(self, *args, **kwargs):
            if self.session.active_project != self:
                self.session.load_project(self)
            return func(self, *args, **kwargs)

        return _wrap

    def __new__(mcs, name, bases, attrs):
        """
        Get a new project class wrapping any instance methods to ensure the 
        project instance is the active project within the current session.
        """
        newattrs = {}
        for k, v in attrs.items():
            if callable(v):
                newattrs[k] = mcs.activate_project(v)
            else:
                newattrs[k] = v

        return super(_ActiveProject, mcs).__new__(mcs, name, bases, newattrs)


@Factory.register('PIXProject')
@six.add_metaclass(_ActiveProject)
class PIXProject(PIXObject):
    """
    Represents a PIX project.
    
    The PIXProject has some additional magic where it will switch the current
    session's active project when any instance methods are called. See 
    `_ActiveProject` metaclass for more information.
    """
    def load_item(self, item_id):
        # type: (str) -> Optional[PIXObject]
        """
        Loads an item from PIX.

        Parameters
        ----------
        item_id : str

        Returns
        -------
        Optional[PIXObject]
        """
        result = self.session.get('/items/{0}'.format(item_id))
        if isinstance(result, PIXObject):
            return result

    def get_inbox(self, limit=None):
        # type: (Optional[int]) -> List[PIXShareFeedEntry]
        """
        Load logged-in user's inbox

        Parameters
        ----------
        limit : Optional[int]

        Returns
        -------
        List[PIXShareFeedEntry]
        """
        url = '/feeds/incoming'
        if limit is not None:
            url += '?limit={0}'.format(limit)
        return self.session.get(url)

    def mark_as_read(self, item):
        # type: (PIXObject) -> None
        """
        Mark's an item in logged-in user's inbox as read.

        Parameters
        ----------
        item : PIXObject
        """
        return self.session.put(
            '/items/{0}'.format(item['id']),
            payload={'flags': {'viewed': 'true'}})

    def delete_inbox_item(self, item):
        # type: (PIXObject) -> None
        """
        Delete item from the inbox.

        Parameters
        ----------
        item : PIXObject
        """
        return self.session.delete('/messages/inbox/{0}'.format(item['id']))


@Factory.register('PIXUser')
class PIXUser(PIXObject):
    """
    Class representing a user.
    """
    @property
    def name(self):
        # type: () -> str
        return self['label']


@Factory.register('PIXPlaylist')
@Factory.register('PIXFolder')
class PIXContainer(PIXObject):
    """
    Container class requires an additional call to get its contents.
    """
    def get_contents(self):
        # type: () -> List[Dict]
        """
        Gets the contents of a folder or playlist.

        Returns
        -------
        List[Dict]
        """
        return self.session.get('/items/{0}/contents'.format(self['id']))

    def children(self):
        # type: () -> List[PIXObject]
        """
        Find all children downstream of self. This requires additional
        calls to get the contents.

        Returns
        -------
        List[PIXObject]
        """
        results = []
        for data in self.get_contents():
            for child in self.factory.iter_children(data, recursive=True):
                results.append(child)
        return results


@Factory.register('PIXShareFeedEntry')
class PIXShareFeedEntry(PIXObject):
    """
    Class representing a feed. A feed is an inbox item similar to an email
    message. They contain the text of the message and can optionally have
    attachments.
    """
    @property
    def sender(self):
        # type: () -> PIXUser
        results = self['from']['list']
        assert len(results) == 1
        return results[0]

    @property
    def recipients(self):
        # type: () -> List[PIXUser]
        return self['to']['list']

    @property
    def message(self):
        # type: () -> str
        return self['text']

    def mark_as_read(self):
        """
        Mark's an item in logged-in user's inbox as read.
        """
        return self.session.put(
            '/items/{0}'.format(self['id']),
            payload={'flags': {'viewed': 'true'}})

    def get_attachments(self):
        # type: () -> List[PIXAttachment]
        """
        Get the feed attachments.

        Returns
        -------
        List[PIXAttachment]
        """
        results = []
        for attachment in self['attachments']['list']:
            if isinstance(attachment, PIXContainer):
                results.extend(attachment.get_contents())
            elif isinstance(attachment, PIXAttachment):
                results.append(attachment)
        return results


class PIXAttachment(PIXObject):
    """
    Class representing an attached item.
    """
    def get_notes(self, limit=None):
        # type: (Optional[int]) -> List[PIXNote]
        """
        Get notes.

        Parameters
        ----------
        limit : Optional[int]
            Specify a limit of notes to return to the REST call.
            NOTE: It appears the default limit if this argument is not
                  provided is 50?

        Returns
        -------
        List[PIXNote]
        """
        if self['notes']['has_notes']:
            url = '/items/{0}/notes'.format(self['id'])
            if limit is not None:
                url += '?limit={0}'.format(limit)
            return self.session.get(url)
        return []


@Factory.register('PIXClip')
class PIXClip(PIXAttachment):
    pass


@Factory.register('PIXImage')
class PIXImage(PIXAttachment):
    pass


@Factory.register('PIXNote')
class PIXNote(PIXObject):
    """
    Class representing a note.
    """
    def get_media(self, media_type):
        # type: (str) -> IO[str]
        """
        Get media from a note.

        Parameters
        ----------
        media_type : str
            {'original', 'markup', 'composite'}

        Returns
        -------
        IO[str]
        """
        # special original behavior if there is a start_frame
        if media_type == 'original' and \
                self['fields'].get('start_frame') is not None:
            headers = {'Accept': 'image/png'}
            url = '/media/{0}/frame/{1}'.format(
                self['fields']['parent_id'], self['fields']['start_frame'])
        else:
            headers = {'Accept': 'text/xml'}
            url = '/media/{0}/{1}'.format(self['id'], media_type)

        with self.session.header(headers):
            response = self.session.get(url)

        if response.status_code != 200:
            raise PIXError(response.reason)

        return response.content
