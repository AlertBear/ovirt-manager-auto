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

        self.host = config['PARAMETERS'].as_list('vds')[0]
        self.sshPassword = config['PARAMETERS'].as_list('vds_password')[0]
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
            self.ut(action='delete', domain=self.domainName, forceDelete=None)

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
                user=self.domainUser, passwordFile=self.passwordFile)
        self.ut.autoTest()
        self.ut(action='delete', domain=self.domainName, forceDelete=None)

    @tcms(4580, 175847)
    def test_manage_domains_add_multiline_file(self):
        cmd = ['echo', '>>', self.passwordFile]
        _run_ssh_command(self.host, self.sshPassword, cmd)
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile)
        self.ut.autoTest()
        self.ut(action='delete', domain=self.domainName, forceDelete=None)

    @tcms(4580, 175847)
    def test_manage_domains_add_relative_file(self):
        cwd = _run_ssh_command(self.host, self.sshPassword, 'pwd')
        self.passwordFile = relpath(self.passwordFile, cwd)
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile)
        self.ut.autoTest()
        self.ut(action='delete', domain=self.domainName, forceDelete=None)

    @tcms(4580, 175847)
    def test_manage_domains_add_missing_options(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, rc=3)
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest)
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                rc=3)
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest)
        self.ut(action='add', domain=self.domainName, rc=3)
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest)
        self.ut(action='add', rc=3)

    @tcms(4580, 175847)
    def test_manage_domains_add_empty_file(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.emptyFile, rc=8)
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest)

        # -interactive cannot be tested now since manage-domains cannot read
        # from a pipe


class ManageDomainsTestCaseEdit(ManageDomainsTestCaseBase):
    """
    https://tcms.engineering.redhat.com/case/175882/?from_plan=4580
    """

    def setUp(self):
        super(ManageDomainsTestCaseEdit, self).setUp()
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, forceDelete=None)
        super(ManageDomainsTestCaseEdit, self).tearDown()

    @bz(1055417)
    @tcms(4580, 175882)
    def test_manage_domains_edit(self):
        """
        rhevm-manage-domains -action=edit
        """
        self.ut(action='edit', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile)
        self.ut.autoTest()

        self.ut(action='edit', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile,
                addPermissions=None)
        self.ut.autoTest()

        self.ut(action='edit', domain=self.domainName)
        self.ut.autoTest()

        # relative password file
        cwd = _run_ssh_command(self.host, self.sshPassword, 'pwd')
        self.passwordFile = relpath(self.passwordFile, cwd)
        self.ut(action='edit', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile)
        self.ut.autoTest()

        # empty password file
        self.ut(action='edit', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.emptyFile, rc=8)
        self.ut.autoTest()


class ManageDomainsTestCaseList(ManageDomainsTestCaseBase):
    """
    https://tcms.engineering.redhat.com/case/107969/?from_plan=4580
    """

    def setUp(self):
        super(ManageDomainsTestCaseList, self).setUp()
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, forceDelete=None)
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
                user=self.domainUser, passwordFile=self.passwordFile)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, forceDelete=None)
        super(ManageDomainsTestCaseValidate, self).tearDown()

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
                user=self.domainUser, passwordFile=self.passwordFile)

    @tcms(4580, 108231)
    def test_manage_domains_delete(self):
        """
        rhevm-manage-domains -action=delete
        """
        self.ut(action='delete', domain=self.domainName, forceDelete=None)
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
        self.ut(rc=1)
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

    @tcms(4580, 110044)
    def test_time_skew(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile, rc=8)
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest)


class ManageDomainsUnpriviledgedUser(ManageDomainsTestCaseBase):
    """
    https://tcms.engineering.redhat.com/case/127947/?from_plan=4580
    """

    __test__ = True
    # doesn't matter what's here, but it has to be anything in order to not to
    # get key error in SetUp
    directoryService = directoryServices.values()[0]

    @tcms(4580, 127947)
    def test_unpriviledged_user(self):
        cmd = ['su', 'postgres', '-c', 'rhevm-manage-domains']
        self.assertRaises(exceptions.HostException, _run_ssh_command,
                          self.host, self.sshPassword, cmd)


