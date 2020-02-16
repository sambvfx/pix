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

The internals of `pix` are driven by a class [factory](https://github.com/sambvfx/pix/blob/master/pix/factory.py) that dynamically builds classes from the json data returned from the REST endpoints. Users have the ability to register base classes that are injected into these dynamic classes to provide customized behaviors.
The objects created by the factory are dictionary-like objects where data returned by the servers can be accessed like a dictionary (e.g. `obj['key']`).

There's a handful of provided [models](https://github.com/sambvfx/pix/blob/master/pix/model.py) that the dynamic objects will include by default. These provide helper methods for common use-cases.

```python
import pix


session = pix.Session()
session.login()

project = session.load_project('MyProject')

# print unread inbox messages
for feed in project.get_inbox():

    # feed  # type: pix.model.PIXShareFeedEntry

    # Skip stuff we've already marked as viewed.
    if not feed['viewed']:
        print('{!r} -> {!r} : {!r}'.format(
            feed.sender, feed.recipients, feed.message))

session.logout()
```


Extending
---------

The provided [models](https://github.com/sambvfx/pix/blob/master/pix/model.py) have some standard helpful methods on them, but what about running your own logic? You can inject your own custom behaviors onto the dynamically created PIX objects. These can exist in your own code repository and can be added to the [factory](https://github.com/sambvfx/pix/blob/master/pix/factory.py) via the environment variable `PIX_PLUGIN_PATH`.

```python
# mypixmodels.py

import pix


@pix.register('PIXNote')
class MyPIXNote:

    def ingest(self):
        print('Ingesting note!')
```

As long as the `PIX_PLUGIN_PATH` has `mypixmodels.py` available the returned `PIXNote` objects will have the custom `ingest` method on them.

```python
import pix


# When used as a context manager, a Session will automatically login/logout.
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
