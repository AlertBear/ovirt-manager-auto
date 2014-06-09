from art.unittest_lib import StorageTest as TestCase
import logging

from utilities.machine import Machine

from art.test_handler.tools import tcms, bz

from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import storageconnections
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sd

import config
import helpers

LOGGER = logging.getLogger(__name__)

api = test_utils.get_api('storage_connection', 'storageconnections')
sd_api = test_utils.get_api('storage_domain', 'storagedomains')
cl_api = test_utils.get_api('cluster', 'clusters')
host_api = test_utils.get_api('host', 'hosts')


GB = 1024 ** 3


class TestCaseLocalFS(TestCase):
    __test__ = False
    sd_name = None
    conn = None
    machine = None

    def setUp(self):
        spm_host = hosts.getSPMHost(config.HOSTS)
        spm_user, spm_password = helpers.get_user_and_passwd_for_host(spm_host)
        self.machine = Machine(
            host=spm_host, user=spm_user, password=spm_password).util('linux')
        LOGGER.info("Creating local storage path")
        try:
            rc, out = self.machine.createLocalStorage(self.path)
        except Exception, ex:
            LOGGER.info(ex)
        LOGGER.info("output: %s" % out)
        assert rc

        self.host = spm_host
        self.password = spm_password
        LOGGER.info("Looking for non-master sd domains")
        status, domains = storagedomains.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME)
        LOGGER.info("Non master answer: %s %s" % (status, domains))
        assert status
        self.sd_name = domains['nonMasterDomains'][0]

        conns = storagedomains.getConnectionsForStorageDomain(self.sd_name)
        LOGGER.info("Connections %s" % conns)
        assert len(conns) == 1
        self.old_path = conns[0].path
        self.conn = conns[0].id
        LOGGER.info("Setup finished")

    def tearDown(self):
        if self.machine is not None:
            self.machine.removeFile(self.path)


class TestCasePosix(TestCase):
    __test__ = False
    conn = None
    host = None
    left_domains = []

    def setUp(self, storage_type, additional_params):
        self.address = config.DOMAIN_ADDRESSES[0]
        self.path = config.DOMAIN_PATHS[0]
        datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)

        assert storagedomains.addStorageDomain(
            True, address=self.address, path=self.path,
            storage_type=storage_type, host=config.HOSTS[0],
            type=config.ENUMS['storage_dom_type_data'],
            name=self.sd_name, **additional_params)

        assert storagedomains.attachStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        assert storagedomains.waitForStorageDomainStatus(
            True, config.DATA_CENTER_NAME, self.sd_name,
            config.ENUMS['storage_domain_state_active'])

        conns = storagedomains.getConnectionsForStorageDomain(self.sd_name)
        assert len(conns) == 1
        self.conn = conns[0].id
        self.host = hosts.getSPMHost(config.HOSTS)
        _, self.password = helpers.get_user_and_passwd_for_host(self.host)

    def tearDown(self, vfs_type):
        LOGGER.info("Tear down")
        LOGGER.info("Detaching and deactivating domain")
        hl_sd.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, self.sd_name)
        host = config.HOSTS[0]
        LOGGER.info("Removing domain %s" % self.sd_name)
        storagedomains.removeStorageDomain(True, self.sd_name, host)
        for (addr, path, sd_id) in self.left_domains:
            LOGGER.info("Cleaning domain %s:%s" % (addr, path))
            helpers.clean_posix_domain(
                addr, path, sd_id, config.HOST_FOR_MNT, 'root',
                config.PASSWD_FOR_MNT, vfs_type)

    def default_update(self):
        pass

    def positive_flow(self, vfs_type):
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        new_address = config.PARAMETERS.as_list('another_address')[0]
        new_path = config.PARAMETERS.as_list('another_path')[0]

        helpers.copy_posix_sd(
            self.address, self.path, new_address, new_path,
            config.HOST_FOR_MNT, 'root', config.PASSWD_FOR_MNT, vfs_type)

        sd = sd_api.find(self.sd_name)

        #just in case - restart vdsm (bug 950055)
        LOGGER.info("Restarting VDSM")
        test_utils.restartVdsmd(self.host, self.password)
        LOGGER.info("Waiting for datacenter up")
        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        assert hosts.waitForHostsStates(True, self.host)

        LOGGER.info("Changing connection")
        result = self.default_update()
        LOGGER.info("result: %s" % result)
        assert result
        self.left_domains.append([self.address, self.path, sd.id])

        LOGGER.info("Activating sd")
        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

    def change_connection_in_active_sd(self):
        #just in case - restart vdsm (bug 950055)
        LOGGER.info("Restarting VDSM")
        test_utils.restartVdsmd(self.host, self.password)
        LOGGER.info("Waiting for datacenter up")
        assert hosts.waitForHostsStates(True, self.host)
        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        LOGGER.info("DC is up")

        result = self.default_update()
        assert not result

        LOGGER.info("Test passed")


