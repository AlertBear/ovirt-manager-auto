#!/bin/env python

import os
import sys
import re
import art.test_handler.plmanagement as plcore
from art.test_handler.plmanagement.interfaces import packaging
from art.test_handler.plmanagement.manager import PluginManager
from subprocess import Popen, PIPE

#SETUP_DIR = 'plugin_setups'
SETUP_DIR = './'
SETUP_NAME = 'setup_%s_plugin.py'
PREFIX_NAME = 'art-plugin'

RELEASE = os.environ.get('RELEASE', "1")
VERSION = os.environ.get('VERSION', "1.0.0")
CHANGELOG = os.environ.get('CHANGELOG', None)


SETUP_SCRIPT = """

from utilities.setup_utils import setup

kwargs = {params}
setup(**kwargs)
"""

class PluginSetupManager(PluginManager):
    packages = plcore.ExtensionPoint(packaging.IPackaging)



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
        params['requires'].append('art = %s' % VERSION)
    #if 'release' not in params:
    #    params['release'] = RELEASE
    # NOTE: currently we want to have same version and release for all packages
    params['release'] = RELEASE
    params['version'] = VERSION
    params['changelog'] = CHANGELOG
    #if 'pip_deps' not in params:
    #    params['pip_deps'] = []
    #if params['pip_deps']:
    #    if 'python-pip' not in params['requires']:
    #        params['requires'].append('python-pip')
    #params['pipdeps'] = params.pop('pip_deps')
    params.pop('pip_deps', None)
    params['config'] = {'bdist_rpm': {'build_requires': 'art-utilities'}}

def main():

    manager = PluginSetupManager()
    res = {}
    for pl in manager.packages:
        params = {'version': '1.0', 'platforms': 'Linux', 'license': 'GPL2'}
        pl.fill_setup_params(params)
        check_params(params)

        file_name = os.path.join(SETUP_DIR, SETUP_NAME % params['name'])

        params['name'] = '%s-%s' % (PREFIX_NAME, params['name'])

        py_mods = [x.rsplit('.', 1)[-1]+'.py' for x in params['py_modules'] ]
        if py_mods:
            post_install = ''
            for m_name in py_mods:
                post_install += "sed -i 's/art[.]\(rhevm\|gluster\|jasper\|\)_api/\\1_api/g' "\
                        "%%{python_sitelib}/art/test_handler/"\
                        "plmanagement/plugins/%s\n" % m_name
            params['post_install_script'] = post_install
#                " &> /dev/null"

        manifest = [
                "exclude art/test_handler/plmanagement/plugins/__init__.py",
                "include %s" % file_name,
                ]
        params['manifest_list'] = manifest

        args = globals()
        args.update(locals())
        with open(file_name, 'w') as fh:
            fh.write(SETUP_SCRIPT.format(**args))

        cmd = ['python', file_name]
        cmd.extend(sys.argv[1:])
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        result = {}
        print "Processing %s plugin" % params['name']
        result['out'], result['err'] = p.communicate()
        result['ec'] = p.returncode
        if result['ec']:
            print "%s failed:\n %s\n%s" % (params['name'], result['out'], result['err'])
        res[params['name']] = result
        if os.path.exists(file_name):
            os.unlink(file_name)

    return res

if __name__ == "__main__":
    res = main()
    report = [x for x, y in res.items() if y['ec']]
    if report:
        print "Plugins packaging failed: %s" % ', '.join(report)
        sys.exit(1)

