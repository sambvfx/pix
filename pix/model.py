"""
PIX object/model module.
"""
import functools
import json
import pix.exc
from pix.factory import register

from typing import TYPE_CHECKING, Iterator, Optional, Dict


if TYPE_CHECKING:
    import pix.factory


class PIXObject(dict):
    """
    The base PIX object.

    This is simply a wrapper of a dictionary to provide additional helper
    methods and reduce complexity of large data structures.
    """
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

    def __getattr__(self, item):
        # This makes either self['attribute'] or self.attribute work.
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
        Getes the contents of a folder or playlist.
        """
        url = '/items/{0}/contents'.format(self.id)
        result = self.session.get(url)
        return result

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


def activate_project(func):
    """
    Simple decorator for `PIXProject` methods that issue API calls to
    insures the project is set as the active project in the current session.
    """
    @functools.wraps(func)
    def _wrap(self, *args, **kwargs):
        self.set_active()
        return func(self, *args, **kwargs)
    return _wrap


@register('PIXProject')
class PIXProject(PIXObject):
    """
    A project is where most of the interfacing currently takes place because
    the content we fetch is dependent on the current project loaded. Any API
    call that returns results differently depending on the current loaded
    project should live here.
    """
    def set_active(self):
        """
        Log into a project.
        """
        if self.session.active_project != self:
            self.session.load_project(self)

    @activate_project
    def load_item(self, item_id):
        """
        Loads an item from PIX.
        """
        url = '/items/{0}'.format(item_id)
        return self.session.get(url)

    @activate_project
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

    @activate_project
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

    @activate_project
    def mark_as_read(self, item):
        """
        Mark's an item in logged-in user's inbox as read.

        Parameters
        ----------
        item : PIXObject
        """
        url = '/items/{0}'.format(item['id'])
        payload = json.dumps({'flags': {'viewed': 'true'}})
        return self.session.put(url, payload)

    @activate_project
    def delete_inbox_item(self, item):
        """
        Delete item from the inbox.

        Parameters
        ----------
        item : PIXObject
        """
        url = '/messages/inbox/{0}'.format(item['id'])
        return self.session.delete(url)


@register('PIXShareFeedEntry')
class PIXShareFeedEntry(PIXObject):
    """
    Class representing a feed.
    """
    def mark_as_read(self):
        """
        Mark's an item in logged-in user's inbox as read.
        """
        url = '/items/{0}'.format(self['id'])
        payload = json.dumps({'flags': {'viewed': 'true'}})
        return self.session.put(url, payload)

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
        """
        with self.session.header({'Accept': 'text/xml'}):
            url = '/media/{0}/{1}'.format(self['id'], media_type)
            response = self.session.get(url)
        if response.status_code == 200:
            return response.text
        raise pix.exc.PIXError(response.reason)

    def _get_original(self):
        """
        Get the original media from a note.
        """
        frame = self.fields['start_frame']
        if frame is not None:
            with self.session.header({'Accept': 'image/png'}):
                url = '/media/{0}/frame/{1}'.format(
                    self.fields['parent_id'], frame)
                response = self.session.get(url)
            return response.content
        else:
            return self.get_media('original')

    def get_original(self):
        """
        Get the notes original media as an Image buffer.

        Returns
        -------
        Optional[PIL.Image]
        """
        results = self._get_original()
        if results:
            import io
            from PIL import Image
            return Image.open(io.BytesIO(results))

    def get_markup(self):
        """
        Get the notes markup as an Image buffer.

        Returns
        -------
        Optional[PIL.Image]
        """
        results = self.get_media('markup')
        if results:
            import io
            import cairosvg.surface
            from PIL import Image
            return Image.open(io.BytesIO(
                cairosvg.surface.PNGSurface.convert(bytestring=results)))

    def get_composite(self):
        """
        Get a composite Image buffer of the original image and the markup.

        Returns
        -------
        Optional[PIL.Image]
        """
        # FIXME: There should be a endpoint that returns this already
        # composited together.
        bg = self.get_original()
        fg = self.get_markup()
        if bg and fg:
            bg.paste(fg, (0, 0), fg)
            return bg
