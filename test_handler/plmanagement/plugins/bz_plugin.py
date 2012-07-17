
import re
import copy
from test_handler.plmanagement import Component, implements, get_logger
from test_handler.plmanagement.interfaces.application import IConfigurable, IApplicationListener
from test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler, ITestGroupHandler, ITestSkipper, SkipTest

from utilities.machine import Machine, LINUX

logger = get_logger('bugzilla')

RUN = 'RUN'
REST = 'REST_CONNECTION'
PARAMETERS = 'PARAMETERS'
BZ_OPTION = 'BUGZILLA'
ENGINE = 'engine'

DEFAULT_URL = 'https://bugzilla.redhat.com/xmlrpc.cgi'
DEFAULT_USER = 'bugzilla-qe-tlv@redhat.com'
DEFAULT_PASSWD = '2kNeViSUVO'


RHEVM_RPM = 'rhevm'
OVIRT_RPM = 'ovirt-engine'

INFO_TAGS = ('version', 'build_id', 'bug_status', 'product', 'short_desc', \
        'component')

CLI = 'cli'
SDK = 'sdk'


def expect_list(bug, item_name):
    item = copy.copy(getattr(bug, item_name))
    if not isinstance(item, (list, tuple, set)):
        item = [item]
    return item


class BugzillaPluginError(Exception):
    pass


class BugNotFound(BugzillaPluginError):
    pass


class FetchVersionError(BugzillaPluginError):
    pass


class Version(object):
    def __init__(self, ver):
        self.ver = [int(x) for x in ver.split('.')]

    def __cmp__(self, ver):
        for a, b in zip(self.ver, ver.ver):
            d = a - b
            if d != 0:
                return d
        return len(self.ver) - len(ver.ver)

    def __str__(self):
        return '.'.join([str(x) for x in self.ver])

    def __contains__(self, ver):
        for a, b in zip(self.ver, ver.ver):
            d = a - b
            if d != 0:
                return False
        return True


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
        self.cache = {}

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-bz', action='store_true', \
                dest='bz_enabled', help="eniable plugin")
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
        self.comp = conf[RUN][ENGINE].lower()


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
        bz_id = str(bz_id)
        if bz_id not in self.cache:
            q = {'bug_id': bz_id}
            bug = self.bugzilla.query(q)
            if not bug:
                raise BugNotFound(bz_id)
            bug = bug[0]
            self.cache[bz_id] = bug
        else:
            bug = self.cache[bz_id]
        msg = "BUG<%s> info: %s" % (bz_id, dict((x, getattr(bug, x)) for x in \
                INFO_TAGS if hasattr(bug, x)))
        logger.info(msg)
        return bug

    def on_application_exit(self):
        if self.bugzilla is not None:
            self.bugzilla.logout()

    def on_application_start(self):
        pass

    def on_plugins_loaded(self):
        pass

    def __check_version(self, bug):
        """Skip?"""
        if self.version is None:
            from rhevm_api.tests_lib.general import getSystemVersion
            self.version = Version("%d.%d" % getSystemVersion())
        if getattr(bug, 'version', None):
            version = expect_list(bug, 'version')
            version = [x for x in version if x != 'unspecified']
            for v in version:
                v = Version(v)
                if v in self.version:
                    break
            else:
                if version:
                    # this bz_id is related to different version,
                    # no reason to skip it
                    return False
        return True

    def __check_component(self, bug):
        """Skip?"""
        comp = getattr(bug, 'component', None)
        if comp:
            comp_list = expect_list(bug, 'component')
            if comp_list:
                comp = comp_list.pop()
                m = re.match('^ovirt-engine-(?P<comp>.+)$', comp, re.I)
                if m:
                    comp = m.group('comp').lower()
                    if comp == SDK and comp == self.comp:
                        return True
                    elif self.comp == CLI and comp in (SDK, CLI):
                        return True
                    elif comp not in (CLI, SDK):
                        return True
        # It is not component related to our engines
        return False

    def __is_open(self, bug):
        return bug.bug_status not in self.const_list

    def _should_be_skipped(self, test):
        if not getattr(test, 'bz', False):
            return
        for bz_id in test.bz.replace(',', ' ').split():
            try:
                bz = self.bz(bz_id)
            except Exception as ex:
                logger.error("failed to get BZ<%s> info: %s", bz_id, ex)
                continue

            if self.__check_version(bz) and \
                    self.__check_component(bz) and \
                    self.__is_open(bz):
                # this bz_id is related to same version component,
                # and also it is not closed so we should skip it
                raise SkipTest(bz)

    def should_be_test_case_skipped(self, test_case):
        pass
        #self._should_be_skipped(test_case)

    def should_be_test_group_skipped(self, test_group):
        pass
        #self._should_be_skipped(test_group)

    def pre_test_case(self, t):
        pass

    def __set_status(self, elm):
        try:
            self._should_be_skipped(elm)
        except SkipTest:
            st = getattr(elm, 'status', elm.TEST_STATUS_FAILED)
            if st == elm.TEST_STATUS_FAILED:
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
        conf_en = conf.get(BZ_OPTION, {}).get('enabled', 'false').lower() == 'true'
        return params.bz_enabled or conf_en


