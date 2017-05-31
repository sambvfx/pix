"""
Python PIX API provides a object-oriented and pythonic workflow for
interacting with PIX's REST API.
"""
from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='pix',
    version='0.3.0',
    description=__doc__,
    long_description=readme(),
    author='Sam Bourne',
    packages=['pix'],
    extras_require={'tests': ['pytest', 'mock']}
)
