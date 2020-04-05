#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
from setuptools import find_packages, setup
from bl3save import __version__

def readme():
    with open('README.md') as f:
        return f.read()

app_name = 'bl3-cli-saveedit'

setup(
        name=app_name,
        version=__version__,
        packages=find_packages(),
        include_package_data=True,
        license='zlib/libpng',
        description='Borderlands 3 Savegame Editor',
        long_description=readme(),
        long_description_content_type='text/markdown',
        url='https://github.com/apocalyptech/bl3-cli-saveedit',
        author='CJ Kucera',
        author_email='cj@apocalyptech.com',
        data_files=[
            # I always like these to be installed along with the apps
            (f'share/{app_name}', ['COPYING.txt', 'README.md']),
            # Seems helpful to bundle the Protobuf definitions (via Gibbed) in here
            (f'share/{app_name}/protobufs', [os.path.join('protobufs', f) for f in sorted(os.listdir('protobufs'))]),
            # Seems less helpful to package my mod testing gear, but whatever.
            (f'share/{app_name}/item_exports', ['mod_testing_gear.txt']),
            ],
        install_requires=[
            'protobuf ~= 3.0',
            ],
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: End Users/Desktop',
            'License :: OSI Approved :: zlib/libpng License',
            'Natural Language :: English',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3',
            'Topic :: Games/Entertainment :: First Person Shooters',
            'Topic :: Utilities',
            ],
        entry_points={
            'console_scripts': [
                'bl3-save-edit = bl3save.cli_edit:main',
                'bl3-save-info = bl3save.cli_info:main',
                # Actually, gonna omit this one.  Without transferring a lot of other data,
                # this can make things a bit weird, and at that point you may as well just
                # copy the savegame and alter other bits about it.
                #'bl3-save-copy-pt = bl3save.cli_copy_pt:main',
                'bl3-process-archive-saves = bl3save.cli_archive:main',
                ],
            },
        )
