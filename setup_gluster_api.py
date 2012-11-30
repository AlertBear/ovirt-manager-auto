#!/bin/env python

import os
from utilities.setup_utils import setup
from utilities.setup_utils import common

RPM_NAME = 'art-tests-gluster-api'
PACKAGE_NAME = 'gluster_api'
DESCRIPTION = "TODO: put some description here"
DEPS = [
        # REQUIRES
        'art',
        'python >= 2.6',
        'python-lxml',
        'PyXML',
        'python-pip',
        'art-utilities',
        'art-tests-rhevm-api',
        ]

PIP_DEPS = [
        'generateDS', # not used yet
        ]

RELEASE = os.environ.get('RELEASE', '1')
VERSION = os.environ.get('VERSION', "1.0.0")
CHANGELOG = os.environ.get('CHANGELOG', None)

SUB_MODULES = [
                'gluster_api',
                'gluster_api.tests_lib',
                'gluster_api.data_struct'
                ]



TEST_DATA_PATH = '/opt'
INSTALLATION_PATH='/opt/art'

PACKAGE_DATA = {
        PACKAGE_NAME: ['art/gluster_api/data_struct/api.xsd'],
        }

DATA_FILES = [
        'art/tests/gluster/*/*.xml',
        'art/tests/gluster/*/*.conf',
        'art/gluster_api/data_struct/api.xsd',
        ]
DATA_FILES = common.expand_paths(TEST_DATA_PATH, *DATA_FILES)


SCRIPT = """\
find /opt/art/gluster_api -type f -regex '.*[.]py$' -exec sed -i 's/art[.]\(gluster_api\|rhevm_api\)/\\1/g' '{}' \; &> /dev/null
chmod -R ugo+rw /opt/art/gluster_api &> /dev/null

"""


CONFS = {'install': {'install_lib': INSTALLATION_PATH},
         'bdist_rpm': {'build_requires': 'art-utilities'},
        }


MANIFEST = [
           'recursive-include art/gluster_api *.xsd',
           'recursive-include art/tests/gluster *.xml *.conf',
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
            description='GLUSTER TESTS',
            long_description=DESCRIPTION,
            platforms='Linux',
            package_dir={PACKAGE_NAME: 'art/gluster_api'},
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

