from rhevm_utils.base import RHEVMUtilsTestCase

from art.test_handler import exceptions
from art.test_handler.tools import tcms, bz

from datetime import datetime, timedelta
from os.path import relpath
from sys import modules

from utilities.rhevm_tools.manage_domains import ManageDomainsUtility
from utilities.rhevm_tools import errors
from utilities import sshConnection

from . import ART_CONFIG as config

NAME = 'manage-domains'
TABLE_NAME = 'vdc_options'
KEY_COLUMN = 'option_name'
VALUE_COLUMN = 'option_value'

__THIS_MODULE = modules[__name__]

directoryServices = {
    'IPA': 'FREE_IPA',
    'LDAP': 'OPEN_LDAP',
    'RHDS': 'RED_HAT_DIRECTORY_SERVER',
    'AD': 'ACTIVE_DIRECTORY'
}


def _run_ssh_command(host, password, cmd):
    ssh_session = sshConnection.SSHSession(
        hostname=host, username='root', password=password)
    rc, out, err = ssh_session.runCmd(cmd)
    if rc:
        raise exceptions.HostException("%s" % err)
    return out


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

        self.host = config['REST_CONNECTION'].get('host', None)
        self.sshPassword = config['PARAMETERS'].get('vdc_root_password', None)
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
    https://tcms.engineering.redhat.com/case/175847/?from_plan=4580
    """

    @tcms(4580, 175847)
    def test_manage_domains_add_file(self):
        """
        rhevm-manage-domains -action=add
        """
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        self.ut.autoTest()
        self.ut(action='delete', domain=self.domainName, force=None)

    @tcms(4580, 175847)
    def test_manage_domains_add_multiline_file(self):
        cmd = ['echo', '>>', self.passwordFile]
        _run_ssh_command(self.host, self.sshPassword, cmd)
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        self.ut.autoTest()
        self.ut(action='delete', domain=self.domainName, force=None)

    @tcms(4580, 175847)
    def test_manage_domains_add_relative_file(self):
        cwd = _run_ssh_command(self.host, self.sshPassword, 'pwd')
        self.passwordFile = relpath(self.passwordFile, cwd)
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        self.ut.autoTest()
        self.ut(action='delete', domain=self.domainName, force=None)

    @bz(1083033)
    @tcms(4580, 175847)
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

    @tcms(4580, 175847)
    def test_manage_domains_add_empty_file(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.emptyFile)
        assert 'cannot be empty' in self.ut.out
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest, rc=22)

        # -interactive cannot be tested now since manage-domains cannot read
        # from a pipe


class ManageDomainsTestCaseEdit(ManageDomainsTestCaseBase):
    """
    https://tcms.engineering.redhat.com/case/175882/?from_plan=4580
    """

    def setUp(self):
        super(ManageDomainsTestCaseEdit, self).setUp()
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, force=None)
        super(ManageDomainsTestCaseEdit, self).tearDown()

    @bz(1083033)
    @bz(1055417)
    @tcms(4580, 175882)
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
    https://tcms.engineering.redhat.com/case/107969/?from_plan=4580
    """

    def setUp(self):
        super(ManageDomainsTestCaseList, self).setUp()
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, force=None)
        super(ManageDomainsTestCaseList, self).tearDown()

    @tcms(4580, 107969)
    def test_manage_domains_list(self):
        """
        rhevm-manage-domains -action=list
        """
        self.ut(action='list')
        self.ut.autoTest()


class ManageDomainsTestCaseValidate(ManageDomainsTestCaseBase):
    """
    https://tcms.engineering.redhat.com/case/334273/?from_plan=4580
    """

    def setUp(self):
        super(ManageDomainsTestCaseValidate, self).setUp()
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, force=None)
        super(ManageDomainsTestCaseValidate, self).tearDown()

    @bz(1083033)
    @tcms(4580, 334273)
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
    https://tcms.engineering.redhat.com/case/108231/?from_plan=4580
    """

    def setUp(self):
        super(ManageDomainsTestCaseDelete, self).setUp()
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)

    @tcms(4580, 108231)
    def test_manage_domains_delete(self):
        """
        rhevm-manage-domains -action=delete
        """
        self.ut(action='delete', domain=self.domainName, force=None)
        self.ut.autoTest()


class ManageDomainsTestCaseHelp(RHEVMUtilsTestCase):
    """
    https://tcms.engineering.redhat.com/case/107969/?from_plan=4580
    """

    __test__ = True
    utility = NAME
    utility_class = ManageDomainsUtility
    _multiprocess_can_split_ = True

    @tcms(4580, 107969)
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
    https://tcms.engineering.redhat.com/case/110044/?from_plan=4580
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

    @bz(1083033)
    @tcms(4580, 110044)
    def test_time_skew(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, password_file=self.passwordFile)
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest, rc=8)


class ManageDomainsUnpriviledgedUser(ManageDomainsTestCaseBase):
    """
    https://tcms.engineering.redhat.com/case/127947/?from_plan=4580
    """

    __test__ = True
    # doesn't matter what's here, but it has to be anything in order to not to
    # get key error in SetUp
    directoryService = directoryServices.values()[0]

    @bz(1083411)
    @tcms(4580, 127947)
    def test_unpriviledged_user(self):
        cmd = ['su', 'postgres', '-c', 'rhevm-manage-domains', 'add',
               '--domain=' + self.domainName,
               '--provider=' + self.provider,
               '--user=' + self.domainUser,
               '--password-file=' + self.password_file]
        out = _run_ssh_command(self.host, self.sshPassword, cmd)
        assert 'Permission denied' in out
        assert 'Exception' not in out


class ManageDomainsUppercaseLowercase(ManageDomainsTestCaseBase):
    """
    https://tcms.engineering.redhat.com/case/107971/?from_plan=4580
    """

    def mixedCase(self, name):
        labels = name.split('.')
        for i in range(0, len(labels), 2):
            labels[i] = labels[i].upper()
        return ".".join(labels)

    @bz(1078147)
    @tcms(4580, 107971)
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
    https://tcms.engineering.redhat.com/case/109297/?from_plan=4580
    """

    __test__ = True
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

    @tcms(4580, 109297)
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
    https://tcms.engineering.redhat.com/case/107972/?from_plan=4580
    """

    @bz(1083033)
    @tcms(4580, 107972)
    def test_manage_domains_nonexistent_user(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user='chucknorris', password_file=self.passwordFile)
        assert 'Authentication Failed' in self.ut.out
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest)

    @tcms(4580, 107972)
    def test_manage_domains_nonexistent_domain(self):
        self.ut(action='add', domain='~!@#$%^*_+=-[]',
                provider=self.provider, user=self.domainUser,
                password_file=self.passwordFile)
        assert 'No LDAP servers can be obtained' in self.ut.out

    @tcms(4580, 107972)
    def test_manage_domains_nonexistent_provider(self):
        self.ut(action='add', domain=self.domainName,
                provider='~!@#$%^*_+=-[]', user=self.domainUser,
                password_file=self.passwordFile)
        assert 'Invalid provider, valid providers are' in self.ut.out


class ManageDomainsBug1037894(ManageDomainsTestCaseBase):
    __test__ = True
    directoryService = 'ACTIVE_DIRECTORY_TLV'

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

# generate test classes dynamically
for action, parent in tests.iteritems():
    for service, confSection in directoryServices.iteritems():
        name = 'ManageDomainsTestCase%s%s' % (action, service)
        attributes = {
            '__test__': True,
            'directoryService': confSection
        }
        newClass = type(name, (parent,), attributes)
        setattr(__THIS_MODULE, name, newClass)
