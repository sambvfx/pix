"""
Python PIX API provides a object-oriented and pythonic workflow for
interacting with PIX's REST API.
"""
import os
import re
from setuptools import setup


_dirname = os.path.abspath(os.path.dirname(__file__))


def read(*paths):
    with open(os.path.join(_dirname, *paths)) as f:
        return f.read()


def version():
    """
    Sources version from the __init__.py so we don't have to maintain the
    value in two places.
    """
    regex = re.compile(r'__version__ = \'([0-9.]+)\'')
    for line in read('pix', '__init__.py').split('\n'):
        match = regex.match(line)
        if match:
            return match.groups()[0]


setup(
    name='pix',
    version=version(),
    description=__doc__,
    long_description=read('README.rst'),
    author='Sam Bourne',
    packages=['pix'],
    extras_require={'tests': ['pytest', 'mock']}
)
