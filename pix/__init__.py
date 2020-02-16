"""
PIX python API.
"""
from __future__ import absolute_import

from .api import Session
from .factory import Factory as _Factory
from .model import PIXObject, PIXProject

register = _Factory.register


__version__ = '0.5.2'
__author__ = 'Sam Bourne'
__contact__ = 'sambvfx@gmail.com'
__license__ = 'MIT'
__copyright__ = 'Copyright (c) 2018 Sam Bourne'


__all__ = [
    'Session',
    'register',
    'PIXObject',
    'PIXProject',
]
