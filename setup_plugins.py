#!/bin/env python

import os
import sys
import re
import art.test_handler.plmanagement as plcore
from art.test_handler.plmanagement import implements
from art.test_handler.plmanagement.interfaces import packaging
from art.test_handler.plmanagement.manager import PluginManager
from subprocess import Popen
from configobj import ConfigObj

#SETUP_DIR = 'plugin_setups'
SETUP_DIR = './'
SETUP_NAME = 'setup_%s_plugin.py'
PRE_INSTALL_FILE = 'preinstall_script'
SETUP_CFG_FILE = 'setup.cfg'
PREFIX_NAME = 'art'
MANIFEST_FILE = "PLMANIFEST.in"
DEFAULT_RELEASE = 1

PRE_INSTALL = """\
python << __END__
import pip

PIP_DEPS = {pip_deps}

for dep in PIP_DEPS:
    if pip.main(['install', '-q', '--upgrade', dep]):
        raise Exception("failed to install %s" % dep)
__END__
"""

SETUP_SCRIPT = """

from setuptools import setup
#from distutils.core import setup

kwargs = {params}
setup(**kwargs)
"""

class PluginSetupManager(PluginManager):
    packages = plcore.ExtensionPoint(packaging.IPackaging)


def gen_manifest(setup_file):
    path_to_manifest_in = os.path.join(SETUP_DIR, MANIFEST_FILE)
    with open(path_to_manifest_in, 'w') as fh:
        fh.write("exclude test_handler/plmanagement/plugins/__init__.py\n")
        fh.write("include %s\n" % setup_file)
#    sys.argv.append('-t')
#    sys.argv.append(path_to_manifest_in)

def gen_config(name, params):
    sdist = {'template': MANIFEST_FILE}
    bdist_rpm = {}
    bdist_rpm['release'] = params['release']
    bdist_rpm['requires'] = ' '.join(params['requires'])
    bdist_rpm['pre_install'] = PRE_INSTALL_FILE
    del params['requires']
    conf = ConfigObj()
    conf['sdist'] = sdist
    conf['bdist_rpm'] = bdist_rpm
    with open(name, 'w') as fh:
        conf.write(fh)

def gen_pre_install(pip_deps):
    with open(PRE_INSTALL_FILE, 'w') as fh:
        fh.write(PRE_INSTALL.format(pip_deps=pip_deps))

def check_params(params):
    if 'maintainer' not in params and 'author' in params:
        params['maintainer'] = params['author']
    if 'maintainer_email' not in params:
        if 'author' in params and params['author'] == params['maintainer']:
            if 'author_email' in params:
                params['maintainer_email'] = params['author_email']
    if 'long_description' not in params and 'description' in params:
        params['long_description'] = params['description']
    if 'requires' not in params:
        params['requires'] = []
    for dep in params['requires']:
        dep = dep.split()[0]
        if re.match('^art$', dep):
            break
    else:
        params['requires'].append('art')
    if 'release' not in params:
        params['release'] = DEFAULT_RELEASE
    if 'pip_deps' not in params:
        params['pip_deps'] = []
    if params['pip_deps']:
        if 'python-pip' not in params['requires']:
            params['requires'].append('python-pip')

def setup():
    if not os.path.exists(SETUP_DIR):
        os.makedirs(SETUP_DIR)
    manager = PluginSetupManager()
    res = {}
    for pl in manager.packages:
        params = {'version': '1.0', 'platforms': 'Linux', 'license': 'GPL2'}
        pl.fill_setup_params(params)
        check_params(params)

        file_name = os.path.join(SETUP_DIR, SETUP_NAME % params['name'])
        #config_file = os.path.join(SETUP_DIR, SETUP_CFG_FILE % params['name'])
        # THERE is problem with static config_name (it is bind to setup.cfg)
        config_file = SETUP_CFG_FILE

        gen_manifest(file_name)
        gen_config(config_file, params)
        gen_pre_install(params.pop('pip_deps'))

        params['name'] = '%s-%s' % (PREFIX_NAME, params['name'])
#        params['install_requires'].append(params['name'])
        args = globals()
        args.update(locals())
        with open(file_name, 'w') as fh:
            fh.write(SETUP_SCRIPT.format(**args))


        cmd = ['python', file_name]
        cmd.extend(sys.argv[1:])
        p = Popen(cmd)
        res[params['name']] = p.wait()
        if os.path.exists(file_name):
            os.unlink(file_name)

    print res

if __name__ == "__main__":
    try:
        setup()
    finally:
        for name in (SETUP_CFG_FILE, PRE_INSTALL_FILE, MANIFEST_FILE):
            if os.path.exists(name):
                os.unlink(name)

