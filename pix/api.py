"""
Main PIX API module.
"""
from __future__ import absolute_import

import os
import requests
import json
import six
import time

from typing import *

from .factory import Factory
from .model import PIXProject
from .exc import PIXLoginError, PIXError
from .utils import import_modules


if TYPE_CHECKING:
    import requests.cookies


class SessionHeader(object):
    """
    Context manager for temporarily changing the session headers.
    """
    def __init__(self, session, headers):
        # type: (Session, Dict[str, str]) -> None
        """
        Parameters
        ----------
        session : Session
        headers : Dict[str, str]
        """
        super(SessionHeader, self).__init__()
        self._session = session
        self.original = None
        self.headers = headers

    def __enter__(self):
        # copy here!
        self.original = dict(self._session.headers)
        self._session.headers.update(self.headers)

    def __exit__(self, exception_type, exception_value, traceback):
        self._session.headers = self.original


class Expiry(object):
    """
    Object that existence check fails for after a set duration in seconds.

    Examples
    --------
    >>> import time
    >>> e = Expiry(5)
    >>> i = 0
    >>> while True:
    ...     if not e:
    ...         break
    ...     print(i)
    ...     i += 1
    ...     time.sleep(1)
    """
    def __init__(self, seconds):
        # type: (Union[int, float]) -> None
        """
        Parameters
        ----------
        seconds : Union[int, float]
        """
        self.expires = time.time() + seconds

    def __bool__(self):
        # type: () -> bool
        """
        Returns
        -------
        bool
        """
        return time.time() < self.expires

    __nonzero__ = __bool__


