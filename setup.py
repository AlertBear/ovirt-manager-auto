#!/bin/env python
import os
#from distutils.core import setup
from utilities.setup_utils import setup, common


PIP_DEPS = [
        'configobj>=4.7.2',
        ]

RELEASE = 1

PACKAGE_NAME = 'art'
DESCRIPTION = "Automated framework for testing REST APIs applications, "\
            "uses generateDS tool to auto generate Python data structures"

TEST_DATA_PATH = '/opt'

SUB_MODULES = ['art',
                'art.core_api',
                'art.test_handler',
                'art.test_handler.handler_lib',
                'art.test_handler.plmanagement',
                'art.test_handler.plmanagement.interfaces',
                'art.generateDS', # WILL be replaced by deps
              ]

PACKAGE_DATA = {
        PACKAGE_NAME: ['art/conf/elements.conf', 'art/conf/settings.conf', 'art/conf/specs/main.spec'],
        }

DATA_FILES = [
        'art/conf/*.conf',
        'art/conf/specs/*.spec',
        # TODO: list of tests
        ]
DATA_FILES = common.expand_paths(TEST_DATA_PATH, *DATA_FILES)

PY_MODULES = ['art.__main__', 'art.__init__', 'art.run',
                'art.generateIds',
                #'art.test_handler.plmanagement.plugins.xml_results_formater_plugin',
                'art.test_handler.plmanagement.plugins.results_collector_plugin',
                # FIXME: don't like these default plugins
                'art.test_handler.plmanagement.plugins.resources_plugin',
                ]


DEPS = [
        # REQUIRES
        'python >= 2.6',
        'python-lxml',
        'python-argparse', # this can cause problem on py2.7
        'python-lockfile',
        'python-tpg',
        'PyXML',
        'python-dateutil',
        'python-pip',
        'art-utilities',
        ]


SCRIPT = """\
if [ $1 -eq 1 ] ;
then
  echo "export PYTHONPATH=\$PYTHONPATH:/opt/art:" > %{_sysconfdir}/profile.d/art.sh
  chmod +x %{_sysconfdir}/profile.d/art.sh
  . %{_sysconfdir}/profile.d/art.sh
fi

"""

POST_INSTALL="""\
find %{{python_sitelib}}/art -type f -regex .*[.]py$ -exec sed -i -e '/^# *__package_exclude_start__.*/,/^# *__package_exclude_end__.*/ d' -e 's/art[.]\(rhevm\|gluster\|jasper\)_api/\\1_api/g' '{{}}' \;
#find %{{python_sitelib}}/art -type f -regex .*[.]py$ -exec sed -i 's/art[.]\(rhevm\|gluster\|jasper\)_api/\\1_api/g' \;

#python << __EOF__
#from configobj import ConfigObj
#conf = ConfigObj('{specs_file}', stringify=False)
#conf['RUN']['elements_conf'] = "path_exists(default='{elements_path}')"
#with open('{specs_file}', 'w') as fh:
#    conf.write(fh)
#__EOF__
sed -i 's|^elements_conf.*$|elements_conf = path_exists(default="{elements_path}")|g' {specs_file} &> /dev/null
""".format(
        elements_path=os.path.join(TEST_DATA_PATH, 'art', 'conf', 'elements.conf'),
        specs_file=os.path.join(TEST_DATA_PATH, 'art', 'conf', 'specs', 'main.spec'))

UN_SCRIPT = """\
if [ $1 -eq 0 ] ;
then
    rm -rf %{_sysconfdir}/profile.d/art.sh
fi

"""

MANIFEST = [
#           'recursive-include art/tests *.conf *.xml',
           'recursive-include art/conf *.conf *.spec',
           'prune art/rhevm_api',
           'prune art/gluster_api',
           'prune art/jasper_api',
#           'prune art/generateDS',
           'prune art/tests',
#           'prune art/test_handler/plmanagement/plugins',
#           'include art/test_handler/plmanagement/plugins/__init__.py',
           ]

if __name__ == '__main__':

    setup(
            name=PACKAGE_NAME,
            version='1.0',
            release=RELEASE,
            author='Red Hat',
            author_email='edolinin@redhat.com',
            maintainer='Red Hat',
            maintainer_email='edolinin@redhat.com',
            description='Automated REST Testing Framework',
            long_description=DESCRIPTION,
            platforms='Linux',
            scripts=['scripts/art', 'scripts/art-setup'],
#                license='?',
            package_dir={PACKAGE_NAME: 'art'},
            packages=SUB_MODULES,
            py_modules=PY_MODULES,
            package_data=PACKAGE_DATA,
            data_files=DATA_FILES,
            manifest_list=MANIFEST,
            pre_install_script=SCRIPT,
            post_install_script=POST_INSTALL,
            post_uninstall_script=UN_SCRIPT,
            pipdeps=PIP_DEPS,
            requires=DEPS,
    )

