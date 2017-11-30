"""
PIX object/model module.
"""
import functools
import json
import six
import pix.exc
from pix.factory import register


if False:
    from typing import *
    import pix.factory


# TODO: Use MutableMapping instead?
class PIXObject(dict):
    """
    The base PIX object.

    This is simply a wrapper of a dictionary to provide additional helper
    methods and reduce complexity of large data structures.
    """
    # since we're inheriting from dict having __dict__ is redundant
    __slots__ = ()

    def __init__(self, factory, *args, **kwargs):
        """
        Parameters
        ----------
        factory : pix.factory.Factory
            Factory used to generate this instance.
        """
        self.factory = factory
        self.session = factory.session
        super(PIXObject, self).__init__(
            {k: self.factory.objectfy(v)
             for k, v in dict(*args, **kwargs).items()})

    @property
    def identifier(self):
        return self.get('label') or self['id']

    def __repr__(self):
        return '<{0}({1!r})>'.format(
            self.__class__.__name__, str(self.identifier))

    def __dir__(self):
        def get_attrs(obj):
            import types
            if not hasattr(obj, '__dict__'):
                return []
            if not isinstance(obj.__dict__, (dict, types.DictProxyType)):
                raise TypeError(
                    '{0}.__dict__ is not a dictionary'.format(obj.__name__))
            return obj.__dict__.keys()

        def dir2(obj):
            attrs = set()
            if not hasattr(obj, '__bases__'):
                # obj is an instance
                if not hasattr(obj, '__class__'):
                    # slots
                    return sorted(get_attrs(obj))
                klass = obj.__class__
                attrs.update(get_attrs(klass))
            else:
                # obj is a class
                klass = obj

            for cls in klass.__bases__:
                attrs.update(get_attrs(cls))
                attrs.update(dir2(cls))
            attrs.update(get_attrs(obj))
            return list(attrs)

        return dir2(self) + self.keys()

    # TODO: Ditch this behavior. (Backwards incompatible change!)
    # It's probably that at some point a user is going create a method named
    # the same as a key fetched from PIX.
    def __getattr__(self, item):
        # This makes either `self['attribute']` or `self.attribute` work.
        return self[item]

    def children(self):
        """
        Find all children downstream of self.

        Returns
        -------
        List[pix.model.PIXObject]
        """
        results = []
        # iter contents first so we don't include ourselves
        for data in self.factory.iter_contents(self):
            for child in self.factory.iter_children(data, recursive=True):
                results.append(child)
        return results


@register('PIXPlaylist')
@register('PIXFolder')
class PIXContainer(PIXObject):
    """
    Container class requires an additional call to get its contents.
    """
    def get_contents(self):
        """
        Gets the contents of a folder or playlist.
        """
        return self.session.get('/items/{0}/contents'.format(self.id))

    def children(self):
        """
        Find all children downstream of self. This requires additional
        calls to get the contents.

        Returns
        -------
        List[pix.model.PIXObject]
        """
        results = []
        for data in self.get_contents():
            for child in self.factory.iter_children(data, recursive=True):
                results.append(child)
        return results


class _ActiveProject(type):
    """
    Metaclass that wraps all instance methods to first ensure that the project 
    is the active project in the session.
    
    The use of a metaclass has advantages of also affecting instance methods 
    on sub-classes of `PIXProject`.
    """
    @staticmethod
    def activate_project(func):
        """
        Simple decorator for `PIXProject` methods that issue API calls to
        insures the project is set as the active project in the current 
        session.
        """
        @functools.wraps(func)
        def _wrap(self, *args, **kwargs):
            if self.session.active_project != self:
                self.session.load_project(self)
            return func(self, *args, **kwargs)

        return _wrap

    def __new__(cls, name, bases, attrs):
        """
        Get a new project class wrapping any instance methods to ensure the 
        project instance is the active project within the current session.
        """
        newattrs = {}
        for k, v in attrs.items():
            if callable(v):
                newattrs[k] = cls.activate_project(v)
            else:
                newattrs[k] = v

        return super(_ActiveProject, cls).__new__(cls, name, bases, newattrs)


@register('PIXProject')
@six.add_metaclass(_ActiveProject)
class PIXProject(PIXObject):
    """
    Represents a PIX project.
    
    The PIXProject has some additional magic where it will switch the current
    session's active project when any instance methods are called. See 
    `_ActiveProject` metaclass for more information.
    """
    def load_item(self, item_id):
        """
        Loads an item from PIX.
        """
        return self.session.get('/items/{0}'.format(item_id))

    def get_inbox(self, limit=None):
        """
        Load logged-in user's inbox

        Parameters
        ----------
        limit : int
        """
        url = '/feeds/incoming'
        if limit is not None:
            url += '?limit={0}'.format(limit)
        return self.session.get(url)

    def iter_unread(self):
        """
        Find all unread messages.

        Returns
        -------
        Iterator[PIXShareFeedEntry]
        """
        for feed in self.get_inbox():
            if not feed.viewed:
                yield feed

    def mark_as_read(self, item):
        """
        Mark's an item in logged-in user's inbox as read.

        Parameters
        ----------
        item : PIXObject
        """
        return self.session.put(
            '/items/{0}'.format(item['id']),
            json.dumps({'flags': {'viewed': 'true'}}))

    def delete_inbox_item(self, item):
        """
        Delete item from the inbox.

        Parameters
        ----------
        item : PIXObject
        """
        return self.session.delete('/messages/inbox/{0}'.format(item['id']))


@register('PIXShareFeedEntry')
class PIXShareFeedEntry(PIXObject):
    """
    Class representing a feed.
    """
    def mark_as_read(self):
        """
        Mark's an item in logged-in user's inbox as read.
        """
        return self.session.put(
            '/items/{0}'.format(self['id']),
            json.dumps({'flags': {'viewed': 'true'}}))

    def iter_attachments(self):
        """
        Iterate over the feeds attachments.

        Returns
        -------
        Iterator[PIXObject]
        """
        for attachment in self.attachments['list']:
            yield attachment

    def get_attachment(self, name):
        """
        Return the first attachment found with a specific name.

        Parameters
        ----------
        name : str

        Returns
        -------
        PIXObject
        """
        # FIXME: any way to optimize this?
        for x in self.iter_attachments():
            identifier = x.get('label') or x['id']
            if identifier == name:
                return x


@register('PIXClip')
@register('PIXImage')
class PIXAttachment(PIXObject):
    """
    Class representing an attached item.
    """
    def get_notes(self, limit=None):
        """
        Get notes.

        Parameters
        ----------
        limit : int
            Specify a limit of notes to return to the REST call.
            NOTE: It appears the default limit if this argument is not provided
                  is 50?

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


@register('PIXNote')
class PIXNote(PIXObject):
    """
    Class representing a note.
    """
    def get_media(self, media_type):
        """
        Get media from a note.

        Parameters
        ----------
        media_type : str
            {'original', 'markup', 'composite'}

        Returns
        -------
        bytes
        """
        # special original behavior if there is a start_frame
        if media_type == 'original' and self.fields['start_frame'] is not None:
            headers = {'Accept': 'image/png'}
            url = '/media/{0}/frame/{1}'.format(
                self.fields['parent_id'], self.fields['start_frame'])
        else:
            headers = {'Accept': 'text/xml'}
            url = '/media/{0}/{1}'.format(self['id'], media_type)

        with self.session.header(headers):
            response = self.session.get(url)

        if response.status_code == 200:
            return response.content

        raise pix.exc.PIXError(response.reason)
