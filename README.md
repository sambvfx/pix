A python api for interacting with [PIX](www.pixsystem.com/). It's goal is to provide a more object-oriented experience when interacting with PIX's REST API. It provides simplified ways to add custom behaviors to the objects returned from PIX that are specific for your needs.

```
import pix.factory
from pix.model import PIXObject


@pix.factory.Factory.register('PIXNote')
class MyPIXNoteExtension(PIXObject):
    def custom_method(self):
        ...
```

 Check out `pix.model` for a few simple examples. Additional contributions are welcomed to expand the base set of helper methods available!

###Environment Variables 
    TIP: *set these before launching*
`PIX_API_URL` : URL to the PIX API (currently "project.pixsystem.com") 
`PIX_APP_KEY` : PIX API key provided through the PIX developer portal
`PIX_USERNAME` : PIX username
`PIX_PASSWORD` : PIX password
