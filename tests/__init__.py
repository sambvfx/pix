import os

import pix.api

os.environ['PIX_API_URL'] = 'https://project.pixsystem.com/developer/api/2'
os.environ['PIX_USERNAME'] = 'sambvfx'
os.environ['PIX_PASSWORD'] = 'mypassword'
os.environ['PIX_APP_KEY'] = '123abc'


class MockResponse:
    def __init__(self, **kwargs):
        self.status_code = 200
        self.text = '{}'
        self.cookies = ['moster']
        for k, v in kwargs.items():
            setattr(self, k, v)


def _get(url, params=None, **kwargs):
    if url.endswith('/session/time_remaining'):
        return MockResponse(status_code=200, text='1800')
    return MockResponse(status_code=404)


pix.api.requests.get = _get


def _put(url, data=None, **kwargs):
    if url.endswith('/session/'):
        return MockResponse(status_code=201)
    elif url.endswith('/session/active_project'):
        return MockResponse(status_code=200)
    return MockResponse(status_code=404)


pix.api.requests.put = _put