class ManageDomainsUppercaseLowercase(ManageDomainsTestCaseBase):
    """
    https://tcms.engineering.redhat.com/case/107971/?from_plan=4580
    """

    def mixedCase(self, name):
        labels = name.split('.')
        for i in range(0, len(labels), 2):
            labels[i] = labels[i].upper()
        return ".".join(labels)

    @tcms(4580, 107971)
    def test_upercase_lowercase(self):
        self.ut(action='add', domain=self.domainName.upper(),
                provider=self.provider, user=self.domainUser,
                passwordFile=self.passwordFile)
        self.ut.kwargs['domain'] = self.domainName
        self.ut.autoTest()

        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile, rc=5)
        assert 'already exists' in self.ut.out

        self.ut(action='edit', domain=self.mixedCase(self.domainName),
                provider=self.provider, user=self.domainUser,
                passwordFile=self.passwordFile)
        self.ut.kwargs['domain'] = self.domainName
        self.ut.autoTest()

        self.ut(action='delete', domain=self.domainName, forceDelete=None)
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
                    user=user, passwordFile=self.passwordFiles['domainName'])
            self.ut.autoTest()

        self.ut(action='list')
        self.ut.autoTest()

        for (domainName, user, provider) in self.directoryServices:
            self.ut(action='edit', domain=domainName, provider=provider,
                    user=user, passwordFile=self.passwordFiles['domainName'])
            self.ut.autoTest()

        self.ut(action='validate', report=None)
        self.ut.autoTest()

        for (domainName, _, _) in self.directoryServices:
            self.ut(action='delete', domain=domainName, forceDelete=None)
            self.ut.autoTest()


class ManageDomainsTestCaseNegativeScenarios(ManageDomainsTestCaseBase):
    """
    https://tcms.engineering.redhat.com/case/107972/?from_plan=4580
    """

    @tcms(4580, 107972)
    def test_manage_domains_nonexistent_user(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user='chucknorris', passwordFile=self.passwordFile, rc=8)
        assert 'Authentication Failed' in self.ut.out
        self.assertRaises(errors.MissingDmainError, self.ut.autoTest)

    @tcms(4580, 107972)
    def test_manage_domains_nonexistent_domain(self):
        self.ut(action='add', domain='~!@#$%^*_+=-[]',
                provider=self.provider, user=self.domainUser,
                passwordFile=self.passwordFile, rc=23)
        assert 'No LDAP servers can be obtained' in self.ut.out

    @tcms(4580, 107972)
    def test_manage_domains_nonexistent_provider(self):
        self.ut(action='add', domain=self.domainName,
                provider='~!@#$%^*_+=-[]', user=self.domainUser,
                passwordFile=self.passwordFile, rc=14)
        assert 'Supported provider types are' in self.ut.out


class ManageDomainsBug1037894(ManageDomainsTestCaseBase):
    __test__ = True
    directoryService = 'ACTIVE_DIRECTORY_TLV'

    def setUp(self):
        super(ManageDomainsBug1037894, self).setUp()
        self.server1 = config[self.directoryService].get('server1', None)
        self.server2 = config[self.directoryService].get('server2', None)

    def tearDown(self):
        self.ut(action='delete', domain=self.domainName, forceDelete=None)
        super(ManageDomainsBug1037894, self).tearDown()

    def test_manage_domains_edit(self):
        self.ut(action='add', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile,
                ldapServers=self.server1 + ',' + self.server2)
        query = 'SELECT %s FROM %s WHERE %s = \'LdapServers\''
        servers = self.ut.setup.psql(query, VALUE_COLUMN, TABLE_NAME,
                                     KEY_COLUMN)

        assert self.server1 in servers[0][0]
        assert self.server2 in servers[0][0]

        self.ut(action='edit', domain=self.domainName, provider=self.provider,
                user=self.domainUser, passwordFile=self.passwordFile,
                ldapServers=self.server1)
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
