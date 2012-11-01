"""
-------------------------
Vdsm Code Coverage Plugin
-------------------------

Plugin enables vdsm_code_coverage functionality on hosts and fetch results.

CLI Options:
------------
    --with-vdsm-code-coverage enable plugin

Configuration Options:
----------------------
    [VDSM_CODE_COVERAGE]
    enabled - to enable the plugin (true/false)
    vdsm_repo - link to vdsm git repo
    vdsmtests_repo - link to vdsm tests git repo
    ruth_repo - link to ruth repo
    vdsm_root_path - vdsm path for root folder
"""

import os
import sys
import shutil
from art.test_handler.plmanagement import Component, implements, get_logger, PluginError
from art.test_handler.plmanagement.interfaces.application import IConfigurable, IApplicationListener
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
                                                    IConfigValidation
from art.test_handler.plmanagement import common
from utilities.machine import Machine, LINUX


logger = get_logger("vdsm_code_coverage")

COVERAGE_SECTION = 'VDSM_CODE_COVERAGE'
VDSM_REPO = 'vdsm_repo'
VDSM_TESTS = 'vdsmtests_repo'
RUTH = 'ruth_repo'
REST = 'REST_CONNECTION'
PARAMETERS = 'PARAMETERS'
VDS_PASSWORD = 'vds_password'
VDS = 'vds'
VDSM_SERVER_PATH = 'vdsm_root_path'

DEBUG_CLIENT = 'debugPluginClient.py'
VDSM_DEBUG_PLUGIN = 'vdsm-debug-plugin'
PYTHON_COVERAGE = 'python-coverage'

DEFAULT_STATE = False
ENABLED = 'enabled'


class VDSMCoverageError(PluginError):
    pass


class VDSMCodeCoverage(Component):
    """
    Plugin enables vdsm_code_coverage functionality on hosts and fetch results.
    """
    implements(IConfigurable, IApplicationListener, IPackaging, IConfigValidation)
    name = 'VDSM code coverage'

    def __init__(self):
        super(VDSMCodeCoverage, self).__init__()
        self.machines = {}
        self.path_to_vdsm = None
        self.res_dir = None
        self.scheme = None
        self.ruth_git = None

    @classmethod
    def add_options(cls, parser):
        out = os.path.expanduser("~/results/vdsm_coverage")
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        msg = "Specify target directory, where results will be stored (default: %(const)s)."
        group.add_argument('--with-vdsm-code-coverage', action="store", \
                dest='vdsm_code_coverage', help=msg, const=out, \
                default=None, nargs='?')

    def __prepare_hosts(self):
        path_to_debug_client = os.path.join(self.path_to_vdsm, DEBUG_CLIENT)
        for name, mobj in self.machines.items():
            logger.info("Preparing %s for VDSM code coverage", name)
            # install python-coverage package, it is needed by vdsmDebugClient
            if not mobj.yum(PYTHON_COVERAGE, 'install'):
                raise VDSMCoverageError(\
                        "failed to install %s: %s" % (PYTHON_COVERAGE, name))
            # install vdsm-debug-plugin
            if not mobj.yum(VDSM_DEBUG_PLUGIN, 'install'):
                raise VDSMCoverageError(\
                        "failed to intall %s: %s" % (VDSM_DEBUG_PLUGIN, name))
            # copy vdsm-debug-client
            if not mobj.copyTo(path_to_debug_client, self.vdsm_server_path):
                raise VDSMCoverageError(\
                        "failed to copy debugClient to host: %s" % name)
            if not mobj.startService('ruthAgent'):
                raise VDSMCoverageError(\
                        "failed to start runthAgent on host: %s" % name)


    def __init_vdsm_agent(self, scheme):

        try:
            from agentUtils import connectAgent
            from coverageControl import VdsmCoverageProxy
        except ImportError:
            logger.error("Failed to import vdsm coverage requirements, "\
                    "please check paths to repos")
            raise

        for name, mobj in self.machines.items():
            agent = connectAgent('%s://%s:54321' % (scheme, name))
            mobj.vdsm_proxy = VdsmCoverageProxy(agent)

    def __start(self):
        for mobj in self.machines.values():
            logger.info("Start VDSM code coverage on %s", mobj.host)
            mobj.vdsm_proxy.start()

    def __stop(self):
        """
        Stops monitoring and fetch results.
        """
        for name, mobj in self.machines.items():
            if not hasattr(mobj, 'vdsm_proxy'):
                continue
            mobj.vdsm_proxy.stop()
            path = mobj.vdsm_proxy.getLocalCopyPath()
            if not os.path.exists(self.res_dir):
                os.makedirs(self.res_dir)
            target = os.path.join(self.res_dir, name) + '.tar.gz'
            logger.info("Storing VDSM code-coverage: %s -> %s", path, target)
            shutil.move(path, target)
            mobj.stopService('ruthAgent')

    def configure(self, params, conf):
        if not params.vdsm_code_coverage:
            return
        self.res_dir = params.vdsm_code_coverage

        vds_section = common.get_vds_section(conf)

        vds = conf[vds_section].as_list(VDS)
        vds_passwd = conf[vds_section].as_list(VDS_PASSWORD)

        for name, passwd in  zip(vds, vds_passwd):
            self.machines[name] = Machine(name, 'root', passwd).util(LINUX)

        self.path_to_vdsm = conf[COVERAGE_SECTION][VDSM_REPO]
        self.vdsm_server_path = conf[COVERAGE_SECTION][VDSM_SERVER_PATH]
        self.scheme = conf[REST]['scheme']

        # add vdsm-things into python_path
        paths = set(sys.path)
        paths.add(self.path_to_vdsm)
        paths.add(conf[COVERAGE_SECTION][VDSM_TESTS])
        paths.add(conf[COVERAGE_SECTION][RUTH])
        sys.path = list(paths)


    def on_application_exit(self):
        self.__stop()

    def on_application_start(self):
        self.__prepare_hosts()
        self.__init_vdsm_agent(self.scheme)
        self.__start()

    def on_plugins_loaded(self):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(COVERAGE_SECTION).as_bool(ENABLED)
        return params.vdsm_code_coverage or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'VDSM code coverage for ART'
        params['long_description'] = cls.__doc__.strip().replace('\n', ' ')
        params['requires'] = [ 'art-utilities' ]
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.vdsm_code_coverage_plugin']


    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(COVERAGE_SECTION, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec[VDSM_REPO] = 'string(default=None)'
        section_spec[VDSM_SERVER_PATH] = 'string(default=None)'
        section_spec[VDSM_TESTS] = 'string(default=None)'
        section_spec[RUTH] = 'string(default=None)'
        spec[COVERAGE_SECTION] = section_spec