class TestCaseNFS(TestCasePosix):
    def setUp(self):
        super(TestCaseNFS, self).setUp('nfs', {})

    def tearDown(self):
        super(TestCaseNFS, self).tearDown('nfs')
        LOGGER.info("After NFS test tearDown")

    def default_update(self):
        LOGGER.info("params: %s" % config.PARAMETERS)
        new_address = config.PARAMETERS.as_list('another_address')[0]
        new_path = config.PARAMETERS.as_list('another_path')[0]

        return storageconnections.update_connection(
            self.conn, address=new_address, path=new_path, type='nfs',
            nfs_version='V3', nfs_retrans=9, nfs_timeo=900, host=self.host)[1]


class TestCasePosixFS(TestCasePosix):
    def setUp(self):
        super(TestCasePosixFS, self).setUp(
            'posixfs', {'vfs_type': config.VFS_TYPE})

    def tearDown(self):
        super(TestCasePosixFS, self).tearDown(config.VFS_TYPE)

    def default_update(self):
        new_address = config.PARAMETERS.as_list('another_address')[0]
        new_path = config.PARAMETERS.as_list('another_path')[0]

        return storageconnections.update_connection(
            self.conn, address=new_address, path=new_path, host=self.host,
            type='posixfs')[1]


class TestCase288707(TestCasePosixFS):
    """
    https://tcms.engineering.redhat.com/case/288707/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE.startswith('posixfs'))
    tcms_plan_id = '9985'
    tcms_test_case = '288707'
    sd_name = "sd_%s" % tcms_test_case

    @tcms(tcms_plan_id, tcms_test_case)
    def test_change_posixfs_connection(self):
        """ Tries to change a posixfs connection
        """
        self.positive_flow(config.VFS_TYPE)


class TestCase288597(TestCaseNFS):
    """
    https://tcms.engineering.redhat.com/case/288597/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE == 'nfs')
    tcms_plan_id = '9985'
    tcms_test_case = '288597'
    sd_name = "sd_%s" % tcms_test_case

    @tcms(tcms_plan_id, tcms_test_case)
    def test_change_nfs_connection(self):
        """ Tries to change an nfs connection
        """
        self.positive_flow('nfs')


class TestCase289001(TestCasePosixFS):
    """
    https://tcms.engineering.redhat.com/case/289001/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE.startswith('posixfs'))
    tcms_plan_id = '9985'
    tcms_test_case = '289001'
    sd_name = "sd_%s" % tcms_test_case
    conn = None

    @tcms(tcms_plan_id, tcms_test_case)
    def test_change_posixfs_connection_in_active_sd(self):
        """ Tries to change a posixfs connection used by an active domain,
            action should fail.
        """
        self.change_connection_in_active_sd()


class TestCase288991(TestCaseNFS):
    """
    https://tcms.engineering.redhat.com/case/288991/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE == 'nfs')
    tcms_plan_id = '9985'
    tcms_test_case = '288991'
    sd_name = "sd_%s" % tcms_test_case
    conn = None

    @tcms(tcms_plan_id, tcms_test_case)
    def test_change_nfs_connection_in_active_sd(self):
        """ Tries to change an nfs connection used by an active domain,
            action should fail
        """
        self.change_connection_in_active_sd()


