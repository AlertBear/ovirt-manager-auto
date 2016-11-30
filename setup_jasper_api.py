#!/bin/env python

import os
from utilities.setup_utils import setup
from utilities.setup_utils import common

RELEASE = os.environ.get('RELEASE', '1')
VERSION = os.environ.get('VERSION', "1.0.0")
CHANGELOG = os.environ.get('CHANGELOG', None)

RPM_NAME = 'art-tests-jasper-api'
PACKAGE_NAME = 'jasper_api'
DESCRIPTION = "TODO: put some description here"
DEPS = [
    # REQUIRES
    'art = %s' % VERSION,
    'python >= 2.6',
    'python-lxml',
    'python-pip',
]

SUB_MODULES = [
    'jasper_api',
    'jasper_api.tests_lib',
]


TEST_DATA_PATH = '/opt'
INSTALLATION_PATH = '/opt/art'

PACKAGE_DATA = {}

DATA_FILES = []
DATA_FILES = common.expand_paths(TEST_DATA_PATH, *DATA_FILES)


SCRIPT = "\n".join(
    [
        "find /opt/art/jasper_api -type f -regex '.*[.]py$' -exec sed -i "
        "'s/art[.]jasper_api/jasper_api/g' '{}' \; &>/dev/null",
        "chmod -R ugo+rw /opt/art/jasper_api &> /dev/null",
    ]
)


CONFS = {
    'install': {'install_lib': INSTALLATION_PATH},
    'bdist_rpm': {'build_requires': 'art-utilities'},
}


if __name__ == '__main__':
    setup(
        name=RPM_NAME,
        version=VERSION,
        release=RELEASE,
        author='Red Hat',
        author_email='edolinin@redhat.com',
        maintainer='Red Hat',
        maintainer_email='edolinin@redhat.com',
        description='JASPER_API TESTS',
        long_description=DESCRIPTION,
        platforms='Linux',
        package_dir={PACKAGE_NAME: 'art/jasper_api'},
        packages=SUB_MODULES,
        package_data=PACKAGE_DATA,
        data_files=DATA_FILES,
        post_install_script=SCRIPT,
        requires=DEPS,
        config=CONFS,
        changelog=CHANGELOG,
    )
