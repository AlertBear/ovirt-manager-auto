"""
-----------
Trac Plugin
-----------

This plugin provides access to the Trac site.
This plugin is triggered by 'trac' attribute of test_case.
It skips test_case when provided trac_ticket_id isn't closed.

Test Case Configuration
-----------------------

<trac>ticket_id, ...</trac>

CLI Options
-----------
    --with-trac Enables plugin

Configuration File Options
--------------------------
    [TRAC]
    enabled - True/False, enables plugin
    url - trac site URL, 'http(s)://[user[:pass]@]host[:port]/path/to/rpc/entry'
            default: https://engineering.redhat.com/trac/automation/rpc

"""

import re
import httplib
import json
from art.test_handler.exceptions import SkipTest
from art.test_handler.plmanagement import Component, implements, get_logger,\
     PluginError
from art.test_handler.plmanagement.interfaces.application import\
     IConfigurable, IApplicationListener
from art.test_handler.plmanagement.interfaces.tests_listener import\
     ITestCaseHandler, ITestGroupHandler, ITestSkipper
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
              IConfigValidation

logger = get_logger('trac')

CONF_SEC = 'TRAC'
DEFAULT_STATE = False
DEFAULT_URL = 'https://engineering.redhat.com/trac/automation/rpc'
ENABLED = 'enabled'

URL_REG = re.compile('^(?P<scheme>https?)://((?P<user>[^@:]+)'\
        '(:(?P<pass>[^@]+)?)@)?(?P<host>[^/:]+)(:(?P<port>[0-9]+))?'\
        '(?P<path>.+)?$')

CONTENT_TYPE = 'application/json'


class TracPluginError(PluginError):
    pass


class TracRequestFailed(TracPluginError):
    pass


class Trac(Component):
    """
    Plugin provides access to Trac site.
    """
    implements(IConfigurable, ITestCaseHandler, ITestGroupHandler, \
            IConfigValidation, IPackaging)
    name = "Trac"

    def __init__(self):
        super(Trac, self).__init__()
        self._cache = {}

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-trac', action='store_true', \
                dest='trac_enabled', help="enable plugin")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        site = conf[CONF_SEC]['url']
        m = URL_REG.match(site)
        if not m:
            raise TracPluginError("can not parse url: %s" % site)

        site = m.groupdict()
        if site['user'] is not None:
            logger.warn("%s: only anonymous access is supported" % site['user'])

        if site['scheme'] == 'http':
            self.http_class = httplib.HTTPConnection
        elif site['scheme'] == 'https':
            self.http_class = httplib.HTTPSConnection
        else:
            assert False, "only http or https is accepted: '%s'" % site['scheme']

        logger.debug("Connecting to Trac with %s", site)
        self.path = site['path'] or ""
        self.headers = {'Content-Type': CONTENT_TYPE,
                        'Accept': CONTENT_TYPE}
        self.host = site['host']
        if site['port'] is not None:
            self.port = int(site['site'])
        else:
            self.port = None

    def _should_be_skipped(self, test):
        ids = getattr(test, 'trac', "").strip()
        if not ids:
            return

        ids = ids.replace(',', ' ').split(' ')
        for id_ in ids:
            ticket = self._ticket(id_)
            logger.info("TRAC<%s> '%s': %s", id_, ticket['summary'], ticket['status'])
            if ticket['status'].lower() != 'closed':
                raise SkipTest(ticket)

    def _ticket(self, id_):
        ticket = self._cache.get(id_, None)
        if ticket:
            return ticket

        body = '{"params": [%s], "method": "ticket.get"}' % id_
        con = None
        try:
            con = self.http_class(self.host, port=self.port)
            con.request('POST', self.path, body=body, headers=self.headers)
            res = con.getresponse()
        except Exception as ex:
            logger.debug(str(ex), exc_info=True)
            raise TracRequestFailed(ex)

        if res.status != 200:
            msg = "query '%s' returned %s %s" % (body, res.status, res.reason)
            raise TracRequestFailed(msg)

        ticket = json.loads(res.read())
        if ticket['error']:
            raise TracRequestFailed(ticket['error'])

        ticket = ticket['result'][3]
        self._cache[id_] = ticket

        return ticket

    def pre_test_case(self, t):
        pass

    def __set_status(self, elm):
        try:
            self._should_be_skipped(elm)
        except SkipTest:
            st = getattr(elm, 'status', elm.TEST_STATUS_FAILED)
            if st in (elm.TEST_STATUS_FAILED, elm.TEST_STATUS_ERROR):
                elm.status = elm.TEST_STATUS_SKIPPED

    def post_test_case(self, t):
        self.__set_status(t)

    def pre_test_group(self, g):
        pass

    def post_test_group(self, g):
        self.__set_status(g)

    def test_group_skipped(self, g):
        pass

    def test_case_skipped(self, t):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[CONF_SEC].as_bool(ENABLED)
        return params.trac_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower()
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Trac plugin for ART'
        params['long_description'] = cls.__doc__
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.trac_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(CONF_SEC, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec['url'] = "is_url_alive(default='%s')" % DEFAULT_URL
        spec[CONF_SEC] = section_spec

