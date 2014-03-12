#!/bin/env python

import os
from utilities.setup_utils import setup
from utilities.setup_utils import common

RELEASE = os.environ.get('RELEASE', '1')
VERSION = os.environ.get('VERSION', "1.0.0")
CHANGELOG = os.environ.get('CHANGELOG', None)

RPM_NAME = 'art-tests-rhevm-api'
PACKAGE_NAME = 'rhevm_api'
DESCRIPTION = "TODO: put some description here"
DEPS = [
    # REQUIRES
    'art = %s' % VERSION,
    'RAUT = %s' % VERSION,
    'python >= 2.6',
    'python-lxml',
    'python-pip',
]


SUB_MODULES = [
    'rhevm_api',
    'rhevm_api.utils',
    'rhevm_api.tests_lib',
    'rhevm_api.tests_lib.low_level',
    'rhevm_api.tests_lib.high_level',
    'rhevm_api.data_struct',
    'unittest_lib',
]


TEST_DATA_PATH = '/opt'
INSTALLATION_PATH = '/opt/art'

PACKAGE_DATA = {
    PACKAGE_NAME: ['art/rhevm_api/data_struct/api.xsd'],
}

DATA_FILES = [
    'art/rhevm_api/data_struct/api.xsd',
    'art/tests/rhevmtests/user_roles_tests/*.py',
    'art/tests/rhevmtests/user_roles_tests/mla/*.py',
    'art/tests/rhevmtests/quota_tests/*.py',
    'art/tests/rhevmtests/sla/*.py',
    'art/tests/rhevmtests/reg_hosts/*.py',
    'art/tests/rhevmtests/watchdog/*.py',
    'art/tests/rhevmtests/rhevm_utils/*.py',
    'art/tests/rhevmtests/rhevm_utils/lc_reports_content/*.xml',
    'art/tests/rhevmtests/storage/storage_*/*.py',
    'art/tests/rhevmtests/networking/*/*.py',
    'art/tests/rhevmtests/templates/*.py',
    'art/tests/rhevmtests/scheduler_tests/*/*.py',
    'art/tests/rhevmtests/upgradeSanity/*.py',
    'art/tests/rhevmtests/hooks/*.py',
    'art/tests/rhevmtests/virt/*/*.py',
    'art/tests/rhevmtests/infra/*/*.py',
    'art/tests/rhevmtests/infra/*/*/*.py',
    'art/tests/rhevmtests/mom/*.py',
]

DATA_FILES = common.expand_paths(TEST_DATA_PATH, *DATA_FILES)


SCRIPT = (
    "find /opt/art/rhevm_api -type f -regex '.*[.]py$' -exec "
    "sed -i 's/art[.]rhevm_api/rhevm_api/g' '{}' \; &> /dev/null\n"
    "find /opt/art/unittest_lib -type f -regex '.*[.]py$' -exec "
    "sed -i 's/art[.]\(rhevm_api\|unittest_lib\)/\\1/g' '{}' \; &> /dev/null\n"
    "find /opt/art/tests/rhevm -type f -regex '.*[.]py$' -exec "
    "sed -i 's/art[.]\(rhevm_api\|unittest_lib\)/\\1/g' '{}' \; &> /dev/null\n"
    "chmod -R ugo+rw /opt/art/rhevm_api &> /dev/null\n"
)

CONFS = {
    'install': {
        'install_lib': INSTALLATION_PATH
    },
    'bdist_rpm': {
        'build_requires': 'art-utilities'
    },
}

MANIFEST = [
    'recursive-include art/rhevm_api *.xsd',
    'recursive-include art/tests/rhevmtests *.conf *.xml *.py',
    'recursive-include art/unittest_lib *.py',
]

if __name__ == '__main__':
    setup(
        name=RPM_NAME,
        version=VERSION,
        release=RELEASE,
        author='Red Hat',
        author_email='edolinin@redhat.com',
        maintainer='Red Hat',
        maintainer_email='edolinin@redhat.com',
        description='RHEVM TESTS',
        long_description=DESCRIPTION,
        platforms='Linux',
        package_dir={
            PACKAGE_NAME: 'art/rhevm_api',
            'unittest_lib': 'art/unittest_lib'
        },
        packages=SUB_MODULES,
        package_data=PACKAGE_DATA,
        data_files=DATA_FILES,
        manifest_list=MANIFEST,
        post_install_script=SCRIPT,
        requires=DEPS,
        config=CONFS,
        changelog=CHANGELOG,
    )
