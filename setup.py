# -*- coding: utf-8 -*-
from __future__ import with_statement
import os
from setuptools import setup

def get_version():
    with open(r'baresql\baresql.py') as f:
        for line in f:
            if line.strip().startswith('self.__version__'):
                return eval(line.split('=')[-1])

def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

setup(
    name='baresql',
    version=get_version(),
    description="playing SQL directly on Python datas",

    long_description=(read('README.rst') + '\n\n' +
                      read('HISTORY.rst')),
    keywords=['sqlite', 'sql'],
    author='stonebig',
    author_email='write_pull_requests_to_stonebig@github.com',
    url='https://github.com/stonebig/baresql',
    license='MIT license',
    packages = ['baresql'],
    install_requires=['pandas'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Education',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Information Analysis',
    ]
)
