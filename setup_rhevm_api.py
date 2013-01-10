#!/bin/env python

import os
from utilities.setup_utils import setup
from utilities.setup_utils import common

RPM_NAME = 'art-tests-rhevm-api'
PACKAGE_NAME = 'rhevm_api'
DESCRIPTION = "TODO: put some description here"
DEPS = [
        # REQUIRES
        'art',
        'python >= 2.6',
        'python-lxml',
        'python-pip',
        'art-utilities',
        ]

PIP_DEPS = [
        'generateDS', # not used yet
        ]

RELEASE = os.environ.get('RELEASE', '1')
VERSION = os.environ.get('VERSION', "1.0.0")
CHANGELOG = os.environ.get('CHANGELOG', None)

SUB_MODULES = [
                'rhevm_api',
                'rhevm_api.utils',
                'rhevm_api.tests_lib',
                'rhevm_api.tests_lib.low_level',
                'rhevm_api.tests_lib.high_level',
                'rhevm_api.data_struct'
                ]



TEST_DATA_PATH = '/opt'
INSTALLATION_PATH='/opt/art'

PACKAGE_DATA = {
        PACKAGE_NAME: ['art/rhevm_api/data_struct/api.xsd'],
        }

DATA_FILES = [
        'art/tests/rhevm/xml_tests/*.xml',
        'art/tests/rhevm/xml_tests/network/*.xml',
        'art/tests/rhevm/xml_tests/network/requiredNetwork/*.xml',
        'art/tests/rhevm/xml_tests/payloads_cases/*.xml',
        'art/tests/rhevm/xml_tests/sla/*.xml',
        'art/tests/rhevm/xml_tests/storage/*.xml',
        'art/tests/rhevm/unittests/user_roles_tests/*.py',
        'art/tests/rhevm/unittests/rhevm_utils/*.py',
        'art/tests/rhevm/unittests/rhevm_utils/lc_reports_content/*.xml',
        'art/rhevm_api/data_struct/api.xsd',
        ]
DATA_FILES = common.expand_paths(TEST_DATA_PATH, *DATA_FILES)


SCRIPT = """\
find /opt/art/rhevm_api -type f -regex '.*[.]py$' -exec sed -i 's/art[.]rhevm_api/rhevm_api/g' '{}' \; &> /dev/null
find /opt/art/tests/rhevm -type f -regex '.*[.]py$' -exec sed -i 's/art[.]rhevm_api/rhevm_api/g' '{}' \; &> /dev/null
chmod -R ugo+rw /opt/art/rhevm_api &> /dev/null

"""

CONFS = {'install': {'install_lib': INSTALLATION_PATH},
         'bdist_rpm': {'build_requires': 'art-utilities'},
         }


MANIFEST = [
           'recursive-include art/rhevm_api *.xsd',
           'recursive-include art/tests/rhevm *.conf *.xml',
           'recursive-include art/tests/rhevm/unittests *.py',
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
            package_dir={PACKAGE_NAME: 'art/rhevm_api'},
            packages=SUB_MODULES,
            package_data=PACKAGE_DATA,
            data_files=DATA_FILES,
            manifest_list=MANIFEST,
#            pipdeps=PIP_DEPS,
            post_install_script=SCRIPT,
            requires=DEPS,
            config=CONFS,
            changelog=CHANGELOG,
    )

