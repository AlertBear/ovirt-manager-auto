from datetime import datetime, timedelta
from os.path import relpath
from sys import modules

from art.test_handler import exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.test_handler.settings import ART_CONFIG as config
from art.unittest_lib import attr

from utilities.rhevm_tools.manage_domains import ManageDomainsUtility
from utilities.rhevm_tools import errors
from utilities import sshConnection

from rhevm_utils.base import RHEVMUtilsTestCase
from rhevm_utils import unittest_conf

NAME = 'manage-domains'
TABLE_NAME = 'vdc_options'
KEY_COLUMN = 'option_name'
VALUE_COLUMN = 'option_value'

__THIS_MODULE = modules[__name__]

directoryServices = {
    'IPA': 'MANAGE_DOMAINS_FREE_IPA',
    'LDAP': 'MANAGE_DOMAINS_OPEN_LDAP',
    'RHDS': 'MANAGE_DOMAINS_RED_HAT_DIRECTORY_SERVER',
    'ADW2K8R2': 'MANAGE_DOMAINS_ADW2K8R2',
    'ADW2K12R2': 'MANAGE_DOMAINS_ADW2K12R2',
}


def _run_ssh_command(host, password, cmd):
    ssh_session = sshConnection.SSHSession(
        hostname=host, username='root', password=password)
    rc, out, err = ssh_session.runCmd(cmd)
    if rc:
        raise exceptions.HostException("%s" % err)
    return out


@attr(tier=3, extra_reqs={'utility': NAME})
class ManageDomainsTestCaseBase(RHEVMUtilsTestCase):
    """
    rhevm-manage-domains testcase
    """

    __test__ = False
    utility = NAME
    utility_class = ManageDomainsUtility
    _multiprocess_can_split_ = True
    directoryService = None

    def setUp(self):
        super(ManageDomainsTestCaseBase, self).setUp()
        self.domainName = config[self.directoryService].get('name', None)
        self.domainUser = config[self.directoryService].get('user', None)
        self.password = config[self.directoryService].get('password', None)
        self.provider = config[self.directoryService].get('provider', None)

        self.host = unittest_conf.VDC_HOST
        self.sshPassword = unittest_conf.VDC_ROOT_PASSWORD
        cmd = ['mktemp']
        self.passwordFile = _run_ssh_command(self.host, self.sshPassword,
                                             cmd).rstrip('\n')
        self.emptyFile = _run_ssh_command(self.host, self.sshPassword,
                                          cmd).rstrip('\n')
        cmd = ['echo', self.password, '>', self.passwordFile]
        _run_ssh_command(self.host, self.sshPassword, cmd)
        cmd = ['echo', '>', self.emptyFile]
        _run_ssh_command(self.host, self.sshPassword, cmd)

        if self.ut.domainExistsInDatabase(self.domainName):
            self.ut(action='delete', domain=self.domainName, force=None)

    def tearDown(self):
        cmd = ['rm', '-f', self.password, self.passwordFile]
        _run_ssh_command(self.host, self.sshPassword, cmd)
        super(ManageDomainsTestCaseBase, self).tearDown()


class ManageDomainsTestCaseAdd(ManageDomainsTestCaseBase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    @polarion("RHEVM3-9166")
    def test_manage_domains_add_file(self):
        """
        rhevm-manage-domains -action=add
        """
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        self.ut.autoTest()
        self.ut(action='delete', domain=self.domainName, force=None)

    @polarion("RHEVM3-11363")
    def test_manage_domains_add_multiline_file(self):
        cmd = ['echo', '>>', self.passwordFile]
        _run_ssh_command(self.host, self.sshPassword, cmd)
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        self.ut.autoTest()
        self.ut(action='delete', domain=self.domainName, force=None)

    @polarion("RHEVM3-11364")
    def test_manage_domains_add_relative_file(self):
        cwd = _run_ssh_command(self.host, self.sshPassword, 'pwd')
        self.passwordFile = relpath(self.passwordFile, cwd)
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        self.ut.autoTest()
        self.ut(action='delete', domain=self.domainName, force=None)

    @polarion("RHEVM3-11365")
    def test_manage_domains_add_missing_options(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser)
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest, rc=22)
        self.ut(action='add', domain=self.domainName, provider=self.provider)
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest, rc=1)
        self.ut(action='add', domain=self.domainName)
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest, rc=1)
        self.ut(action='add')
        self.ut.autoTest(rc=1)

    @polarion("RHEVM3-11366")
    def test_manage_domains_add_empty_file(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.emptyFile)
        assert 'cannot be empty' in self.ut.out
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest, rc=22)

        # -interactive cannot be tested now since manage-domains cannot read
        # from a pipe


