
import time
import datetime
from socket import error as SocketException, gethostbyaddr
from urllib import quote

from art.test_handler.plmanagement import Component, implements, get_logger,\
     PluginError, ThreadScope
from art.test_handler.plmanagement.interfaces.application import\
     IConfigurable, IApplicationListener
from art.test_handler.plmanagement.interfaces.tests_listener import\
     ITestCaseHandler, ITestGroupHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
              IConfigValidation
from art.test_handler.plmanagement.interfaces.tests_listener import \
        ITestSuiteHandler, ITestCaseHandler


DEFUALT_SITE = 'http://log-server.eng.lab.tlv.redhat.com:9292'
DEFAULT_VDC_LOG = '/var/log/jbossas/standalone/engine/engine.log'
DEFAULT_VDS_LOG = '/var/log/vdsm/vdsm.log'

ENABLED = 'enabled'
SITE = 'site'
VDC_LOGS = 'vdc'
VDS_LOGS = 'vds'

LOGSTASH_SEC = 'LOGSTASH'
PARAMETERS = 'PARAMETERS'
VDC_PARAMS = 'REST_CONNECTION'
VDS = 'vds'
VDC = 'host'


logger = get_logger('logstash')


class LogStash(Component):
    """
    Plugin adds hyperlinks pointed to logs collected from engine and vdsm
    """
    implements(IConfigurable, IConfigValidation, IPackaging, ITestCaseHandler, \
            ITestSuiteHandler)

    name = "LogStash"

    def __init__(self):
        super(LogStash, self).__init__()
        self.th = ThreadScope()


    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        self.site = conf[LOGSTASH_SEC][SITE]
        self.vds = [self.__get_name(x) for x in conf[PARAMETERS].as_list(VDS)]
        self.vds_logs = conf[LOGSTASH_SEC][VDS_LOGS]
        self.vdc = self.__get_name(conf[VDC_PARAMS][VDC])
        self.vdc_logs = conf[LOGSTASH_SEC][VDC_LOGS]

    def pre_test_case(self, t):pass
    def test_case_skipped(self, t):pass

    def post_test_case(self, tc):
        self.__log_results("Logs for test case", tc.start_time, tc.end_time)

    def pre_test_suite(self, s):pass

    def post_test_suite(self, ts):
        self.__log_results("Logs for test suite", ts.start_time, ts.end_time)

    def __log_results(self, title, st, et):
        links = self.__generate_links(st, et)
        for name, link in links.items():
            logger.info("%s -> %s: %s\n", title, name, link)

    def __generate_links(self, st, et):
        et = self.__format_time(et)
        st = self.__format_time(st)

        res = {}
        for name, path in self.vdc_logs.items():
            name, link = self.__generate_link(self.vdc, name, path, st, et)
            res[name] = link
        for vds in self.vds:
            for name, path in self.vds_logs.items():
                name, link = self.__generate_link(vds, name, path, st, et)
                res[name] = link
        return res

    def __generate_link(self, machine, name, log_path, st, et):
        name = "%s/%s" % (machine, name.upper())
        return name, self.__get_query(machine, st, et, log_path)

    def __format_time(self, t):
        return t.strftime("%Y-%m-%dT%X")

    def __get_name(self, name):
        try:
            name = gethostbyaddr(name)[0]
        except SocketException as ex:
            # use original name, but there is not warranty that logstash
            # will match that machine
            logger.warn("cannot resolve '%s' hostname: %s", name, ex)
        return name

    def __get_query(self, machine, st, et, log):
        q = "@source_host:\"%s\" AND @source_path:\"%s\" AND "\
                "@timestamp:[%s TO %s]" % (machine, log, st, et)
        # NOTE: maybe source_path is not necessarily
        return "%s/search?q=%s" % (self.site, quote(q))

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[LOGSTASH_SEC].as_bool(ENABLED)
        return params.logstash_enabled or conf_en

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-logstash', action='store_true', \
                dest='logstash_enabled', help="enable plugin")

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower()
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'LogStash plugin for ART'
        params['long_description'] = cls.__doc__
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.logstash_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(LOGSTASH_SEC, {})
        section_spec[SITE] = "string(default='%s')" % DEFUALT_SITE
        section_spec[ENABLED] = "boolean(default=False)"
        section_spec[VDC_LOGS] = {}
        section_spec[VDC_LOGS]['engine'] = "string(default='%s')" % DEFAULT_VDC_LOG
        section_spec[VDS_LOGS] = {}
        section_spec[VDS_LOGS]['vdsm'] = "string(default='%s')" % DEFAULT_VDS_LOG
        spec[LOGSTASH_SEC] = section_spec

