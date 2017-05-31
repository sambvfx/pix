A python api for interacting with [PIX](www.pixsystem.com/). It's goal is to provide a more object-oriented experience when interacting with PIX's REST API. It provides simplified ways to add custom behaviors to the objects returned from PIX that are specific for your needs.


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



Examples
--------

Inject your own custom behaviors onto the dynamically created PIX objects. These can exist in your own code repository and can be added to the [factory](https://github.com/sambvfx/pix/blob/master/pix/factory.py) via the environment variable `PIX_PLUGIN_PATH`.

For example:

```python
# mypixmodels.py

from pix.factory import register
from pix.model import PIXObject


@register('PIXNote')
class MyPIXNoteExtension(PIXObject):
    def ingest(self):
        print 'Ingesting note!'
        # handle note ingesting

```

Exporting these environment variables before launching our python session simplifies the process within python. However these can also be provided to the `Session` directly if needed.

```bash
$ export PIX_API_URL='project.pixsystem.com'
$ export PIX_APP_KEY='123abc'
$ export PIX_USERNAME='sambvfx'
$ export PIX_PASSWORD='mypassword'
$ export PIX_PLUGIN_PATH=/path/to/mypixmodels.py:/path/to/other/package
```

Our custom `ingest` method is now available on the note!

```python
import pix.api

with pix.api.Session() as session:
    project = session.get_project('PROJECT_NAME')
    for feed in project.iter_unread():
        for note in feed.get_notes():
            note.ingest()
```