class TestCase288710(TestCaseNFS):
    """
    https://tcms.engineering.redhat.com/case/288710/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE == 'nfs')
    tcms_plan_id = '9985'
    tcms_test_case = '288710'
    sd_name = "sd_%s" % tcms_test_case

    @bz(950055)
    @tcms(tcms_plan_id, tcms_test_case)
    def test_change_conn_more_than_once(self):
        """ Tries to change the same connection twice.
        """
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        new_address = config.PARAMETERS.as_list('another_address')[0]
        new_path = config.PARAMETERS.as_list('another_path')[0]
        sd = sd_api.find(self.sd_name)

        helpers.copy_nfs_sd(
            self.address, self.path, new_address, new_path,
            config.HOST_FOR_MNT, 'root', config.PASSWD_FOR_MNT)

        #just in case - restart vdsm (bug 950055)
        LOGGER.info("Restarting VDSM")
        test_utils.restartVdsmd(self.host, self.password)
        LOGGER.info("Waiting for datacenter up")
        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        assert hosts.waitForHostsStates(True, self.host)

        result = storageconnections.update_connection(
            self.conn, address=new_address, path=new_path, type='nfs',
            host=self.host)[1]
        assert result

        helpers.clean_nfs_domain(
            self.address, self.path, sd.id, config.HOST_FOR_MNT, 'root',
            config.PASSWD_FOR_MNT)

        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        old_address = new_address
        old_path = new_path

        new_address = config.PARAMETERS.as_list('another_address')[1]
        new_path = config.PARAMETERS.as_list('another_path')[1]

        helpers.copy_nfs_sd(
            self.address, self.path, new_address, new_path,
            config.HOST_FOR_MNT, 'root', config.PASSWD_FOR_MNT)

        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        assert hosts.waitForHostsStates(True, self.host)

        result = storageconnections.update_connection(
            self.conn, address=self.address, path=self.path, type='nfs',
            host=self.host)[1]
        assert result

        self.left_domains[0][0] = old_address
        self.left_domains[0][1] = old_path

        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)


class TestCase293074(TestCaseNFS):
    """
    https://tcms.engineering.redhat.com/case/293074/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE == 'nfs')
    tcms_plan_id = '9985'
    tcms_test_case = '293074'
    sd_name = "sd_%s" % tcms_test_case
    cluster = 'cl_%s' % tcms_test_case
    old_cluster = None

    @tcms(tcms_plan_id, tcms_test_case)
    def test_editing_with_no_active_host(self):
        """ Tries to edit storage connection when there is no host in DC,
            action should fail.
        """
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        host = host_api.find(config.HOSTS[0])
        self.old_cluster = cl_api.find(host.get_cluster().id, attribute='id')
        assert clusters.addCluster(
            True, name=self.cluster, cpu=config.PARAMETERS['cpu_name'],
            version=config.PARAMETERS['compatibility_version'],
            data_center=config.DATA_CENTER_NAME)
        assert clusters.attachHostToCluster(
            True, config.HOSTS[0], self.cluster)
        assert hosts.waitForHostsStates(True, config.HOSTS[0])
        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        LOGGER.info("DC is up")

        new_address = config.PARAMETERS.as_list('another_address')[0]
        new_path = config.PARAMETERS.as_list('another_path')[0]
        result = storageconnections.update_connection(
            self.conn, address=new_address, path=new_path, type='nfs',
            host=self.host)[1]
        assert not result

    def tearDown(self):
        clusters.attachHostToCluster(
            True, config.HOSTS[0], self.old_cluster.name)
        assert hosts.waitForHostsStates(True, config.HOSTS[0])
        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        clusters.removeCluster(True, self.cluster)
        TestCaseNFS.tearDown(self)


class TestCase288708(TestCaseLocalFS):
    """
    https://tcms.engineering.redhat.com/case/288708/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE == 'localfs')
    tcms_plan_id = '9985'
    tcms_test_case = '288708'
    path = "/home/manage_conn_test_%s" % tcms_test_case

    @tcms(tcms_plan_id, tcms_test_case)
    def test_change_local_connection(self):
        """ Tries to change a local connection
        """
        LOGGER.info("Deactivating storage domain")
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        LOGGER.info("Copying sd")
        helpers.copy_local_sd(self.old_path, self.path, self.machine)

        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)

        #just in case - restart vdsm (bug 950055)
        LOGGER.info("Restarting VDSM")
        test_utils.restartVdsmd(self.host, self.password)
        LOGGER.info("Waiting for datacenter up")
        assert datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        assert hosts.waitForHostsStates(True, self.host)

        LOGGER.info("Updating connection")

        _, result = storageconnections.update_connection(
            self.conn, path=self.path, type='localfs', host=self.host)
        assert result

        LOGGER.info("Activating storage domain")
        assert storagedomains.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)
        LOGGER.info("Test finished successfully")

    def tearDown(self):
        # don't assert, it may be still active
        LOGGER.info("Tear down")
        storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_name)

        LOGGER.info("Reverting changes in storage connection")
        storageconnections.update_connection(
            self.conn, path=self.old_path, type='localfs', host=self.host)

        LOGGER.info('Re-activating storage domain')
        storagedomains.activateStorageDomain(True, config.DATA_CENTER_NAME,
                                             self.sd_name)

        LOGGER.info("Calling common tearDown")
        super(TestCase288708, self).tearDown()


class TestCase289228(TestCaseLocalFS):
    """
    https://tcms.engineering.redhat.com/case/289228/?from_plan=9985

    **Author**: Katarzyna Jachim
    """
    __test__ = (config.STORAGE_TYPE == 'localfs')
    tcms_plan_id = '9985'
    tcms_test_case = '289228'
    path = "/home/manage_conn_test_%s" % tcms_test_case

    @tcms(tcms_plan_id, tcms_test_case)
    def test_try_to_change_local_connection_in_active_sd(self):
        """ Tries to change a local connection used by an active domain,
            action should fail.
        """
        result = storageconnections.update_connection(
            self.conn, path=self.path, type='localfs', host=self.host)[1]
        assert not result
