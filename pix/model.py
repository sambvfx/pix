"""
PIX object/model module.
"""
import functools
import json
import pix.factory
import pix.exc


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
        factory : ``pix.factory.Factory``
            Factory used to generate this instance.
        """
        self.factory = factory
        self.session = factory.session
        super(PIXObject, self).__init__(
            {k: self.factory.objectfy(v)
             for k, v in dict(*args, **kwargs).iteritems()})

    def __repr__(self):
        identifier = self.get('label') or self['id']
        return '<{0}({1!r})>'.format(self.__class__.__name__, str(identifier))

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
        list[``pix.model.PIXObject``]
        """
        results = []
        # iter contents first so we don't include ourselves
        for data in self.factory.iter_contents(self):
            for child in self.factory.iter_children(data, recursive=True):
                results.append(child)
        return results


@pix.factory.Factory.register('PIXPlaylist')
@pix.factory.Factory.register('PIXFolder')
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
        list[``pix.model.PIXObject``]
        """
        results = []
        for data in self.get_contents():
            for child in self.factory.iter_children(data, recursive=True):
                results.append(child)
            return results


def activate_project(func):
    """
    Simple decorator for ``PIXProject`` methods that issue API calls to
    insures the project is set as the active project in the current session.
    """
    @functools.wraps(func)
    def _wrap(self, *args, **kwargs):
        self.set_active()
        return func(self, *args, **kwargs)
    return _wrap


@pix.factory.Factory.register('PIXProject')
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
    def get_inbox(self, limit=25):
        """
        Load logged-in user's inbox
        """
        assert isinstance(limit, int)
        url = "/feeds/incoming?limit={0}".format(limit)
        return self.session.get(url)

    @activate_project
    def mark_as_read(self, item):
        """
        Mark's an item in logged-in user's inbox as read.
        """
        url = "/items/{0}".format(item['id'])
        payload = json.dumps({'flags': {'viewed': 'true'}})
        return self.session.put(url, payload)

    @activate_project
    def delete_inbox_item(self, item):
        """
        Delete item from inbox
        """
        url = "/messages/inbox/{0}".format(item['id'])
        return self.session.delete(url)


@pix.factory.Factory.register('PIXClip')
@pix.factory.Factory.register('PIXImage')
class PIXAttachment(PIXObject):
    """
    Class representing an attached item.
    """
    def get_notes(self):
        """
        Get notes.
        """
        if self['notes']['has_notes']:
            url = '/items/{0}/notes?limit=100'.format(self['id'])
            return self.session.get(url)
        return []


@pix.factory.Factory.register('PIXNote')
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
        ``PIL.Image`` | None
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
        ``PIL.Image`` | None
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
        ``PIL.Image``
        """
        bg = self.get_original()
        if bg is None:
            raise pix.exc.PIXError('No original image found!')
        fg = self.get_markup()
        if fg is None:
            raise pix.exc.PIXError('No markup found!')
        bg.paste(fg, (0, 0), fg)
        return bg
