
import re
import logging
from test_handler.plmanagement import logger as root_logger
from test_handler.plmanagement import Component, implements
from test_handler.plmanagement.interfaces.application import IConfigurable, IApplicationListener
from test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler, ITestGroupHandler, ITestSkipper, SkipTest

from utilities.machine import Machine, LINUX

logger = logging.getLogger(root_logger.name+'.bugzilla')

REST = 'REST_CONNECTION'
PARAMETERS = 'PARAMETERS'
BZ_OPTION = 'BUGZILLA'
DEFAULT_URL = 'https://bugzilla.redhat.com/xmlrpc.cgi'
DEFAULT_USER = 'bugzilla-qe-tlv@redhat.com'
DEFAULT_PASSWD = '2kNeViSUVO'


RHEVM_RPM = 'rhevm'
OVIRT_RPM = 'ovirt-engine'


class BugzillaPluginError(Exception):
    pass


class BugNotFound(BugzillaPluginError):
    pass


class FetchVersionError(BugzillaPluginError):
    pass


class Bugzilla(Component):
    """
    Plugin provides access to bugzilla site.
    """
    implements(IConfigurable, IApplicationListener, ITestCaseHandler, ITestGroupHandler, ITestSkipper)
    name = "Bugzilla"
    enabled = True
    depends_on = []

    def __init__(self):
        super(Bugzilla, self).__init__()
        self.bugzilla = None
        self.version = None
        self.build_id = None # where should I get it

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-bz', action='store_true', \
                dest='bz_enabled', help="enable plugin")
        group.add_argument('--bz-user', action="store", dest='bz_user', \
                help="username for bugzilla")
        group.add_argument('--bz-pass', action="store", dest='bz_pass', \
                help="password for bugzilla")
        group.add_argument('--bz-host', action="store", dest='bz_host', \
                help="url address for bugzilla")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        bz_cfg = conf.get(BZ_OPTION, {})
        import bugzilla
        self.user = params.bz_user or bz_cfg.get('user', DEFAULT_USER)
        self.passwd = params.bz_pass or bz_cfg.get('password', DEFAULT_PASSWD)
        self.bugzilla = bugzilla.RHBugzilla(url=params.bz_host\
                or bz_cfg.get('url', DEFAULT_URL))
        self.bugzilla.login(self.user, self.passwd)

        self.const_list = bz_cfg.get('constant_list', "Closed,ON_QA, Verified")
        self.const_list = set(self.const_list.upper().replace(',', ' ').split())

        #self.machine = Machine(conf[PARAMETERS]['vdc'], 'root', \
        #        conf[PARAMETERS]['vdc_root_password']).util(LINUX)

        self.build_id = None # where should I get it


    def is_state(self, bz_id, *states):
        """
        Returns True/False accordingly
        Parameters:
         * bz_id - bugzilla ID
         * staties - expected states
        """
        bug = self.bz(bz_id)
        return bug.bug_status in states

    def bz(self, bz_id):
        """
        Returns BZ record
        """
        q = {'bug_id': bz_id}
        bug = self.bugzilla.query(q)
        if not bug:
            raise BugNotFound(bz_id)
        bug = bug[0]
        msg = "BUG<%s> info: %s" % (bz_id, dict((x, getattr(bug, x)) for x in \
                ('version', 'build_id', 'bug_status', 'product', 'short_desc')))
        logger.info(msg)
        return bug

    def on_application_exit(self):
        if self.bugzilla is not None:
            self.bugzilla.logout()

    def on_application_start(self):
        pass

    def on_plugins_loaded(self):
        pass

    def _should_be_skipped(self, test):
        if not getattr(test, 'bz', False):
            return
        for bz_id in test.bz.replace(',', ' ').split():
            try:
                bz = self.bz(bz_id)
            except Exception as ex:
                logger.error("failed to get BZ<%s> info: %s", bz_id, ex)
                continue

            if self.version is None:
                from rhevm_api.tests_lib.general import getSystemVersion
                self.version = "%d.%d" % getSystemVersion()
#                continue # probably the newest version
            if self.version not in bz.version:
                # this bz_id is related to different version,
                # no reason to skip it
                continue
# FIXME: consider build_id as well
#            if bz.build_id and bz.build_id != self.build_id:
#                # this bz_id is related to different build,
#                # no reason to skip it
#                continue
            if bz.bug_status not in self.const_list:
                # this bz_id is related to same version and build,
                # or build is now unknown, and also it is not closed,
                # so we can skip it
                raise SkipTest(bz)

    def should_be_test_case_skipped(self, test_case):
        self._should_be_skipped(test_case)

    def should_be_test_group_skipped(self, test_group):
        self._should_be_skipped(test_group)

    def pre_test_case(self, t):
        pass

    def post_test_case(self, t):
        pass

    def pre_test_group(self, g):
        pass

    def post_test_group(self, g):
        pass

    def test_group_skipped(self, g):
        pass

    def test_case_skipped(self, t):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(BZ_OPTION, {}).get('enabled', 'false').lower() == 'true'
        return params.bz_enabled or conf_en


