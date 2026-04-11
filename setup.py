# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='ckanext-graphic-walker',
    version='0.1.0',
    description='Interactive CSV data visualization for CKAN using Graphic Walker',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pabrojast/ckanext-graphic-walker',
    author='pabrojast',
    license='AGPL-3.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
    ],
    keywords='CKAN visualization CSV graphic-walker data-analysis',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*', 'graphic-walker-app']),
    namespace_packages=['ckanext'],
    python_requires='>=3.8',
    include_package_data=True,
    package_data={},
    entry_points='''
        [ckan.plugins]
        graphic_walker=ckanext.graphic_walker.plugin:GraphicWalkerPlugin
    ''',
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)
