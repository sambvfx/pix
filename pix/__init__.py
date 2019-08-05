"""
PIX python API.
"""
from __future__ import absolute_import

from .api import Session
from .factory import register
from .model import PIXObject, PIXProject


__version__ = '0.5.1'
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
