"""
-----------
Jira Plugin
-----------

This plugin provides access to the Jira tracking site.
This plugin is triggered by 'jira' attribute of test_case.
It skips test_case when provided jira_ticket_id isn't closed.

CLI Options
-----------
    --with-jira  Enable plugin

Configuration File Options
--------------------------
    | **[JIRA]**
    | **enabled** - True/False, enables plugin
    | **url** - trac site URL,
                'http(s)://[user[:pass]@]host[:port]/path/to/rpc/entry'
    |        *default*: https://projects.engineering.redhat.com
    | **user** - username
    | **password** - password
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

from art.test_handler.settings import opts
from art.test_handler.exceptions import SkipTest
from art.test_handler.plmanagement import (
    Component, implements, get_logger, PluginError,
)
from art.test_handler.plmanagement.interfaces.application import (
    IConfigurable,
)
from art.test_handler.plmanagement.interfaces.tests_listener import (
    ITestSkipper,
)
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import (
    IConfigValidation,
)
from art.test_handler import find_config_file
from utilities.issuesdb import IssuesDB
from jira.client import JIRA

logger = get_logger('jira')

JIRA_ID = 'jira'
CONF_SEC = 'JIRA'
DEFAULT_STATE = False
DEFAULT_URL = 'https://projects.engineering.redhat.com'
DEFAULT_USER = 'rhevm-qe-user'
DEFAULT_PASSWORD = 'rhevm'
ENABLED = 'enabled'
PATH_TO_ISSUEDB = 'path_to_issuedb'
JIRA_URL = 'url'
JIRA_USER = 'user'
JIRA_PASSWORD = 'password'
COMPONENT_MAP = {
    'oVirt-API-REST': 'rest',
    'oVirt-API-PythonSDK': 'sdk',
    'oVirt-API-JavaSDK': 'java',
    'oVirt-API-CLI': 'cli',
    'oVirt-Storage-iSCSI': 'iscsi',
    'oVirt-Storage-Glusterfs': 'glusterfs',
    'oVirt-Storage-NFS': 'nfs',
}


def jira_decorator(ids_dict):
    """
    Decorator to use for mark test elements as skipped because of jira issue.
    """
    def jira_wrap(func):
        setattr(func, JIRA_ID, ids_dict)
        return func
    return jira_wrap


def parse_version(version):
    return tuple("{0:0>8}".format(a) for a in version.split('.'))


class JiraSkipTest(SkipTest):
    def __init__(self, ticket, site):
        super(JiraSkipTest, self).__init__()
        self.ticket = ticket
        self.site = site

    def __str__(self):
        msg = "Known issue %s/browse/%s" % (self.site, self.ticket)
        return msg


class JiraPluginError(PluginError):
    pass


class Jira(Component):
    """
    Plugin provides access to Jira site.
    """
    implements(
        IConfigurable,
        IConfigValidation,
        ITestSkipper,
        IPackaging,
    )
    name = "Jira"

    def __init__(self):
        super(Jira, self).__init__()
        self._cache = {}
        self.config_name = None
        self.issuedb = None
        self.site = None
        self.user = None
        self.password = None
        self.version = None
        self.__register_functions()

    def __register_functions(self):
        from art.test_handler import tools
        setattr(tools, JIRA_ID, jira_decorator)

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-jira', action='store_true',
                           dest='jira_enabled', help="enable plugin")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        from art.test_handler.test_runner import TestGroup
        TestGroup.add_elm_attribute('TEST_JIRA_ID', JIRA_ID)

        self.site = conf[CONF_SEC]['url']
        self.user = conf[CONF_SEC]['user']
        self.password = conf[CONF_SEC]['password']

        self.config_name = getattr(conf, 'filename', None)

        try:
            if conf[CONF_SEC][PATH_TO_ISSUEDB]:
                path = find_config_file(conf[CONF_SEC][PATH_TO_ISSUEDB])
                self.issuedb = IssuesDB(path)
        except Exception as ex:
            logger.warn(
                "Failed to load issue db %s: %s",
                conf[CONF_SEC].get(PATH_TO_ISSUEDB),
                ex,
            )

        self._set_version(conf['PARAMETERS']['compatibility_version'])

    def _set_version(self, version):
        self.version = parse_version(version)

    def _should_be_skipped(self, test):
        ids = test.attrs.get(JIRA_ID, dict())
        if not isinstance(ids, dict):
            ids = dict()

        if self.issuedb and test.test_name:
            ids.update(
                dict(id_, None)
                for id_ in self.issuedb.lookup(
                    test.test_name, self.config_name,
                )
            )

        for id_, params in ids.iteritems():
            if params is None:
                params = dict()
            ticket = self._ticket(id_)
            resolved = ticket.fields.resolution is not None
            logger.info(
                "JIRA<%s> '%s': resolved(%s)", id_, ticket.fields.summary,
                resolved,
            )
            engine_api = opts['engine']
            storage_type = opts['storage_type']
            if not resolved:
                # Ticket is open
                affects_api_or_storage = (
                    self._is_affected(engine_api, ticket) or
                    self._is_affected(storage_type, ticket)
                )
                if (
                    self._affects_version(ticket) and
                    affects_api_or_storage
                ):
                    # Skip when it affects version and component
                    raise JiraSkipTest(id_, self.site)
            else:
                # Ticket is closed
                if (
                    self._affects_version(ticket) and
                    not self._is_fixed_in(ticket)
                ):
                    # Interested in version only, skip in case
                    # it wasn't fixed for specific version
                    raise JiraSkipTest(id_, self.site)
                # NOTE: (lbednar) I think that there is no reason to check
                # component in this case

    def _is_affected(self, component, ticket):

        components = [
            COMPONENT_MAP[c.name]
            for c in ticket.fields.components if c.name in COMPONENT_MAP
        ]

        if not components:
            logger.info("  No component specified in ticket, considering all.")
            return True
        if component in components and component is not None:
            logger.info("It affects specific component: %s", component)
            return True

        logger.info("%s is not specified in ticket", component)

        return False

    def _affects_version(self, ticket):
        affects = [v.name for v in ticket.fields.versions]
        if not affects:
            logger.warn("  No version specified in ticket, considering all.")
            return True
        for version in affects:
            version = parse_version(version.split('-')[-1])
            if version == self.version:
                logger.info("  Affected version was matched: %s", version)
                return True
        logger.info(
            "  It doesn't affect your specific version: %s not in %s",
            self.version, affects,
        )
        return False

    def _is_fixed_in(self, ticket):
        fixed_in = [v.name for v in ticket.fields.fixVersions]
        if not fixed_in:
            logger.warn("  There is no fixed version specified in ticket!")
            return False
        versions = sorted(parse_version(v.split('-')[-1]) for v in fixed_in)
        if self.version >= versions[-1]:
            logger.info(
                "  Issue was fixed for current/higher version: %s",
                versions[-1],
            )
            return True
        logger.info(
            "  Issue wasn't fixed for current version (%s), "
            "it was fixed for %s", self.version, fixed_in,
        )
        return False

    def _ticket(self, id_):
        issue = self._cache.get(id_, None)
        if issue:
            return issue

        jira_instance = JIRA(
            options={
                'server': self.site,
                'verify': False,
            },
            basic_auth=(self.user, self.password),
        )

        issue = jira_instance.issue(id_)
        self._cache[id_] = issue
        return issue

    def __set_status(self, elm):
        try:
            self._should_be_skipped(elm)
        except SkipTest as ex:
            st = getattr(elm, 'status', elm.TEST_STATUS_FAILED)
            if st in (elm.TEST_STATUS_FAILED, elm.TEST_STATUS_ERROR):
                logger.info("Test marked as Skipped due to: %s", ex)
                elm.status = elm.TEST_STATUS_SKIPPED
            raise

    def should_be_test_case_skipped(self, t):
        self.__set_status(t)

    def should_be_test_group_skipped(self, g):
        self.__set_status(g)

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf[CONF_SEC].as_bool(ENABLED)
        return params.jira_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower()
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Jira plugin for ART'
        params['long_description'] = cls.__doc__
        params['requires'] = ['python-jira']
        params['py_modules'] = [
            'art.test_handler.plmanagement.plugins.jira_plugin',
        ]

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(CONF_SEC, {})
        section_spec[ENABLED] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec[JIRA_URL] = "string(default='%s')" % DEFAULT_URL
        section_spec[JIRA_USER] = "string(default='%s')" % DEFAULT_USER
        section_spec[JIRA_PASSWORD] = "string(default='%s')" % DEFAULT_PASSWORD
        section_spec[PATH_TO_ISSUEDB] = "string(default=None)"