class Session(object):
    """
    A Session manages all API calls to the PIX REST endpoints. It manages
    the current PIX session including the user logging in and the current
    active project. PIX REST calls return results differently depending on
    the active user and project. It also handles refreshing the active session
    if it expires

    Examples
    --------
    >>> session = Session()
    ... for project in session.get_projects():
    ...     for feed in project.iter_unread():
    ...         for attachment in feed.iter_attachments():
    ...             for note in attachment.get_notes():
    ...                 image_bytes = note.get_media('composite')
    """

    def __init__(self, api_url=None, app_key=None, username=None, password=None,
                 plugin_paths=None):
        # type: (Optional[str], Optional[str], Optional[str], Optional[str], Optional[List[str]]) -> None
        """
        Parameters
        ----------
        api_url : Optional[str]
            The host PIX API url. If None, then the environment variable
            PIX_API_URL will be used.
        app_key : Optional[str]
            The host PIX API KEY. If None, then the environment variable
            PIX_APP_KEY will be used.
        username : Optional[str]
            The PIX username used for logging in. If None, then the environment
            variable PIX_USERNAME will be used.
        password : Optional[str]
            The PIX password associated with `username` used for logging in.
            If None, then the environment variable PIX_PASSWORD will be used.
        plugin_paths : Optional[List[str]]
            Paths to custom modules or packages that should be loaded prior to 
            constructing any objects via the factory. This allows for 
            registration of any custom bases within the factory. If None, 
            the environment variable PIX_PLUGIN_PATH will be used.
        """
        self.api_url = api_url or os.environ.get('PIX_API_URL')
        self.app_key = app_key or os.environ.get('PIX_APP_KEY')
        self.username = username or os.environ.get('PIX_USERNAME')
        self.password = password or os.environ.get('PIX_PASSWORD')

        _creds = [x for x in ('api_url', 'app_key', 'username', 'password')
                  if getattr(self, x) is None]
        if _creds:
            raise PIXLoginError('Missing login credentials: {}'.format(
                ', '.join(_creds)))

        plugin_paths = plugin_paths or os.environ.get('PIX_PLUGIN_PATH')
        if plugin_paths:
            import_modules(plugin_paths)

        self.factory = Factory(self)

        self.headers = {
            'X-PIX-App-Key': self.app_key,
            'Content-type': 'application/json;charset=utf-8',
            'Accept': 'application/json;charset=utf-8'
        }

        self.cookies = None  # type: requests.cookies.RequestsCookieJar

        # A time-out object representing the current session. Expires after a
        # set duration and is then refreshed.
        self._session = None  # type: Expiry

        # current active project
        self.active_project = None  # type: PIXProject

    def __enter__(self):
        # type: () -> Session
        """
        Use session as a context manager to log out when it exits.

        Examples
        --------
        >>> with Session() as session:
        ...     project = session.load_project('FooBar')
        ...     label = project.label

        Returns
        -------
        Session
        """
        return self

    def __exit__(self, *args):
        self.logout()

    def login(self):
        """
        Log into PIX
        """
        result = requests.put(
            url=self.api_url + '/session/',
            headers=self.headers,
            data=json.dumps(
                {'username': self.username, 'password': self.password}))

        if result.status_code != 201:
            raise PIXLoginError(result.reason)

        self.cookies = result.cookies
        self._session = Expiry(self.time_remaining())

    def logout(self):
        """
        Log out of PIX
        """
        result = self.delete_session()
        self._session = result

    def time_remaining(self):
        # type: () -> int
        """
        Get the time remaining for current session.

        Returns
        -------
        int
        """
        # Not using self.get here is intentional to avoid recursive self.login
        # calls.
        response = requests.get(
            url=self.api_url + '/session/time_remaining',
            cookies=self.cookies,
            headers=self.headers)
        return json.loads(response.text)

    def delete_session(self):
        # type: () -> requests.Response
        """
        End a PIX session.

        Returns
        -------
        requests.Response
        """
        return requests.delete(
            url=self.api_url + '/session/', cookies=self.cookies,
            headers=self.headers)

    def put(self, url, payload=None):
        # type: (str, Optional[Dict]) -> requests.Response
        """
        PUT REST call

        Parameters
        ----------
        url : str
        payload : Optional[Dict]

        Returns
        -------
        requests.Response
        """
        if not self._session:
            self.login()

        if self.api_url not in url:
            url = self.api_url + url

        if payload is not None:
            payload = json.dumps(payload)

        return requests.put(
            url=url, cookies=self.cookies, headers=self.headers, data=payload)

    def post(self, url, payload=None):
        # type: (str, Optional[Dict]) -> requests.Response
        """
        POST REST call

        Parameters
        ----------
        url : str
        payload : Optional[Dict]

        Returns
        -------
        requests.Response
        """
        if not self._session:
            self.login()

        if self.api_url not in url:
            url = self.api_url + url

        if payload is not None:
            payload = json.dumps(payload)

        return requests.post(
            url=url, cookies=self.cookies, headers=self.headers, data=payload)

    def delete(self, url, payload=None):
        # type: (str, Optional[Dict]) -> requests.Response
        """
        DELETE REST call

        Parameters
        ----------
        url : str
        payload : Optional[Dict]

        Returns
        -------
        requests.Response
        """
        if not self._session:
            self.login()

        if self.api_url not in url:
            url = self.api_url + url

        if payload is not None:
            payload = json.dumps(payload)

        return requests.delete(
            url=url, cookies=self.cookies, headers=self.headers, data=payload)

    def get(self, url):
        # type: (str) -> Union[requests.Response, Any]
        """
        GET REST call

        Parameters
        ----------
        url : str

        Returns
        -------
        Union[requests.Response, Any]
        """
        if not self._session:
            self.login()

        if self.api_url not in url:
            url = self.api_url + url

        return self.process_result(
            requests.get(url=url, cookies=self.cookies, headers=self.headers))

    def process_result(self, raw_result):
        # type: (requests.Response) -> Union[requests.Response, Any]
        """
        Process request results. This utilizes the `Factory` to premote
        certain elements within the raw results to dict-like objects. These
        objects may be built with base classes registered with the factory to
        offer additional helper methods.

        Parameters
        ----------
        raw_result : requests.Response
        
        Returns
        -------
        Union[requests.Response, Any]
        """
        if self.headers['Accept'] != 'application/json;charset=utf-8':
            return raw_result
        return self.factory.objectfy(json.loads(raw_result.text))

    def header(self, headers):
        # type: (Dict[str, str]) -> SessionHeader
        """
        Context manager for temporarily setting the session headers.

        Examples
        --------
        >>> session = Session()
        >>> with session.header({'Accept': 'text/xml'}):
        ...     response = session.get('/media/1234/markup')

        Parameters
        ----------
        headers : Dict[str, str]

        Returns
        -------
        SessionHeader
        """
        return SessionHeader(self, headers)

    def get_projects(self, limit=None):
        # type: (Optional[int]) -> List[PIXProject]
        """
        Load all projects user has access to.

        Parameters
        ----------
        limit : Optional[int]

        Returns
        -------
        List[PIXProject]
        """
        url = '/projects'

        if limit is not None:
            url += '?limit={}'.format(limit)

        response = self.get(url)

        if isinstance(response, dict):
            if response.get('type') == 'bad_request':
                raise PIXError(
                    'Error fetching projects: {}'.format(
                        response.get('user_message')))

        response = cast(List[PIXProject], response)

        return response

    def load_project(self, project):
        # type: (Union[str, PIXProject]) -> PIXProject
        """
        Load a project as the active project.

        Parameters
        ----------
        project : Union[str, PIXProject]

        Returns
        -------
        PIXProject
        """
        if isinstance(project, six.string_types):
            for p in self.get_projects():
                if p['label'] == project or p['id'] == project:
                    project = p
                    break
            else:
                raise PIXError(
                    'No project found {!r}'.format(project))

        result = self.put(
            '/session/active_project', payload={'id': project['id']})

        if result.status_code == 200:
            self.active_project = project
            return project

        raise PIXError(result.reason)
