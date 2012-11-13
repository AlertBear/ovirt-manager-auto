"""
---------------
Bugzilla Plugin
---------------

This plugin provides access to the Bugzilla site.
This plugin is triggered by 'bz' attribute of test case. If the provided
bug is opened the test will be marked as Skipped in case of its failure.

Test Case Configuration
-----------------------
<bz>bug_num</bz>

CLI Options
-----------
    --with-bz  Enables  the Bugzilla plugin.
    --bz-user BZ_USER  User name for Bugzilla ,
        the default is 'bugzilla-qe-tlv@redhat.com'.
    --bz-pass BZ_PASS  Password for the Bugzilla ,
            the default is 'F3x5RiBnzn'.
    --bz-host BZ_HOST  URL  address for Bugzilla ,
            the default is https://bugzilla.redhat.com/xmlrpc.cgi

Configuration File Options
--------------------------
    | **[BUGZILLA]**
    | **enabled**  true/false; equivalent to with-bz CLI option
    | **user**  Equivalent to bz-user CLI option
    | **password**  Equivalent to bz-pass CLI option
    | **url**  Equivalent to bz-host CLI option
    | **constant_list**  List of bug states which should be not skipped

Usage
-----

From XML test sheet
+++++++++++++++++++
You can add <bz> tag for each test_case or test_group with appropiate bugzilla
id. You can define more than one comma-separated ids.

From unittest suite
+++++++++++++++++++
In art.test_handler.tools module is defined bz(*bz_ids) decorator. You can
decorate your functions and pass as many ids as you need.
"""

import re
import copy
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


from utilities.machine import Machine, LINUX

logger = get_logger('bugzilla')

RUN = 'RUN'
REST = 'REST_CONNECTION'
PARAMETERS = 'PARAMETERS'
BZ_OPTION = 'BUGZILLA'
ENGINE = 'engine'
PRODUCT = 'product'

DEFAULT_URL = 'https://bugzilla.redhat.com/xmlrpc.cgi'
DEFAULT_USER = 'bugzilla-qe-tlv@redhat.com'
DEFAULT_PASSWD = 'F3x5RiBnzn'
DEFAULT_STATE = False

RHEVM_RPM = 'rhevm'
OVIRT_RPM = 'ovirt-engine'

INFO_TAGS = ('version', 'build_id', 'bug_status', 'product', 'short_desc', \
        'component')

CLI = 'cli'
SDK = 'sdk'
REST = 'rest'

RHEVM_PRODUCT = 'Red Hat Enterprise Virtualization Manager'
OVIRT_PRODUCT = 'oVirt'

BZ_ID = 'bz'

def bz_decorator(*ids):
    """
    Bugzilla decorator
    """
    def decorator(func):
        setattr(func, BZ_ID, ','.join([str(i) for i in ids]))
        return func
    return decorator


def expect_list(bug, item_name, default=None):
    item = copy.copy(getattr(bug, item_name, default))
    if not isinstance(item, (list, tuple, set)):
        item = [item]
    return item


def transform_ovirt_comp(comp):
    m = re.match('^ovirt-engine-(?P<comp>.+)$', comp, re.I)
    m = m.group('comp').lower()
    if m == 'restapi':
        m = REST
    return m


class BugzillaPluginError(PluginError):
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
    implements(IConfigurable, IApplicationListener, ITestCaseHandler,
               ITestGroupHandler, ITestSkipper, IConfigValidation, IPackaging)

    name = "Bugzilla"
    enabled = True
    depends_on = []

    def __init__(self):
        super(Bugzilla, self).__init__()
        self.bugzilla = None
        self.version = None
        self.build_id = None  # where should I get it
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
        bz_cfg = conf.get(BZ_OPTION)
        import bugzilla
        self.user = params.bz_user or bz_cfg.get('user')
        self.passwd = params.bz_pass or bz_cfg.get('password')
        self.bugzilla = bugzilla.RHBugzilla(url=params.bz_host\
                or bz_cfg.get('url'))
        self.bugzilla.login(self.user, self.passwd)

        self.const_list = bz_cfg.get('constant_list', "Closed, Verified")
        self.const_list = set(self.const_list.upper().replace(',', ' ').\
                              split())

        #self.machine = Machine(conf[PARAMETERS]['vdc'], 'root', \
        #        conf[PARAMETERS]['vdc_root_password']).util(LINUX)

        self.build_id = None  # where should I get it
        self.comp = conf[RUN][ENGINE].lower()
        self.product = bz_cfg[PRODUCT]
        self.__register_functions()

    def __register_functions(self):
        from art.test_handler import tools
        setattr(tools, BZ_ID, bz_decorator)

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
            from art.rhevm_api.tests_lib.low_level.general import getSystemVersion
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

    def __deal_with_comp_and_version(self, bug):
        comp = expect_list(bug, 'component', '')
        if comp and comp[0]:
            comp = comp.pop()
        else:
            comp = ''
        if 'ovirt-engine' in comp:
            comp = transform_ovirt_comp(comp)
            if comp in (SDK, CLI) and self.comp == REST:
                return False
            if comp == SDK and self.comp in (SDK, CLI):
                return self.__check_version(bug)
            if comp == CLI and self.comp == comp:
                return self.__check_version(bug)
            if comp == CLI and self.comp in (SDK, REST):
                return False
            return self.__check_version(bug)
        # different component, why not to skip it
        return True

    def __is_open(self, bug):
        return bug.bug_status not in self.const_list


    def __is_related_product(self, bug):
        product = getattr(bug, 'product', '')
        # there could be bug which is not related to RHEVM or oVirt
        if product in (RHEVM_PRODUCT, OVIRT_PRODUCT):
            # now it is sure that bug is related directly to up/down stream
            if product != self.product:
                msg = "BZ<%s> is related to different product: '%s' != '%s'"
                logger.warn(msg, bug.id, self.product, product)
                return False
        return True



    def _should_be_skipped(self, test):
        if not getattr(test, 'bz', False):
            return
        for bz_id in test.bz.replace(',', ' ').split():
            try:
                bz = self.bz(bz_id)
            except Exception as ex:
                logger.error("failed to get BZ<%s> info: %s", bz_id, ex)
                continue

            if not self.__is_related_product(bz):
                continue

            if self.__is_open(bz) and self.__deal_with_comp_and_version(bz):
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
            if st in (elm.TEST_STATUS_FAILED, elm.TEST_STATUS_ERROR):
                # NOTE: many test_cases running with sdk_engine ends with
                # ERROR status instead of FAIL so it is needed to be able skip
                # also these test_cases. I am not happy with that because
                # status ERROR is dedicated for different purpose, but current
                # design is not able to handle in better way.
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
        conf_en = conf[BZ_OPTION].as_bool('enabled')
        return params.bz_enabled or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower()
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'Bugzilla plugin for ART'
        params['long_description'] = 'Plugin for ART. '\
                                'Provides connection to Bugzilla DB. '\
                                'Tests could be skipped according to BZ state.'
        params['requires'] = ['python-bugzilla', 'art-utilities']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.bz_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.get(BZ_OPTION, {})
        section_spec['user'] = "string(default='%s')" % DEFAULT_USER
        section_spec['password'] = "string(default='%s')" % DEFAULT_PASSWD
        section_spec['enabled'] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec['url'] = "is_url_alive(default='%s')" % DEFAULT_URL
        section_spec[PRODUCT] = "option('%s', '%s', default='%s')" % \
                (RHEVM_PRODUCT, OVIRT_PRODUCT, RHEVM_PRODUCT)
        spec[BZ_OPTION] = section_spec
