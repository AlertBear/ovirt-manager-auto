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
    | **constant_list**  String of bug states which should not be skipped
    | **path_to_issuedb** Path to file where are you can map bugs to cases

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
import copy
from functools import wraps

from art.test_handler.exceptions import SkipTest
from art.test_handler.plmanagement import (
    Component,
    implements,
    get_logger,
    PluginError
)
from art.test_handler.plmanagement.interfaces.application import (
    IConfigurable,
    IApplicationListener
)

from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import (
    IConfigValidation
)
from art.test_handler.plmanagement.interfaces.tests_listener import (
    ITestGroupHandler,
)
from art.test_handler.settings import initPlmanager, opts
from art.test_handler import find_config_file

from utilities.issuesdb import IssuesDB


logger = get_logger('bugzilla')

BZ_OPTION = 'BUGZILLA'
ENGINE = 'engine'
PRODUCT = 'product'
PATH_TO_ISSUEDB = 'path_to_issuedb'

DEFAULT_URL = 'https://bugzilla.redhat.com/xmlrpc.cgi'
DEFAULT_USER = 'bugzilla-qe-tlv@redhat.com'
DEFAULT_PASSWD = 'F3x5RiBnzn'
DEFAULT_STATE = False

RHEVM_RPM = 'rhevm'
OVIRT_RPM = 'ovirt-engine'

INFO_TAGS = ('version',
             'build_id',
             'bug_status',
             'product',
             'short_desc',
             'component')

SKIP_FOR_RESOLUTION = [
    'NOTABUG',
    'WONTFIX',
    'DEFERRED',
    'WORKSFORME',
    'RAWHIDE',
    'UPSTREAM',
    'CANTFIX',
    'INSUFFICIENT_DATA',
    'NEXTRELEASE'
]

CLI = 'cli'
SDK = 'sdk'
REST = 'rest'
NONE_VER = '---'

RHEVM_PRODUCT = 'Red Hat Enterprise Virtualization Manager'
OVIRT_PRODUCT = 'oVirt'

BZ_ID = 'bz'

URL_RE = re.compile("^(https?://[^/]+)")


def bz(bug_dict):
    """
    Decorator function to skip test case, when we have opened bug for it.

    * parameters:
        ** bug_dict: {'bug_id': {
                        'engine': ['cli', 'java'],
                        'version': ['3.4', '3.5']
                        }
                    }
    * raises: SkipTest
    * returns: function object
    """
    def real_bz(func):

        def check_should_skip(bz_id, engine=None, version=None):
            plmanager = initPlmanager()
            BZ_PLUGIN = [pl for pl in plmanager.application_liteners
                         if pl.name == "Bugzilla"][0]
            try:
                BZ_PLUGIN.should_be_skipped(bz_id, engine, version)
            except BugzillaSkipTest:
                logger.warn("Skipping test because BZ%s for "
                            "engine %s, version %s",
                            bz_id, opts['engine'], version)
                raise

        @wraps(func)
        def skip_if_bz(*args, **kwargs):
            try:
                # backward compatible for @bz(bug_id) structure
                if not isinstance(bug_dict, dict):
                    logger.info("This bz is in old structure "
                                "- consider changing it")
                    check_should_skip(bug_dict)
                # @bz new structure
                else:
                    for bz_id, options in bug_dict.iteritems():
                        engine = options.get('engine')
                        version = options.get('version')
                        check_should_skip(bz_id, engine, version)
                return func(*args, **kwargs)
            except IndexError:
                logger.warning("Failed to get Bugzilla plugin")
        return skip_if_bz
    return real_bz


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


class BugzillaSkipTest(SkipTest):
    def __init__(self, bz_id, site):
        super(BugzillaSkipTest, self).__init__()
        self.bz = bz_id
        self.site = site

    def __str__(self):
        msg = "Known issue %s/show_bug.cgi?id=%s" % (self.site, self.bz)
        return msg


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
        return 0

    def __str__(self):
        return '.'.join([str(x) for x in self.ver])

    def __contains__(self, ver):
        return self.__cmp__(ver) >= 0


