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
    long_description=read('README.md'),
    author='Sam Bourne',
    packages=['pix'],
    install_requires=[
        'six',
        'requests',
        'typing',
    ],
    extras_require={'tests': [
        'pytest',
        'mock',
    ]},
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
)
