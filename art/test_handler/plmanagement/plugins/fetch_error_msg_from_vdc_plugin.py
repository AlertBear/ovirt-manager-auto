import re
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler, ITestSuiteHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
                                                    IConfigValidation

from utilities.machine import Machine, LINUX


logger = get_logger('error_fetcher')


CONF_SEC = 'ERROR_FETCHER'
PARAMETERS = 'REST_CONNECTION'
VDC = 'host'
ENABLED = 'enabled'
LOG_PATH = 'path_to_log'
VDC_PASSWD = 'vdc_root_password'
PARAMS = 'PARAMETERS'

DEFAULT_LOG_PATH = '/var/log/ovirt-engine/engine.log'
TEMP_FILE = '/tmp/tailed_engine_log.log'
DEFAULT_STATE = False


# TODO: Consider TestSuites in parallel.
# TODO: Consider TestCases in parallel.
# TODO: it is quite hard work with parallelism here (maybe not possible with this design)


class ErrorFetcher(Component):
    """
    Plugin collects error messages from VDC machine for test_cases which fail.
    """
    implements(IConfigurable, ITestCaseHandler, ITestSuiteHandler, IPackaging, \
                                                            IConfigValidation)
    name = "Errors fetcher"

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--fetch-errors', action='store_true', \
                dest='error_fetcher', help="enable plugin")
#        group.add_argument('--fe-vdc-pass', action='store', \
#                dest='fe_vdc_pass', help="Password for root account on VDC machine")
        group.add_argument('--fe-path-to-log', action='store', \
                dest='fe_path_to_log', help="Path to log on VDC machine")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        passwd = conf.get(PARAMS).get(VDC_PASSWD)
        self.vdc = Machine(conf[PARAMETERS][VDC], 'root', passwd).util(LINUX)
        self.path_to_log = params.fe_path_to_log
        self.path_to_log = self.path_to_log or conf.get(CONF_SEC).get(LOG_PATH)

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(CONF_SEC).as_bool(ENABLED)
        return params.error_fetcher or conf_en

    def pre_test_case(self, t):
        cmd = ['tail', '-fn0', self.path_to_log]
        rc, self.pid, err = self.ssh.runCmd(cmd, bg=(TEMP_FILE,))
        if rc:
            self.pid = None
            logger.error("Failed to tail %s: %s", self.path_to_log, err)

    def post_test_case(self, t):
        if getattr(self, 'pid', None) is not None:
            self.ssh.runCmd(['kill', '-15', str(self.pid)])
            self.pid = None
        else:
            return

        if t.status != t.TEST_STATUS_FAILED:
            return

        cmd = ['sed', '-n', '/ ERROR /,/ \(INFO\|DEBUG\|WARN\) / p', \
                TEMP_FILE, '|', 'grep', '-v', '\(INFO\|DEBUG\|WARN\)']
        rc, out, err = self.ssh.runCmd(cmd)
        if rc:
            if not out.strip() and not err.strip():
                logger.warn("VDC(%s) log doesn't contain error messages", self.vdc.host)
            else:
                logger.warn("Failed to fetch error message from %s: %s, %s, %s", \
                        self.vdc.host, cmd, rc, out+err)
        elif not out.strip() and not err.strip():
            logger.warn("VDC(%s) log doesn't contain error messages", self.vdc.host)
        else:
            logger.error("Errors fetched from VDC(%s): %s", self.vdc.host, out)

    def test_case_skipped(self, t):
        pass

    def pre_test_suite(self, s):
        self.ssh = self.vdc.ssh.__enter__()

    def post_test_suite(self, s):
        if self.ssh is not None:
            self.ssh.__exit__(None, None, None)

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Plugin for ART, which collects ERRORs messages from VDC log.'
        params['long_description'] = cls.__doc__
        params['requires'] = ['art-utilities']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.fetch_error_msg_from_vdc_plugin']


    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(CONF_SEC, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec[LOG_PATH] = "string(default='%s')" % DEFAULT_LOG_PATH
        spec[CONF_SEC] = section_spec
        parms_spec = spec.get(PARAMS, {})
        parms_spec[VDC_PASSWD] = "string(default=None)"
        spec[PARAMS] = parms_spec

