"""
----------------
Log Stash Plugin
----------------

Plugin adds hyperlinks pointed to logs collected from engine and vdsm
by logstash tool: http://logstash.net/

Configuration Options:
----------------------
    | **[LOGSTASH]**
    | **enabled** - to enable the plugin (true/false)
    | **site** - link to logstash web page
    | **summary_xml_dir** - dir where to put the summary xml files in
    | **[[vdc]]** - sub-section to specify log names-paths pairs from vdc server,
    |    *default*: **engine** = /var/log/jbossas/standalone/engine/engine.log
    |
    | **[[vds]]** - sub-section to specify log names-paths pairs from vds server,
    |    *default*: **vdsm** = /var/log/vdsm/vdsm.log
"""

import os
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

from art.test_handler.plmanagement.plugins.jenkins_summary_logger import getLogger


DEFUALT_SITE = 'http://log-server.eng.lab.tlv.redhat.com:9292'
DEFAULT_VDC_LOG = '/var/log/jbossas/standalone/engine/engine.log'
DEFAULT_VDS_LOG = '/var/log/vdsm/vdsm.log'
DEFAULT_SUMMARY_XML_DIR = os.environ.get('WORKSPACE', '.')

ENABLED = 'enabled'
SITE = 'site'
VDC_LOGS = 'vdc'
VDS_LOGS = 'vds'
SUMMARY_XML_DIR = 'summary_xml_dir'

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
        ## for the jenkins summary xml files
        self.xmllogger = getLogger('logstash', conf[LOGSTASH_SEC][SUMMARY_XML_DIR])
        self.xmllogger.field(name='What do the colors on the test title mean?',
                             cdata=('<p align="center"><font color="#990000">'
                                   'Failed</font> <font color="#999900">'
                                   'Skipped</font> <font color="#000099">'
                                   'Passed</font></p>'))

    def pre_test_case(self, t):pass
    def test_case_skipped(self, t):pass

    def post_test_case(self, tc):
        self.__log_results("Logs for test case", tc.start_time, tc.end_time)
        #self.__summary_results("Test %s, it %d" % (tc.test_name, tc.serial), tc.start_time, tc.end_time, tc.status)

    def pre_test_suite(self, ts): pass

    def post_test_suite(self, ts):
        self.__log_results("Logs for test suite", ts.start_time, ts.end_time)
        self.__summary_results('Test Suite', ts.start_time, ts.end_time)
        ## just make sure that all the xml tags are closed
        self.xmllogger.close_all()

    def __log_results(self, title, st, et):
        links = self.__generate_links(st, et)
        for name, link in links.items():
            logger.debug("%s -> %s: %s\n", title, name, link)

    def __generate_links(self, st, et):
        et = self.__format_time(et)
        st = self.__format_time(st)
        res = {}
        ## get the vdc logs
        for name, path in self.vdc_logs.items():
            name, link = self.__generate_link(self.vdc, name, path, st, et)
            res[name] = link
        ## for each vds, iterate through it's logs
        for vds in self.vds:
            for name, path in self.vds_logs.items():
                name, link = self.__generate_link(vds, name, path, st, et)
                res[name] = link
        return res

    def __generate_link(self, machine, name, log_path, st, et):
        name = "%s/%s" % (machine, name.upper())
        return name, self.__get_query(st, et, source_host=machine, source_path=log_path)

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

    def __summary_results(self, title, st, et, status='Passed'):
        """
        Creates a new field and a new table with the logstash links for the test case/suite
        """
        ## make sure we are not inside a table, if we are not this will do nothing
        et = self.__format_time(et)
        st = self.__format_time(st)
        self.xmllogger.table_close()
        if status.startswith('Pass'):
            color = '#000099'
        elif status == 'Skipped':
            color = '#999900'
        else:
            color = '#990000'

        hosts = ['%s' % self.vdc] + ['%s' % vds for vds in self.vds]
        self.xmllogger.field(name=title,
                             titlecolor=color,
                             value=" Aggregated logs",
                             href=self.__get_query(st, et, source_host=hosts))
        self.xmllogger.table()
        ## add the rows
        self.xmllogger.table_add_row('ENGINE:%s' % self.vdc,
                href=self.__get_query(st, et, source_host=self.vdc))
        for vds in self.vds:
            self.xmllogger.table_add_row('VDS:%s' % vds,
                    href=self.__get_query(st, et, source_host=vds))
        ## add the columns and populate the cells
        for name, path in self.vdc_logs.items():
            self.xmllogger.table_add_column(path,
                                href=self.__get_query(st, et, source_path=path))
            self.xmllogger.table_add_cell('ENGINE:%s' % self.vdc,
                                path,
                                '%s:%s' % (self.vdc, path),
                                href=self.__get_query(st, et, source_host=self.vdc, source_path=path))
        for vds in self.vds:
            for name, path in self.vds_logs.items():
                self.xmllogger.table_add_column(path,
                                href=self.__get_query(st, et, source_path=path))
                self.xmllogger.table_add_cell('VDS:%s' % vds,
                                path,
                                '%s:%s' % (vds, path),
                                href=self.__get_query(st, et, source_host=vds, source_path=path))

    def __get_query(self, st, et, **conditions):
        ## handle arrays and tuples as 'or' conditions
        for key, val in conditions.iteritems():
            if not isinstance(val, basestring):
                val = '("' + '" OR "'.join(val) + '")'
            else:
                val = '"%s"' % val
            conditions[key] = val
        ## aggregate all into 'and' conditions
        q = 'AND '.join('@%s:%s ' % it for it in conditions.iteritems()) \
            + "AND @timestamp:[%s TO %s]" % (st, et)
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
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.logstash_plugin',
                               'art.test_handler.plmanagement.plugins.jenkins_summary_logger',
                               ]

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(LOGSTASH_SEC, {})
        section_spec[SITE] = "string(default='%s')" % DEFUALT_SITE
        section_spec[ENABLED] = "boolean(default=False)"
        section_spec[VDC_LOGS] = {}
        section_spec[VDC_LOGS]['engine'] = "string(default='%s')" % DEFAULT_VDC_LOG
        section_spec[VDS_LOGS] = {}
        section_spec[VDS_LOGS]['vdsm'] = "string(default='%s')" % DEFAULT_VDS_LOG
        section_spec[SUMMARY_XML_DIR] = "string(default='%s')" % DEFAULT_SUMMARY_XML_DIR
        spec[LOGSTASH_SEC] = section_spec

