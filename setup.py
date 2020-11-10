#!/usr/bin/env python3
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
        license='zlib/libpng',
        description='Borderlands 3 Savegame Editor',
        long_description=readme(),
        long_description_content_type='text/markdown',
        url='https://github.com/apocalyptech/bl3-cli-saveedit',
        author='CJ Kucera',
        author_email='cj@apocalyptech.com',
        data_files=[
            # I always like these to be installed along with the apps
            (f'share/{app_name}', ['COPYING.txt', 'README.md', 'README-saves.md', 'README-profile.md']),
            # Seems helpful to bundle the Protobuf definitions (via Gibbed) in here
            (f'share/{app_name}/protobufs', [os.path.join('protobufs', f) for f in sorted(os.listdir('protobufs'))]),
            # Seems less helpful to package my mod testing gear, but whatever.
            (f'share/{app_name}/item_exports', ['mod_testing_gear.txt']),
            ],
        package_data={
            'bl3save': [
                'resources/inventoryserialdb.json.xz',
                'resources/short_name_balance_mapping.json.xz',
                'resources/balance_to_inv_key.json.xz',
                ],
            },
        install_requires=[
            'protobuf ~= 3.0, >= 3.12',
            ],
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        classifiers=[
            'Development Status :: 5 - Production/Stable',
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

                # Savegame-related scripts
                'bl3-save-edit = bl3save.cli_edit:main',
                'bl3-save-info = bl3save.cli_info:main',
                'bl3-save-import-protobuf = bl3save.cli_import_protobuf:main',
                'bl3-save-import-json = bl3save.cli_import_json:main',
                'bl3-process-archive-saves = bl3save.cli_archive:main',
                # Actually, gonna omit this one.  Without transferring a lot of other data,
                # this can make things a bit weird, and at that point you may as well just
                # copy the savegame and alter other bits about it.
                #'bl3-save-copy-pt = bl3save.cli_copy_pt:main',

                # Profile-related scripts
                'bl3-profile-edit = bl3save.cli_prof_edit:main',
                'bl3-profile-info = bl3save.cli_prof_info:main',
                'bl3-profile-import-protobuf = bl3save.cli_prof_import_protobuf:main',
                'bl3-profile-import-json = bl3save.cli_prof_import_json:main',
                ],
            },
        )
