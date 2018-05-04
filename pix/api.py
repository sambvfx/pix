"""
Main PIX API module.
"""
import os
import requests
import json
import six

import pix.factory
import pix.exc
import pix.utils

import logging

from typing import *


if TYPE_CHECKING:
    import pix.model


logger = logging.getLogger(__name__)


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


class Session(object):
    """
    A Session manages all API calls to the PIX REST endpoints. It manages
    the current PIX session including the user logging in and the current
    active project. PIX REST calls return results differently depending on
    the active user and project.

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
        api_url = api_url or os.environ.get('PIX_API_URL')
        password = password or os.environ.get('PIX_PASSWORD')
        app_key = app_key or os.environ.get('PIX_APP_KEY')
        username = username or os.environ.get('PIX_USERNAME')

        # e.g. 'https://project.pixsystem.com/developer/api/2'
        self.api_url = api_url  # type: str

        plugin_paths = plugin_paths or os.environ.get('PIX_PLUGIN_PATH')
        if plugin_paths:
            pix.utils.import_modules(plugin_paths)

        self.factory = pix.factory.Factory(self)

        self._projects = None  # type: List[pix.model.PIXProject]
        self.active_project = None  # type: pix.model.PIXProject

        self._session = None  # type: requests.Response

        self.headers = {
            'X-PIX-App-Key': None,
            'Content-type': 'application/json;charset=utf-8',
            'Accept': 'application/json;charset=utf-8'
        }

        self.cookies = None

        self.login(app_key=app_key, username=username, password=password)

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

    def login(self, app_key, username, password):
        # type: (str, str, str) -> None
        """
        Log into PIX

        Parameters
        ----------
        app_key : str
            The host PIX API KEY.
        username : str
            The PIX username used for logging in.
        password : str
            The PIX password associated with `username` used for logging in.
        """
        result = self.session(
            app_key, payload={'username': username, 'password': password})

        assert result.status_code == 201, 'Error logging into PIX.'

        self._session = result

    def logout(self):
        """
        Log out of PIX
        """
        result = self.delete_session()
        self._session = result

    def session(self, app_key, payload=None):
        # type: (str, Optional[Dict]) -> requests.Response
        """
        Get a PIX session

        Parameters
        ----------
        app_key : str
        payload : Optional[Dict]

        Returns
        -------
        requests.Response
        """
        self.headers['X-PIX-App-Key'] = app_key

        logger.info(self.api_url + '/session')

        if payload is not None:
            payload = json.dumps(payload)

        result = requests.put(
            url=self.api_url + '/session/', headers=self.headers, data=payload)

        self.cookies = result.cookies

        return result

    def time_remaining(self):
        # type: () -> requests.Response
        """
        Get the time remaining for current session.

        Returns
        -------
        requests.Response
        """
        return self.get('/session/time_remaining')

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
        if self.api_url not in url:
            url = self.api_url + url

        if payload is not None:
            payload = json.dumps(payload)

        return requests.delete(
            url=url, cookies=self.cookies, headers=self.headers, data=payload)

    def get(self, url):
        # type: (str) -> Union[requests.Response, pix.model.PIXObject, Dict, List]
        """
        GET REST call

        Parameters
        ----------
        url : str

        Returns
        -------
        Union[requests.Response, pix.model.PIXObject, Dict, List]
        """
        if self.api_url not in url:
            url = self.api_url + url
        return self.process_result(
            requests.get(url=url, cookies=self.cookies, headers=self.headers))

    def process_result(self, raw_result):
        # type: (requests.Response) -> Union[requests.Response, pix.model.PIXObject, Dict[str, Any], Any]
        """
        Process request results. This utilizes the `pix.factory.Factory`
        to premote certain elements within the raw results to dict-like
        objects. These objects may be built with base classes registered with
        the factory to offer additional helper methods.

        Parameters
        ----------
        raw_result : requests.Response
        
        Returns
        -------
        Union[requests.Response, pix.model.PIXObject, Dict[str, Any], Any]
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
        # type: (Optional[int]) -> List[pix.model.PIXProject]
        """
        Load all projects user has access to.

        Parameters
        ----------
        limit : Optional[int]

        Returns
        -------
        List[pix.model.PIXProject]
        """
        if self._session is None:
            raise pix.exc.PIXError(
                'You must login before you can fetch projects.')

        if self._projects is None:

            url = '/projects'

            if limit is not None:
                url += '?limit={}'.format(limit)

            response = self.get(url)

            if isinstance(response, dict):
                if response.get('type') == 'bad_request':
                    raise pix.exc.PIXError(
                        'Error fetching projects: {0}'.format(
                            response.get('user_message')))

            response = cast(List[pix.model.PIXProject], response)

            self._projects = response

        return self._projects

    def load_project(self, project):
        # type: (Union[str, pix.model.PIXProject]) -> pix.model.PIXProject
        """
        Load a project as the active project.

        Parameters
        ----------
        project : Union[str, pix.model.PIXProject]

        Returns
        -------
        pix.model.PIXProject
        """
        if isinstance(project, six.string_types):
            for p in self.get_projects():
                if p['label'] == project or p['id'] == project:
                    project = p
                    break
            else:
                raise pix.exc.PIXInvalidProjectError(
                    'No project found {!r}'.format(project))

        result = self.put(
            '/session/active_project', payload={'id': project['id']})

        if result.status_code == 200:
            self.active_project = project
            return project

        raise pix.exc.PIXError(result.reason)
