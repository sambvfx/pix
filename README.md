A python api for interacting with [PIX](http://www.pixsystem.com/). It's goal is to provide a more object-oriented experience when interacting with PIX's REST API. It provides simplified ways to add custom behaviors to the objects returned from PIX that are specific for your needs.


Setup
-----
First clone the repo somewhere.

```bash
git clone https://github.com/sambvfx/pix.git
cd pix
pip install -r requirements.txt .
```


If you wish to contribute back please install the test dependencies using the `tests` bundle.

```bash
pip install ".[tests]"
```


Basics
------

Interacting with PIX requires a `Session` object. This is the object that manages all the API calls to PIX's REST endpoints.

```python
import pix


session = pix.Session(
    app_url='https://project.pixsystem.com/developer/api/2',
    app_key='123abc',
    username='sambvfx',
    password='mypassword',
    plugin_paths='/path/to/mypixmodels.py:/path/to/other/package',
)
```

The `Session` arguments can also be sourced from enviornment variables which simplifies instantiation.

```bash
$ export PIX_API_URL='https://project.pixsystem.com/developer/api/2'
$ export PIX_APP_KEY='123abc'
$ export PIX_USERNAME='sambvfx'
$ export PIX_PASSWORD='mypassword'
$ export PIX_PLUGIN_PATH='/path/to/mypixmodels.py:/path/to/other/package'
```

Once we have a session, before we issue any API calls a project needs to be activated. Returned results will change depending on the active project.

```python
from __future__ import print_function
import pix


session = pix.Session()
projects = session.get_projects()
print(projects)
# [<PIXProject('MyProject')>]
project = session.load_project('MyProject')
```

From here we can issue some commands provided by our default [models](https://github.com/sambvfx/pix/blob/master/pix/model.py). For example getting all unread inbox messages.

```python
from __future__ import print_function
import pix


session = pix.Session()

project = session.load_project('MyProject')

# print unread inbox messages
for feed in project.get_inbox():
    if feed['viewed']:
        continue
    print('{!r} -> {!r} : {!r}'.format(
        feed.sender, feed.recipients, feed.message))

session.logout()
```


Extending
---------

Inject your own custom behaviors onto the dynamically created PIX objects. These can exist in your own code repository and can be added to the [factory](https://github.com/sambvfx/pix/blob/master/pix/factory.py) via the environment variable `PIX_PLUGIN_PATH`.

```python
# mypixmodels.py

from __future__ import print_function
import pix

@pix.register('PIXNote')
class MyPIXNoteExtension(pix.PIXObject):
    def ingest(self):
        print('Ingesting note!')
        # handle note ingesting
```

As long as the `PIX_PLUGIN_PATH` has `mypixmodels.py` available the returned `PIXNote` objects will have the custom `ingest` method on them.

```python
import pix

with pix.Session() as session:
    project = session.load_project('MyProject')
    for feed in project.get_inbox():
        if feed['viewed']:
            continue
        for attachment in feed.get_attachments():
            for note in attachment.get_notes():
                note.ingest()
```

Samples
-------

The `pix.PIXProject` object uses a special metaclass that will ensure it's the active project in the session for each method that gets called. This allows for the use of the project class by itself.

```python
import datetime
import pathlib

import pix

from typing import *


if TYPE_CHECKING:
    import io
    from PIL import Image


class MyCustomProject(pix.PIXProject):
    """
    Custom project subclass
    """
    def __init__(self, factory=None, *args, **kwargs):
        if factory is None:
            session = pix.Session()
            factory = session.factory
        super(MyCustomProject, self).__init__(factory, *args, **kwargs)

    def get_ingest_dir(self, date=None):
        # type: (Optional[str]) -> pathlib.Path
        """
        Get the note ingestion path.

        Parameters
        ----------
        date : Optional[str]
            e.g. '2018.04.03'

        Returns
        -------
        pathlib.Path
        """
        if date is None:
            date = datetime.datetime.today().strftime('%Y.%m.%d')

        # e.g. '/Volumes/projects/projectname/notes/2018.04.03'
        return pathlib.Path(
            'Volumes',
            'projects',
            self.identifier,
            'notes',
            date
        )

    def ingest(self, path=None):
        # type: (Optional[pathlib.Path]) -> List[pathlib.Path]
        """
        Get all unread note composite images and save them to disk

        Parameters
        ----------
        path : Optional[pathlib.Path]
            Optional path to directory where to collect note composites.

        Returns
        -------
        List[pathlib.Path]
        """
        import io
        from PIL import Image

        if path is None:
            path = self.get_ingest_dir()

        results = []
        for feed in self.get_inbox():
            for attachment in feed.get_attachments():
                for note in attachment.get_notes():
                    if note['viewed']:
                        continue
                    image_bytes = note.get_media('composite')
                    img = Image.open(io.BytesIO(image_bytes))
                    outpath = path / note.identifier
                    img.save(outpath)
                    self.mark_as_read(note)
                    results.append(outpath)
        return results


project = MyCustomProject(id='jurassicpark')
project.ingest()
```
