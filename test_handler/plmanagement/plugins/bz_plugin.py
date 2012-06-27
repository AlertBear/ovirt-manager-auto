
from test_handler.plmanagement import Component, implements
from test_handler.plmanagement.interfaces.application import IConfigurable, IApplicationListener
from test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler, ITestGroupHandler, ITestSkipper, SkipTest

BZ_OPTION = 'bugzilla'
DEFAULT_URL = 'https://bugzilla.redhat.com/xmlrpc.cgi'

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
        if not params.bz_enabled:
            # added option to enable tcms from config_file
            return
        import bugzilla
        self.user = params.bz_user or conf[BZ_OPTION]['user']
        self.passwd = params.bz_pass or conf[BZ_OPTION]['password']
        self.bugzilla = bugzilla.RHBugzilla(url=params.bz_host\
                or conf[BZ_OPTION].get('url', DEFAULT_URL))
        self.bugzilla.login(self.user, self.passwd)

    def is_state(self, bz_id, *states):
        """
        Returns True/False accordinally
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
        return self.bugzilla.query(bug_id=bz_id)

    def on_application_exit(self):
        if self.bugzilla is not None:
            self.bugzilla.logout()

    def on_application_start(self):
        pass

    def on_plugins_loaded(self):
        pass

    def _should_be_skipped(self, test):
        if hasattr(test, 'bz'):
            if not self.is_state(test.bz, 'CLOSED'):
                raise SkipTest("BZ not closed: %s" % test.bz)

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
        return params.bz_enabled

