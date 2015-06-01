#!/usr/bin/env python3
import sys
if sys.version_info < (3, 4):
    raise Exception("Python 3.4+ required.")
from setuptools import setup

setup(
    name='letschat',
    version='0.0.1',
    description='API for Lets-Chat open source chat server (https://github.com/sdelements/lets-chat)',
    author='Cathal Garvey',
    author_email='cathalgarvey@cathalgarvey.me',
    keywords=('chat', 'slack', 'lets-chat', 'lets chat', "let's chat", 'bot', 'api'),
    license = "AGPL",
    entry_points = {
        "console_scripts": [
        ]
    },
    exclude_package_data={'': ['.gitignore']},
    packages=['letschat'],
    requires=['requests'],
    classifiers= [
      'Development Status :: 4 - Beta',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
      'Programming Language :: Python',
      'Programming Language :: Python :: 3.4',
      'Topic :: Software Development :: Libraries :: Python Modules',
      'Topic :: Communications :: Chat'
    ],
    long_description = open('ReadMe.md').read(),
    url='http://github.com/cathalgarvey/python-letschat'
)
