import os
import sys
import shutil
from test_handler.plmanagement import Component, implements, get_logger
from test_handler.plmanagement.interfaces.application import IConfigurable, IApplicationListener

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


class VDSMCoverageError(Exception):
    pass


class VDSMCodeCoverage(Component):
    """
    Plugin enables vdsm_code_coverage functionality on hosts and fetch results.
    """
    implements(IConfigurable, IApplicationListener)
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

        vds = conf[PARAMETERS].as_list(VDS)
        vds_passwd = conf[PARAMETERS].as_list(VDS_PASSWORD)

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
        return params.vdsm_code_coverage is not None

