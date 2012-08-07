#!/bin/env python
import os
from configobj import ConfigObj
#from distutils.core import setup
from setuptools import setup


PRE_INSTALL = """\
python << __END__
import pip

PIP_DEPS = {pip_deps}

for dep in PIP_DEPS:
    if pip.main(['install', '-q', '--upgrade', dep]):
        raise Exception("failed to install %s" % dep)
__END__
"""

PRE_INSTALL_FILE = 'preinstall_script'
SETUP_CFG_FILE = 'setup.cfg'

PIP_DEPS = [
        'configobj',
        'odfpy',
        ]

RELEASE = 1

RHEVM_API_ENABLED = True
GLUSTER_API_ENABLED = True
INCLUDE_TESTS = True # for now it will be included anyway because bug in distutils
INCLUDE_CONFS = True # same here


PACKAGE_NAME = 'art'
DESCRIPTION = "Automated framework for testing REST APIs applications, "\
            "uses generateDS tool to auto generate Python data structures"

SUB_MODULES = ['art',
                'art.core_api',
                'art.test_handler',
                'art.test_handler.plmanagement',
                'art.test_handler.plmanagement.interfaces']

RHEVM_SUB_MODULES = [
                'art.rhevm_api',
                'art.rhevm_api.tests_lib',
                'art.rhevm_api.utils',
                'art.rhevm_api.data_struct',
                    ]

GLUSTESR_SUB_MODULES = [
                'art.gluster_api',
                'art.gluster_api.tests_lib',
                'art.gluster_api.data_struct'
                ]

PY_MODULES = ['art.__main__', 'art.__init__', 'art.run',
                #'art.test_handler.plmanagement.plugins.xml_results_formater_plugin',
                'art.test_handler.plmanagement.plugins.results_collector_plugin',
                'art.test_handler.plmanagement.plugins.resources_plugin',
                ]

# DUE BUG IN DISTUTILS
#TEST_FILES_LIST = ['tests/gluster/xml_tests/*.conf', \
#                    'tests/gluster/xml_tests/*.xml', \
#                    'tests/rhevm/xml_tests/*.conf', \
#                    'tests/rhevm/xml_tests/*.xml', \
#                    'tests/rhevm/xml_tests/network/*.conf', \
#                    'tests/rhevm/xml_tests/network/*.xml', \
#                    'tests/xml_templates/*.conf', \
#                    'tests/xml_templates/*.xml']

PACKAGE_DATA = {PACKAGE_NAME: []}

if RHEVM_API_ENABLED:
    SUB_MODULES += RHEVM_SUB_MODULES
    PACKAGE_DATA['art.rhevm_api'] = ['art/rhevm_api/data_struct/api.xsd']

if GLUSTER_API_ENABLED:
    SUB_MODULES += GLUSTESR_SUB_MODULES
    PACKAGE_DATA['art.gluster_api'] = ['art/gluster_api/data_struct/api.xsd']

if INCLUDE_TESTS:
    PACKAGE_DATA[PACKAGE_NAME].append('tests/*/*.xml')

if INCLUDE_CONFS:
    PACKAGE_DATA[PACKAGE_NAME].append('conf/*.conf')


DEPS = [
        # REQUIRES
        'python-lxml',
        'python-argparse',
        'python-lockfile',
        'python-tpg',
        'PyXML',
        'python-dateutil',
        'python-pip',
        'art-utilities',
        ]


def gen_config():
    bdist_rpm = {}
    bdist_rpm['release'] = RELEASE
    bdist_rpm['requires'] = ' '.join(DEPS)
    bdist_rpm['pre_install'] = PRE_INSTALL_FILE

    conf = ConfigObj()
    conf['bdist_rpm'] = bdist_rpm
    with open(SETUP_CFG_FILE, 'w') as fh:
        conf.write(fh)

def gen_pre_install(pip_deps):
    with open(PRE_INSTALL_FILE, 'w') as fh:
        fh.write(PRE_INSTALL.format(pip_deps=pip_deps))


if __name__ == '__main__':

    try:
        gen_config()
        gen_pre_install(PIP_DEPS)

        setup(
                name=PACKAGE_NAME,
                version='1.0',
                author='Red Hat',
                author_email='edolinin@redhat.com',
                maintainer='Red Hat',
                maintainer_email='edolinin@redhat.com',
                description='Automated REST Testing Framework',
                long_description=DESCRIPTION,
                platforms='Linux',
#                license='?',
                package_dir={PACKAGE_NAME: 'art'},
                packages=SUB_MODULES,
                py_modules=PY_MODULES,
#                install_requires=DEPS,
                package_data=PACKAGE_DATA,
                include_package_data=True,
        )
    finally:
        if os.path.exists(SETUP_CFG_FILE):
            os.unlink(SETUP_CFG_FILE)
        if os.path.exists(PRE_INSTALL_FILE):
            os.unlink(PRE_INSTALL_FILE)