class Bugzilla(Component):
    """
    Plugin provides access to bugzilla site.
    """
    implements(
        IConfigurable,
        IApplicationListener,
        IConfigValidation,
        ITestGroupHandler,
        IPackaging,
    )

    name = "Bugzilla"
    enabled = True
    depends_on = []

    def __init__(self):
        super(Bugzilla, self).__init__()
        self.bugzilla = None
        self.version = None
        self.build_id = None  # where should I get it
        self.cache = {}
        self.issuedb = None
        self.config_name = None
        self.__register_functions()

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-bz', action='store_true',
                           dest='bz_enabled', help="eniable plugin")
        group.add_argument('--bz-user', action="store", dest='bz_user',
                           help="username for bugzilla")
        group.add_argument('--bz-pass', action="store", dest='bz_pass',
                           help="password for bugzilla")
        group.add_argument('--bz-host', action="store", dest='bz_host',
                           help="url address for bugzilla")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return
        bz_cfg = conf.get(BZ_OPTION)
        import bugzilla
        self.url = params.bz_host or bz_cfg.get('url')
        self.user = params.bz_user or bz_cfg.get('user')
        self.passwd = params.bz_pass or bz_cfg.get('password')
        self.bugzilla = bugzilla.Bugzilla44(url=self.url)
        self.bugzilla.login(self.user, self.passwd)

        self.const_list = bz_cfg.get('constant_list', "Closed,Verified")
        self.const_list = self.const_list.upper().replace(',', ' ').split()

        self.build_id = None  # where should I get it
        self.product = bz_cfg[PRODUCT]

        self.url = URL_RE.match(self.url).group(0)

        self.config_name = getattr(conf, 'filename', None)

        try:
            if bz_cfg[PATH_TO_ISSUEDB]:
                path = find_config_file(bz_cfg[PATH_TO_ISSUEDB])
                self.issuedb = IssuesDB(path)
        except Exception as ex:
            logger.warn("Failed to load issue db %s: %s",
                        bz_cfg.get(PATH_TO_ISSUEDB), ex)

        from art.test_handler.test_runner import TestGroup
        TestGroup.add_elm_attribute('TEST_BZ_ID', BZ_ID)

    def __register_functions(self):
        from art.test_handler import tools
        setattr(tools, BZ_ID, bz)

    def is_state(self, bz_id):
        """
        Returns True is the bug is in state specified in self.const_list
        by default it will return true if verified or closed
        Parameters:
         * bz_id - bugzilla ID
        """
        bug = self.bz(bz_id)
        return self.is_state_by_bug(bug)

    def is_state_by_bug(self, bug):
        """
        Returns True is the bug is in state specified in self.const_list
        by default it will return true if verified or closed
        Parameters:
         * bug - bz object
        """
        return bug.bug_status in self.const_list

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
        msg = "BUG<%s> info: %s" % (bz_id, dict((x, getattr(bug, x)) for x in
                                    INFO_TAGS if hasattr(bug, x)))
        logger.info(msg)
        return bug

    def on_application_start(self):
        pass

    def on_application_exit(self):
        if self.bugzilla is not None:
            self.bugzilla.logout()

    def on_plugins_loaded(self):
        pass

    def should_be_skipped(self, bz_id, engines=None, versions=None):
        """
        Raises BugzillaSkipTest if the bug is in non-resolved state
        (not verified or closed) and it's open for the current running engine
        and its in the specified version or was fixed in later version
        * parameters:
            ** bz_id the id of the bug
            ** engines list of relevant engines for this bug
            ** versions list of relevant versions for this bug
        * raises: BugzillaSkipTest exception if the test should get skipped
        * return: None if the test should not skip
        """
        # get bz object
        try:
            bz = self.bz(bz_id)
        except BugNotFound as ex:
            logger.error("failed to get BZ<%s> info: %s", bz_id, ex)
            return

        while bz.bug_status == 'CLOSED' and bz.resolution == 'DUPLICATE':
            try:
                bz_id = bz.dupe_of
                bz = self.bz(bz.dupe_of)
            except BugNotFound as ex:
                logger.error("failed to get duplicate BZ<%s> info: %s",
                             bz.bz_id, ex)
                return

        # check if the bz is open for the current engine
        engine_in = engines is None or opts['engine'] in engines

        if versions is None:
            from art.rhevm_api.tests_lib.low_level import general
            versions = ["%d.%d.%d.%d" % general.getSystemVersion()]

        for version in versions:
            self.version = Version(version)
            # if the bug is open & should skip for engine &
            # relevant for this version
            if (not self.is_state_by_bug(bz) and engine_in and
                    self.__check_version(bz)):
                logger.info("skipping due to in_state=%s, engine_in=%s",
                            self.is_state_by_bug(bz), engine_in)
                raise BugzillaSkipTest(bz_id, self.url)

            # if the bug is closed on current release resolution, but was fixed
            # in later version
            if bz.bug_status == 'CLOSED':
                if self.__check_fixed_at(bz) and engine_in:
                    raise BugzillaSkipTest(bz_id, self.url)

        for version in versions:
            self.version = Version(version)
            # if the bug is closed but should skip due to resolution cause
            if (bz.bug_status == 'CLOSED' and engine_in and
                    self.__check_version(bz) and
                    bz.resolution in SKIP_FOR_RESOLUTION):
                logger.info("skipping due to in_state=%s, resolution=%s",
                            self.is_state(bz_id), bz.resolution)
                raise BugzillaSkipTest(bz_id, self.url)

    def __check_version(self, bug):
        """
        Returns True if the bug is related to this version
        """
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

    def __check_fixed_at(self, bug):
        """
        Returns True if the bug was fixed at a later version,
        hence should be skipped.
        """
        if getattr(bug, "target_release", None):
            fixed_at = bug.target_release[0]
            if fixed_at == NONE_VER:
                return False

            try:
                fixed_at = Version(fixed_at)
                if fixed_at > self.version:
                    return True
            except (ValueError, TypeError):
                logger.warn("Version '%s' is not applicable", fixed_at)

        return False

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

    def pre_test_group(self, g):
        bug_dict = g.attrs.get(BZ_ID)
        if not bug_dict or not isinstance(bug_dict, dict):
            return
        for bz_id, options in bug_dict.iteritems():
            engine = options.get('engine')
            version = options.get('version')
            self.should_be_skipped(bz_id, engine, version)

    def post_test_group(self, g):
        pass

    def test_group_skipped(self, g):
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
        params['requires'] = ['python-bugzilla >= 0.8.0', 'art-utilities',
                              'art-tests-rhevm-api']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'bz_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(BZ_OPTION, {})
        section_spec['user'] = "string(default='%s')" % DEFAULT_USER
        section_spec['password'] = "string(default='%s')" % DEFAULT_PASSWD
        section_spec['enabled'] = 'boolean(default=%s)' % DEFAULT_STATE
        section_spec['url'] = "string(default='%s')" % DEFAULT_URL
        section_spec[PRODUCT] = "option('%s', '%s', default='%s')" % (
            RHEVM_PRODUCT, OVIRT_PRODUCT, RHEVM_PRODUCT)
        section_spec[PATH_TO_ISSUEDB] = "string(default=None)"
