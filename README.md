PIX Python API
--------------

[![Build Status](https://travis-ci.org/sambvfx/pix.svg?branch=master)](https://travis-ci.org/sambvfx/pix)

A python api for interacting with [PIX](http://www.pixsystem.com/). It's goal is to provide a more object-oriented experience when interacting with PIX's REST API. It provides simplified ways to add custom behaviors to the objects returned from PIX that are specific for your needs.


Building
-----

###### Install from pypi:

```bash
pip install pix-api
```

*OR*

###### Install from source:

```bash
git clone https://github.com/sambvfx/pix.git
cd pix
pip install -e .
```

> NOTE: If you wish to contribute back please install the tests dependencies using the `tests` bundle.

```bash
pip install -e ".[tests]"
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
import pix


session = pix.Session()
projects = session.get_projects()
print(projects)
# [<PIXProject('MyProject')>]
project = session.load_project('MyProject')
```

From here we can issue some commands provided by our default [models](https://github.com/sambvfx/pix/blob/master/pix/model.py). For example getting all unread inbox messages.

```python
import pix


session = pix.Session()

project = session.load_project('MyProject')

# print unread inbox messages
for feed in project.get_inbox():
    # Skip stuff we've already marked as viewed.
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

import pix


@pix.register('PIXNote')
class MyPIXNote(pix.PIXObject):
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
        for attachment in feed.get_attachments():
            for note in attachment.get_notes():
                note.ingest()
```

Samples
-------
Check out [samples](https://github.com/sambvfx/pix/tree/master/samples) for various examples to get started.

> NOTE: Some samples may require thirdparty libraries or other things to be installed to work properly. Check each sample's documentation for further instructions.
