"""
Main PIX API module.
"""
import os
import requests
import json

from base64 import b64decode

import pix.factory
import pix.exc


class SessionHeader(object):
    """
    Context manager for temporarily changing the session headers.
    """
    def __init__(self, session, headers):
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
    A ``Session`` manages all API calls to the PIX REST endpoints. It manages
    the current PIX session including the user logging in and the current
    active project. PIX REST calls return results differently depending on
    the active user and project.

    Examples
    --------
    >>> session = Session()
    ... for project in session.get_projects():
    ...     print project.label
    ...     for feed in project.get_inbox():
    ...         if not feed.viewed:
    ...             print feed
    """

    def __init__(self, host=None, app_key=None, username=None, password=None):
        """
        Parameters
        ----------
        host : str | None
            The host PIX API url. If None, then the environment variable
            PIX_API_URL will be used.
        app_key : str | None
            The host PIX API KEY. If None, then the environment variable
            PIX_APP_KEY will be used.
        username : str | None
            The PIX username used for logging in. If None, then the environment
            variable PIX_USERNAME will be used.
        password : str | None
            The PIX password associated with `username` used for logging in.
            If None, then the environment variable PIX_PASSWORD will be used.
            NOTE: An encoded `b64encode('password')` version may be used to
                  slightly obfuscate passwords stored as plain text.
        """
        host = host or os.environ.get('PIX_API_URL')

        password = password or os.environ.get('PIX_PASSWORD')

        # FIXME: Come up with something better?
        # encoded password provided?
        try:
            password = b64decode(password)
        except TypeError:
            pass

        app_key = app_key or os.environ.get('PIX_APP_KEY')
        username = username or os.environ.get('PIX_USERNAME')

        self._projects = None
        self._project_names = None
        self.active_project = None

        self._session = None
        self.headers = {
            'X-PIX-App-Key': None,
            'Content-type': 'application/json;charset=utf-8',
            'Accept': 'application/json;charset=utf-8'
        }
        self.baseURL = 'https://{0}/developer/api/2'.format(host)
        self.cookies = None

        self.factory = pix.factory.Factory(self)
        self.login(app_key=app_key, username=username, password=password)

    def __enter__(self):
        """
        Use session as a context manager to log out when it exits.

        Examples
        --------
        >>> with Session() as session:
        ...     project = session.load_project('FooBar')
        ...     print project.label
        """
        return self

    def __exit__(self, *args):
        self.logout()

    def login(self, app_key, username, password):
        """
        Log into PIX

        Parameters
        ----------
        app_key : str | None
            The host PIX API KEY. If None, then the environment variable
            PIX_APP_KEY will be used.
        username : str | None
            The PIX username used for logging in. If None, then the environment
            variable PIX_USERNAME will be used.
        password : str | None
            The PIX password associated with `username` used for logging in.
            If None, then the environment variable PIX_PASSWORD will be used.
            NOTE: An encoded `b64encode('password')` version may be used to
                  slightly obfuscate passwords stored as plain text.
        """
        payload = json.dumps({'username': username, 'password': password})
        result = self.session(app_key, payload)
        assert result.status_code == 201, 'Error logging into PIX.'
        self._session = result

    def logout(self):
        """
        Log out of PIX
        """
        result = self.delete_session()
        self._session = result

    def session(self, app_key, payload):
        """
        Get a PIX session
        """
        self.headers['X-PIX-App-Key'] = app_key
        result = requests.put(url=self.baseURL + '/session/',
                              headers=self.headers, data=payload)
        self.cookies = result.cookies
        return result

    def time_remaining(self):
        """
        Get the time remaining for current session.
        """
        url = '/session/time_remaining'
        result = self.get(url)
        return result

    def delete_session(self):
        """
        End a PIX session.
        """
        result = requests.delete(url=self.baseURL + '/session/',
                                 cookies=self.cookies, headers=self.headers)
        return result

    def put(self, url, payload=None):
        """
        PUT REST call
        """
        try:
            self.cookies
        except AttributeError:
            self.cookies = None
        if self.baseURL not in url:
            url = self.baseURL + url
        return requests.put(url=url, cookies=self.cookies,
                            headers=self.headers, data=payload)

    def post(self, url, payload=None):
        """
        POST REST call
        """
        if self.baseURL not in url:
            url = self.baseURL + url
        return requests.post(url=url, cookies=self.cookies,
                             headers=self.headers, data=payload)

    def delete(self, url, payload=None):
        """
        DELETE REST call
        """
        if self.baseURL not in url:
            url = self.baseURL + url
        return requests.delete(url=url, cookies=self.cookies,
                               headers=self.headers, data=payload)

    def get(self, url):
        """
        GET REST call
        """
        if self.baseURL not in url:
            url = self.baseURL + url
        return self.process_result(
            requests.get(url=url, cookies=self.cookies, headers=self.headers))

    def process_result(self, raw_result):
        """
        Process request results. This utilizes the `pix.api.factory.Factory`
        to premote certain elements within the raw results to dict-like
        objects. These objects may be built with base classes registered with
        the factory to offer additional helper methods. See
        `pix.api.factory.Factory` for more information.
        """
        if self.headers['Accept'] != 'application/json;charset=utf-8':
            return raw_result
        return self.factory.objectfy(json.loads(raw_result.text))

    def header(self, headers):
        """
        Context manager for temporarily setting the session headers.

        Examples
        --------
        >>> with self.header({'Accept': 'text/xml'}):
        ...     response = self.get('/media/1234/markup')

        Parameters
        ----------
        headers : dict

        Returns
        -------
        ``SessionHeader``
        """
        return SessionHeader(self, headers)

    def get_projects(self):
        """
        Load all projects user has access to.

        Returns
        -------
        list[``pix.model.PIXProject``]
        """
        if self._session is None:
            raise pix.exc.PIXError(
                'You must login before you can fetch projects.')

        if self._projects is None:
            url = '/projects?limit=3000'
            response = self.get(url)
            if isinstance(response, dict):
                if response.get('type') == 'bad_request':
                    raise pix.exc.PIXError(
                        'Error fetching projects: {0}'.format(
                            response.get('user_message')))
            self._projects = response
            self._project_names = {x.label: x for x in self._projects}

        return self._projects

    @property
    def project_names(self):
        if self._project_names is None:
            self.get_projects()
        return self._project_names

    def load_project(self, project):
        """
        Load a project as the active project.

        Parameters
        ----------
        project : str | ``pix.model.PIXProject``

        Returns
        -------
        ``pix.model.PIXProject``
        """
        if isinstance(project, basestring):
            project = self.project_names[project]
        request_dict = {'id': project.id}
        url = '/session/active_project'
        payload = json.dumps(request_dict)
        result = self.put(url, payload)
        if result.status_code == 200:
            self.active_project = project
            return project
        raise pix.exc.PIXError(result.reason)
