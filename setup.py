#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
    from setuptools import find_packages
except ImportError:
    from distutils.core import setup
    find_packages = None


with open('README.rst') as readme_file:
    readme = readme_file.read()

requirements = [
    'six',
    'arrow',
    'iec60063',
    'tendril-schema',
    'tendril-validation>=0.1.5',
    'tendril-conventions-electronics>=0.1.1',
    'tendril-conventions-status',
    'tendril-utils-types>=0.1.8',
    'tendril-utils-yaml>=0.1.1',
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='tendril-eda',
    version='0.1.1',
    description="Tendril EDA Primitives",
    long_description=readme,
    author="Chintalagiri Shashank",
    author_email='shashank@chintal.in',
    url='https://github.com/chintal/tendril-eda',
    packages=find_packages(),
    install_requires=requirements,
    license="AGPLv3",
    zip_safe=False,
    keywords='tendril',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Programming Language :: Python',
    ],
    include_package_data=True,
    package_data={
        'tendril': [
            'schema/templates/*.yaml',
        ]
    }
    # test_suite='tests',
    # tests_require=test_requirements
)
