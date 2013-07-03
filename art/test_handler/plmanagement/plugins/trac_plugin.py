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
    --with-trac  Enable plugin

Configuration File Options
--------------------------
    | **[TRAC]**
    | **enabled** - True/False, enables plugin
    | **url** - trac site URL,
                'http(s)://[user[:pass]@]host[:port]/path/to/rpc/entry'
    |        *default*: https://engineering.redhat.com/trac/automation/rpc
    | **path_to_issuedb** Path to file where are you can map bugs to cases

Usage
-----

Issues DB syntax
++++++++++++++++
<issues>
  <issue ids="xx,yy">
    <case_name>regex</case_name>
    <config_name>regex</config_name>
  </issue>
</issues>
"""

import re
import httplib
import json
from art.test_handler.exceptions import SkipTest
from art.test_handler.plmanagement import Component, implements, get_logger,\
    PluginError
from art.test_handler.plmanagement.interfaces.application import\
    IConfigurable
from art.test_handler.plmanagement.interfaces.tests_listener import\
    ITestCaseHandler, ITestGroupHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation
from art.test_handler import find_config_file
from utilities.issuesdb import IssuesDB

logger = get_logger('trac')

CONF_SEC = 'TRAC'
DEFAULT_STATE = False
DEFAULT_URL = 'https://engineering.redhat.com/trac/automation/rpc'
ENABLED = 'enabled'
PATH_TO_ISSUEDB = 'path_to_issuedb'

URL_REG = re.compile('^(?P<scheme>https?)://((?P<user>[^@:]+)'
                     '(:(?P<pass>[^@]+)?)@)?(?P<host>[^/:]+)'
                     '(:(?P<port>[0-9]+))?(?P<path>.+)?$')

CONTENT_TYPE = 'application/json'
TRAC_ID = 'trac'


class TracSkipTest(SkipTest):
    def __init__(self, ticket, site):
        super(TracSkipTest, self).__init__()
        self.ticket = ticket
        self.site = site

    def __str__(self):
        msg = "Known issue %s/ticket/%s" % (self.site, self.ticket)
        return msg


class TracPluginError(PluginError):
    pass


class TracRequestFailed(TracPluginError):
    pass


class Version(object):  # TODO: need to deduplicate
    def __init__(self, ver):
        self.ver = [int(x) for x in ver.split('.')]

    def __cmp__(self, ver):
        for a, b in zip(self.ver, ver.ver):
            d = a - b
            if d != 0:
                return d
        return 0

    def __str__(self):
        return '.'.join([str(x) for x in self.ver])

    def __contains__(self, ver):
        return self.__cmp__(ver) == 0


class Trac(Component):
    """
    Plugin provides access to Trac site.
    """
    implements(IConfigurable, ITestCaseHandler, ITestGroupHandler,
               IConfigValidation, IPackaging)
    name = "Trac"

    def __init__(self):
        super(Trac, self).__init__()
        self._cache = {}
        self.config_name = None
        self.issuedb = None
        self._version = None

    @property
    def version(self):
        if self._version is None:
            from art.rhevm_api.tests_lib.low_level.general\
                import getSystemVersion
            self._version = Version("%d.%d" % getSystemVersion())
        return self._version

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-trac', action='store_true',
                           dest='trac_enabled', help="enable plugin")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        from art.test_handler.test_runner import TestGroup
        TestGroup.add_elm_attribute('TEST_TRAC_ID', TRAC_ID)

        site = conf[CONF_SEC]['url']
        m = URL_REG.match(site)
        if not m:
            raise TracPluginError("can not parse url: %s" % site)

        site = m.groupdict()
        if site['user'] is not None:
            logger.warn("%s: only anonymous access is supported", site['user'])

        if site['scheme'] == 'http':
            self.http_class = httplib.HTTPConnection
        elif site['scheme'] == 'https':
            self.http_class = httplib.HTTPSConnection
        else:
            assert False, "only http or https is accepted: '%s'" %\
                site['scheme']

        logger.debug("Connecting to Trac with %s", site)
        self.path = site['path'] or ""
        self.headers = {'Content-Type': CONTENT_TYPE,
                        'Accept': CONTENT_TYPE}
        self.host = site['host']
        if site['port'] is not None:
            self.port = int(site['site'])
        else:
            self.port = None
        self.site_url = "%s://%s/%s" % (site['scheme'], site['host'],
                                        site['path'].rsplit('/', 1)[0])

        self.config_name = getattr(conf, 'filename', None)

        try:
            if conf[CONF_SEC][PATH_TO_ISSUEDB]:
                path = find_config_file(conf[CONF_SEC][PATH_TO_ISSUEDB])
                self.issuedb = IssuesDB(path)
        except Exception as ex:
            logger.warn("Failed to load issue db %s: %s",
                        conf[CONF_SEC].get(PATH_TO_ISSUEDB), ex)

    def _should_be_skipped(self, test):
        if not getattr(test, TRAC_ID, False):
            ids = []
        else:
            ids = getattr(test, TRAC_ID).replace(',', ' ').split()

        if self.issuedb:
            ids += self.issuedb.lookup(test.test_name, self.config_name)

        for id_ in ids:
            ticket = self._ticket(id_)
            try:
                if self.version not in Version(ticket['version']):
                    continue
            except (TypeError, ValueError):
                pass  # Version is not applicable here
            logger.info("TRAC<%s> '%s': %s", id_, ticket['summary'],
                        ticket['status'])
            if ticket['status'].lower() != 'closed':
                raise TracSkipTest(ticket, self.site_url)

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
        except SkipTest as ex:
            st = getattr(elm, 'status', elm.TEST_STATUS_FAILED)
            if st in (elm.TEST_STATUS_FAILED, elm.TEST_STATUS_ERROR):
                logger.info("Test marked as Skipped due to: %s", ex)
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
        params['requires'] = ['art-utilities', 'art-tests-rhevm-api']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'trac_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(CONF_SEC, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec['url'] = "is_url_alive(default='%s')" % DEFAULT_URL
        section_spec[PATH_TO_ISSUEDB] = "string(default=None)"
