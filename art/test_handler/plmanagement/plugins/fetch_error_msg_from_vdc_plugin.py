"""
---------------------
Errors Fetcher Plugin
---------------------
Plugin collects error messages from VDC machine for test_cases which fail.

CLI Options:
------------
    --fetch-errors  Enable the plugin
    --fe-vdc-pass   Password for root account on VDC machine
    --fe-path-to-log    Path to log on VDC machine

Configuration Options:
----------------------
    | **[ERROR_FETCHER]**
    | **enabled** - to enable the plugin (true/false)
    | **path_to_log** - path to log on VDC machine
    |
    | **[PARAMETERS]**
    | **vdc_root_password** - password for root account on VDC machine
"""

from art.test_handler.plmanagement import Component, implements, get_logger, \
    ThreadScope
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.tests_listener import \
    ITestCaseHandler, ITestSuiteHandler
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
TEMP_FILE_PREF = '/tmp/tailed_engine_log'
TEMP_FILE = '%s-%%s.log' % TEMP_FILE_PREF
DEFAULT_STATE = False


# TODO: Consider TestSuites in parallel.


class ErrorFetcher(Component):
    """
    Plugin collects error messages from VDC machine for test_cases which fail.
    """
    implements(IConfigurable, ITestCaseHandler, ITestSuiteHandler, IPackaging,
               IConfigValidation)
    name = "Errors fetcher"

    def __init__(self, *args, **kwargs):
        super(ErrorFetcher, self).__init__(*args, **kwargs)
        self.th = ThreadScope()

    @property
    def pid(self):
        return self.th.pid

    @property
    def temp_file(self):
        return self.th.tmp

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--fetch-errors', action='store_true',
                           dest='error_fetcher', help="enable plugin")
        group.add_argument('--fe-path-to-log', action='store',
                           dest='fe_path_to_log',
                           help="Path to log on VDC machine")

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
        self.th.tmp = TEMP_FILE % self.th.th_id
        rc, self.th.pid, err = self.ssh.runCmd(cmd, bg=(self.temp_file,))
        if rc:
            logger.error("Failed to tail %s: %s", self.path_to_log, err)
            self.th.destroy()

    def __fetch_logs(self, t):
        cmd = ['sed', '-n', '/ ERROR /,/ \(INFO\|DEBUG\|WARN\) / p',
               self.temp_file, '|', 'grep', '-av', '\(INFO\|DEBUG\|WARN\)']
        rc, out, err = self.ssh.runCmd(cmd)
        if rc:
            if not out.strip() and not err.strip():
                logger.warn("VDC(%s) log doesn't contain error messages",
                            self.vdc.host)
            else:
                logger.warn("Failed to fetch error message from %s: "
                            "%s, %s, %s", self.vdc.host, cmd, rc, out + err)
        elif not out.strip() and not err.strip():
            logger.warn("VDC(%s) log doesn't contain error messages",
                        self.vdc.host)
        else:
            logger.error("Errors fetched from VDC(%s): %s", self.vdc.host, out)

    def __kill(self, sig):
        self.ssh.runCmd(['kill', sig, str(self.pid)])

    def _kill_tail(self):
        self.__kill('-15')
        rc, _, _ = self.ssh.runCmd(['stat', '/proc/%s' % self.pid])
        if rc == 0:
            self.__kill('-9')
            # I don't know what else to do ...

    def post_test_case(self, t):
        try:
            if self.pid is not None:
                self._kill_tail()
            else:
                return

            if t.status == t.TEST_STATUS_FAILED:
                self.__fetch_logs(t)

            self.ssh.runCmd(['rm', '-f', str(self.temp_file)])
        finally:
            self.th.destroy()

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
        params['description'] = 'Plugin for ART, which collects ERRORs '\
            'messages from VDC log.'
        params['long_description'] = cls.__doc__.strip()
        params['requires'] = ['art-utilities']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'fetch_error_msg_from_vdc_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(CONF_SEC, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec[LOG_PATH] = "string(default='%s')" % DEFAULT_LOG_PATH
        spec[CONF_SEC] = section_spec
        parms_spec = spec.get(PARAMS, {})
        parms_spec[VDC_PASSWD] = "string(default=None)"
        spec[PARAMS] = parms_spec