class ManageDomainsTestCaseEdit(ManageDomainsTestCaseBase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    def setUp(self):
        super(ManageDomainsTestCaseEdit, self).setUp()
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, force=None)
        super(ManageDomainsTestCaseEdit, self).tearDown()

    @polarion("RHEVM3-9165")
    def test_manage_domains_edit(self):
        """
        rhevm-manage-domains -action=edit
        """
        self.ut(action='edit', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        self.ut.autoTest()

        self.ut(action='edit', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile,
                add_permissions=None)
        self.ut.autoTest()

        self.ut(action='edit', domain=self.domainName)
        self.ut.autoTest(rc=22)

        # relative password file
        cwd = _run_ssh_command(self.host, self.sshPassword, 'pwd')
        self.passwordFile = relpath(self.passwordFile, cwd)
        self.ut(action='edit', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        self.ut.autoTest()

        # empty password file
        self.ut(action='edit', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.emptyFile)
        self.ut.autoTest(rc=22)


class ManageDomainsTestCaseList(ManageDomainsTestCaseBase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    def setUp(self):
        super(ManageDomainsTestCaseList, self).setUp()
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, force=None)
        super(ManageDomainsTestCaseList, self).tearDown()

    @polarion("RHEVM3-9171")
    def test_manage_domains_list(self):
        """
        rhevm-manage-domains -action=list
        """
        self.ut(action='list')
        self.ut.autoTest()


class ManageDomainsTestCaseValidate(ManageDomainsTestCaseBase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    def setUp(self):
        super(ManageDomainsTestCaseValidate, self).setUp()
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, force=None)
        super(ManageDomainsTestCaseValidate, self).tearDown()

    @polarion("RHEVM3-9163")
    def test_manage_domains_validate(self):
        """
        rhevm-manage-domains -action=validate
        """
        self.ut(action='validate')
        self.ut.autoTest()

        self.ut(action='validate', report=None)
        self.ut.autoTest()


class ManageDomainsTestCaseDelete(ManageDomainsTestCaseBase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    def setUp(self):
        super(ManageDomainsTestCaseDelete, self).setUp()
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)

    @polarion("RHEVM3-9176")
    def test_manage_domains_delete(self):
        """
        rhevm-manage-domains -action=delete
        """
        self.ut(action='delete', domain=self.domainName, force=None)
        self.ut.autoTest()


class ManageDomainsTestCaseHelp(RHEVMUtilsTestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    utility = NAME
    utility_class = ManageDomainsUtility
    _multiprocess_can_split_ = True

    @polarion("RHEVM3-11367")
    def test_manage_domains_help(self):
        """
        rhevm-manage-domains
        """
        self.ut()
        self.ut.autoTest()

        self.ut(help=None)
        self.ut.autoTest()


class ManageDomainsTimeSkew(ManageDomainsTestCaseBase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    _multiprocess_can_split_ = False

    def _shiftTime(self, delta):
        cmd = ['date', '-s', str(datetime.now() + delta)]
        _run_ssh_command(self.host, self.sshPassword, cmd)

    def setUp(self):
        super(ManageDomainsTimeSkew, self).setUp()
        self._shiftTime(timedelta(minutes=15))

    def tearDown(self):
        cmd = ['date', '+%T %m/%d/%y']
        out = _run_ssh_command(self.host, self.sshPassword, cmd).rstrip()
        engineTime = datetime.strptime(out, '%X %m/%d/%y')
        if (engineTime - datetime.now()) < timedelta(minutes=5):
            # test runs on the engine
            self._shiftTime(timedelta(minutes=-15))
        else:
            self._shiftTime(timedelta())

    @polarion("RHEVM3-9168")
    def test_time_skew(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest, rc=8)


class ManageDomainsUnpriviledgedUser(ManageDomainsTestCaseBase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    # doesn't matter what's here, but it has to be anything in order to not to
    # get key error in SetUp
    directoryService = directoryServices.values()[0]

    @polarion("RHEVM3-9167")
    def test_unprivileged_user(self):
        # user needs permissions on current working directorty, that's why /tmp
        cmd = ('cd /tmp; su postgres -c "rhevm-manage-domains add --domain=%s '
               '--provider=%s --user=%s --password-file=%s"' %
               (self.domainName, self.provider, self.domainUser,
                self.passwordFile))
        out = _run_ssh_command(self.host, self.sshPassword, cmd)
        assert 'Permission denied' in out
        assert 'Exception' not in out


class ManageDomainsUppercaseLowercase(ManageDomainsTestCaseBase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    def mixedCase(self, name):
        labels = name.split('.')
        for i in range(0, len(labels), 2):
            labels[i] = labels[i].upper()
        return ".".join(labels)

    @polarion("RHEVM3-9174")
    def test_upercase_lowercase(self):
        self.ut(action='add', domain=self.domainName.upper(),
                provider=self.provider, user=self.domainUser,
                password_file=self.passwordFile)
        self.ut.kwargs['domain'] = self.domainName
        self.ut.autoTest()

        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        assert 'already exists' in self.ut.out

        self.ut(action='edit', domain=self.mixedCase(self.domainName),
                provider=self.provider, user=self.domainUser,
                password_file=self.passwordFile)
        self.ut.kwargs['domain'] = self.domainName
        self.ut.autoTest()

        self.ut(action='delete', domain=self.domainName, force=None)
        self.ut.autoTest()


class ManageDomainsMultipleProviders(RHEVMUtilsTestCase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    utility = NAME
    utility_class = ManageDomainsUtility

    def setUp(self):
        super(ManageDomainsMultipleProviders, self).setUp()
        self.directoryServices = []
        self.passwordFiles = {}
        self.host = config['PARAMETERS'].as_list('vds')[0]
        self.sshPassword = config['PARAMETERS'].as_list('vds_password')[0]
        mktemp = ['mktemp']
        for _, confSection in directoryServices.iteritems():
            domainName = config[confSection].get('name', None)
            user = config[confSection].get('user', None)
            password = config[confSection].get('password', None)
            provider = config[confSection].get('provider', None)
            self.directoryServices.append((domainName, user, provider))

            tempfile = _run_ssh_command(self.host, self.sshPassword,
                                        mktemp).rstrip('\n')
            self.passwordFiles['domainName'] = tempfile
            cmd = ['echo', password, '>', self.passwordFiles['domainName']]
            _run_ssh_command(self.host, self.sshPassword, cmd)

    def tearDown(self):
        cmd = ['rm', '-f'] + [f for f in self.passwordFiles.values()]
        _run_ssh_command(self.host, self.sshPassword, cmd)
        super(ManageDomainsMultipleProviders, self).tearDown()

    @polarion("RHEVM3-9170")
    def test_use_all_providers(self):
        for (domainName, user, provider) in self.directoryServices:
            self.ut(action='add', domain=domainName, provider=provider,
                    user=user, password_file=self.passwordFiles['domainName'])
            self.ut.autoTest()

        self.ut(action='list')
        self.ut.autoTest()

        for (domainName, user, provider) in self.directoryServices:
            self.ut(action='edit', domain=domainName, provider=provider,
                    user=user, password_file=self.passwordFiles['domainName'])
            self.ut.autoTest()

        self.ut(action='validate', report=None)
        self.ut.autoTest()

        for (domainName, _, _) in self.directoryServices:
            self.ut(action='delete', domain=domainName, force=None)
            self.ut.autoTest()


class ManageDomainsTestCaseNegativeScenarios(ManageDomainsTestCaseBase):
    """
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/
        workitem?id=RHEVM3-9162
    """

    @polarion("RHEVM3-9175")
    def test_manage_domains_nonexistent_user(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user='chucknorris', password_file=self.passwordFile)
        assert 'Authentication Failed' in self.ut.out
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest)

    @polarion("RHEVM3-11368")
    def test_manage_domains_nonexistent_domain(self):
        self.ut(action='add', domain='~!@#$%^*_+=-[]',
                provider=self.provider, user=self.domainUser,
                password_file=self.passwordFile)
        assert 'No LDAP servers can be obtained' in self.ut.out

    @polarion("RHEVM3-11369")
    def test_manage_domains_nonexistent_provider(self):
        self.ut(action='add', domain=self.domainName,
                provider='~!@#$%^*_+=-[]', user=self.domainUser,
                password_file=self.passwordFile)
        assert "Invalid argument value. Details: Invalid provider" \
               in self.ut.out


class ManageDomainsBug1037894(ManageDomainsTestCaseBase):
    directoryService = 'MANAGE_DOMAINS_ACTIVE_DIRECTORY_TLV'

    def setUp(self):
        super(ManageDomainsBug1037894, self).setUp()
        self.server1 = config[self.directoryService].get('server1', None)
        self.server2 = config[self.directoryService].get('server2', None)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, force=None)
        super(ManageDomainsBug1037894, self).tearDown()

    def test_manage_domains_edit(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile,
                ldap_servers=self.server1 + ',' + self.server2)
        query = 'SELECT %s FROM %s WHERE %s = \'LdapServers\''
        servers = self.ut.setup.psql(query, VALUE_COLUMN, TABLE_NAME,
                                     KEY_COLUMN)

        assert self.server1 in servers[0][0]
        assert self.server2 in servers[0][0]

        self.ut(action='edit', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile,
                ldap_servers=self.server1)
        servers = self.ut.setup.psql(query, VALUE_COLUMN, TABLE_NAME,
                                     KEY_COLUMN)
        assert self.server1 in servers[0][0]
        assert self.server2 not in servers[0][0]


tests = {
    'Add': ManageDomainsTestCaseAdd,
    'Edit': ManageDomainsTestCaseEdit,
    'List': ManageDomainsTestCaseList,
    'Validate': ManageDomainsTestCaseValidate,
    'Delete': ManageDomainsTestCaseDelete,
    'TimeSkew': ManageDomainsTimeSkew,
    'MixedCase': ManageDomainsUppercaseLowercase,
    'Negative': ManageDomainsTestCaseNegativeScenarios,
}

# generates test classes dynamically
for action, parent in tests.iteritems():
    for service, confSection in directoryServices.iteritems():
        name = 'ManageDomainsTestCase%s%s' % (action, service)
        attributes = {
            '__test__': True,
            'directoryService': confSection
        }
        newClass = type(name, (parent,), attributes)
        setattr(__THIS_MODULE, name, newClass)
