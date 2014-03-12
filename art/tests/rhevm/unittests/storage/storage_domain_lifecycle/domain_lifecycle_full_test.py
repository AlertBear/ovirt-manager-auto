import logging
from art.unittest_lib import BaseTestCase as TestCase
from nose.tools import istest
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_domains
from art.rhevm_api.tests_lib.low_level import datacenters as ll_datacenters
from art.rhevm_api.tests_lib.low_level import clusters as ll_clusters
from art.rhevm_api.tests_lib.low_level import vms, hosts

from art.rhevm_api.tests_lib.high_level import hosts as hi_hosts
from art.rhevm_api.tests_lib.high_level import datacenters, storagedomains
from utilities.utils import getIpAddressByHostName
from art.test_handler.tools import tcms, bz
import art.rhevm_api.utils.storage_api as st_api
import art.rhevm_api.utils.iptables as ip_action

from art.rhevm_api.utils.test_utils import get_api, wait_for_tasks

from art.test_handler import exceptions
from sys import modules


import config

TCMS_PLAN_ID = '6458'
logger = logging.getLogger(__name__)
dc_type = config.DATA_CENTER_TYPE
ENUMS = config.ENUMS

__THIS_MODULE = modules[__name__]

LOGGER = logging.getLogger(__name__)

DC_API = get_api('data_center', 'datacenters')
HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
SD_API = get_api('storage_domain', 'storagedomains')
CLUSTER_API = get_api('cluster', 'clusters')

GB = 1024 ** 3
TEN_GB = 10 * GB


def setup_module():
    """
    creates datacenter, adds hosts, clusters, storages according to
    the config file

    for this TCMS plan we need 3 SD but only one of them should be created on
    setup. the other two SDs will be created manually in the test cases.
    so to accomplish this behaviour, the luns and paths lists are saved
    and overridden with only one lun/path to sent as parameter to build_setup.
    after the build_setup finish, we return to the original lists
    """
    if config.DATA_CENTER_TYPE == config.STORAGE_TYPE_NFS:
        domain_path = config.PATH
        config.PARAMETERS['data_domain_path'] = [domain_path[0]]
    else:
        luns = config.LUNS
        config.PARAMETERS['lun'] = [luns[0]]

    logger.info("Preparing datacenter %s with hosts %s",
                config.DATA_CENTER_NAME, config.VDC)

    datacenters.build_setup(config=config.PARAMETERS,
                            storage=config.PARAMETERS,
                            storage_type=config.DATA_CENTER_TYPE,
                            basename=config.BASENAME)

    if config.DATA_CENTER_TYPE == config.STORAGE_TYPE_NFS:
        config.PARAMETERS['data_domain_path'] = domain_path
    else:
        config.PARAMETERS['lun'] = luns


def teardown_module():
    """
    Removes created datacenter, storages etc.
    """
    ll_st_domains.cleanDataCenter(
        True, config.DATA_CENTER_NAME, vdc=config.VDC,
        vdc_password=config.VDC_PASSWORD)


def put_host_to_cluster(host, cluster):
    """
    Takes host from cluster it currently is in and puts it to given cluster
    Parameters:
        * host - name of the host
        * cluster - target cluster
    """
    host_obj = HOST_API.find(host)
    host_cluster_obj = CLUSTER_API.find(host_obj.cluster.id, 'id')
    if host_cluster_obj.data_center is not None:
        dc_obj = DC_API.find(host_cluster_obj.data_center.id, 'id')
        wait_for_tasks(config.SETUP_ADDRESS, config.VDC_PASSWORD,
                       dc_obj.name)

    assert hi_hosts.deactivate_host_if_up(host)
    assert hosts.updateHost(True, host, cluster=cluster)
    assert hosts.activateHost(True, host)


class BaseTestCase(TestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    tcms_test_case = None
    master_domain_ip = None
    engine_ip = None

    @classmethod
    def setup_class(cls):
        logger.info("DC name : %s", config.DATA_CENTER_NAME)

        found, master_domain = ll_st_domains.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME)
        assert found
        master_domain = master_domain['masterDomain']
        logger.info("Master domain found : %s", master_domain)

        found, cls.master_domain_ip = ll_st_domains.getDomainAddress(
            True, master_domain)
        assert found
        cls.master_domain_ip = cls.master_domain_ip['address']
        logger.info("Master domain ip found : %s", cls.master_domain_ip)

        cls.engine_ip = getIpAddressByHostName(config.VDC)


def _create_sds():
    """
    helper function for creating 2 SD
    Return: False if not all the storage domains was created,
            True otherwise
    """
    status = True
    sd_args = {'type': ENUMS['storage_dom_type_data'],
               'storage_type': config.DATA_CENTER_TYPE,
               'host': config.FIRST_HOST}

    for index in range(1, 3):
        sd_args['name'] = config.SD_NAMES_LIST[index]
        if config.DATA_CENTER_TYPE == 'nfs':
            sd_args['address'] = config.ADDRESS[index]
            sd_args['path'] = config.PATH[index]
        elif config.DATA_CENTER_TYPE == 'iscsi':
            sd_args['lun'] = config.LUNS[index]
            sd_args['lun_address'] = config.LUN_ADDRESS[index]
            sd_args['lun_target'] = config.LUN_TARGET[index]
            sd_args['lun_port'] = config.LUN_PORT

        logger.info('Creating storage domain with parameters: %s', sd_args)
        status = ll_st_domains.addStorageDomain(True, **sd_args) and status

    return status


def _create_vm(vm_name, vm_description, disk_interface,
               sparse=True, volume_format=ENUMS['format_cow'],
               vm_type=config.VM_TYPE_DESKTOP):
    """
    helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    logger.info("Creating VM %s" % vm_name)
    return vms.createVm(
        True, vm_name, vm_description, cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=config.SD_NAME_0,
        size=config.DISK_SIZE,
        diskType=config.DISK_TYPE_SYSTEM,
        volumeType=sparse, volumeFormat=volume_format,
        diskInterface=disk_interface, memory=config.GB,
        cpu_socket=config.CPU_SOCKET,
        cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
        user=config.VM_USER, password=config.VM_PASSWORD,
        type=vm_type, installation=True, slim=True,
        image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
        useAgent=config.USE_AGENT)


class TestCase174610(BaseTestCase):
    """
    * Block connection from engine to host.
    * Wait until host goes to non-responsive.
    * Unblock connection.
    * Check that the host is UP again.
    https://tcms.engineering.redhat.com/case/174610/?from_plan=6458
    """
    __test__ = True
    tcms_test_case = '174610'

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_disconnect_engine_from_host(self):
        """
        Block connection from one engine to host.
        Wait until host goes to non-responsive.
        Unblock connection.
        Check that the host is UP again.
        """
        ip_action.block_and_wait(self.engine_ip, config.VDS_USER[0],
                                 config.VDS_PASSWORD[0], config.FIRST_HOST,
                                 config.FIRST_HOST,
                                 config.HOST_NONRESPONSIVE)

        ip_action.unblock_and_wait(self.engine_ip, config.VDS_USER[0],
                                   config.VDS_PASSWORD[0], config.FIRST_HOST,
                                   config.FIRST_HOST)

    @classmethod
    def teardown_class(cls):
        """
        unblock all connections that were blocked during the test
        """
        logger.info('Unblocking connections')
        try:
            st_api.unblockOutgoingConnection(cls.engine_ip,
                                             config.VDS_USER[0],
                                             config.VDS_PASSWORD[0],
                                             config.FIRST_HOST)
        except exceptions.NetworkException, msg:
            logging.info("Connection already unblocked. reason: %s", msg)


class TestCase174613(TestCase):
    """
    test check if creating storage domain with defined values
    is working properly
    https://tcms.engineering.redhat.com/case/174613/?from_plan=12050
    """
    __test__ = (dc_type == ENUMS['storage_type_nfs'])
    tcms_plan_id = '12050'
    tcms_test_case = '174613'
    nfs_retrans = 4
    nfs_timeout = 900
    nfs_version = 'v3'
    sd_names = config.SD_NAMES_LIST[1:]

    @istest
    @tcms(tcms_plan_id, tcms_test_case)
    def test_create_sd_with_defined_values(self):
        """
        test checks if creating NFS SD with defined values work fine
        """
        version = None
        for index in range(1, 3):
            logger.info("creating storage domain #%s with values:"
                        "retrans = %d, timeout = %d, vers = %s",
                        index,
                        self.nfs_retrans,
                        self.nfs_timeout,
                        version)

            storage = ll_st_domains.NFSStorage(
                name=config.SD_NAMES_LIST[index],
                address=config.ADDRESS[index],
                path=config.PATH[index],
                timeout_to_set=self.nfs_timeout,
                retrans_to_set=self.nfs_retrans,
                vers_to_set=version,
                expected_timeout=self.nfs_timeout,
                expected_retrans=self.nfs_retrans,
                expected_vers=version,
                sd_type=ENUMS['storage_dom_type_data'])

            if not hosts.isHostUp(True, config.FIRST_HOST):
                hosts.activateHost(True, config.FIRST_HOST)

            storagedomains.create_nfs_domain_and_verify_options(
                [storage], host=config.FIRST_HOST,
                password=config.VDS_PASSWORD[0],
                datacenter=config.DATA_CENTER_NAME)

            version = self.nfs_version

    @classmethod
    def teardown_class(cls):
        """
        Removes SD
        """
        logger.info('Removing storage domains')
        assert ll_st_domains.removeStorageDomains(
            True, cls.sd_names, config.FIRST_HOST)


class TestCase174631(TestCase):
    """
    test checks if creating vm disks on different storage
    domain works fine and the disks are functional within guest OS
    https://tcms.engineering.redhat.com/case/174631/?from_plan=6458
    """
    __test__ = True
    tcms_test_case = '174631'
    sd_names = config.SD_NAMES_LIST[1:]
    interfaces = [config.INTERFACE_VIRTIO, config.INTERFACE_IDE]
    formats = [ENUMS['format_cow'], ENUMS['format_raw']]
    num_of_disks = 2

    @classmethod
    def setup_class(cls):
        logger.info('Creating vm and installing OS on it')
        if not _create_vm(config.VM_NAME,
                          config.VM_NAME,
                          config.INTERFACE_VIRTIO_SCSI):
                raise exceptions.VMException("Failed to create VM")

        logger.info('Creating 2 storage domains')
        if not _create_sds():
            raise exceptions.StorageDomainException("Failed to create SDs")

        for sd in cls.sd_names:
            if not ll_st_domains.attachStorageDomain(
                    True, config.DATA_CENTER_NAME, sd):
                raise exceptions.StorageDomainException(
                    "Failed to attach SD %s" % sd)

        logger.info('Shutting down VM %s', config.VM_NAME)
        if not vms.stopVm(True, config.VM_NAME):
            raise exceptions.VMException("Failed to shutdown vm %s"
                                         % config.VM_NAME)

    @tcms(TCMS_PLAN_ID, tcms_test_case)
    def test_multiple_disks_on_different_sd(self):
        """
        creates disks on different SD
        """
        logger.info("Adding new disks")

        for sd in self.sd_names:
            for index in range(self.num_of_disks):
                logger.info("Add new disk - format %s, interface %s",
                            self.formats[index],
                            self.interfaces[index])
                if self.formats[index] == ENUMS['format_raw']:
                    policy_allocation = False
                else:
                    # policy_allocation = True --> sparse
                    policy_allocation = True
                self.assertTrue(vms.addDisk(True, config.VM_NAME,
                                            config.DISK_SIZE, True, sd,
                                            type=ENUMS['disk_type_data'],
                                            interface=self.interfaces[index],
                                            format=self.formats[index],
                                            sparse=policy_allocation),
                                "Failed to add disk")

        self.assertTrue(vms.startVm(True, config.VM_NAME),
                        "Failed to start vm %s" % config.VM_NAME)

        self.assertTrue(vms.stopVm(True, config.VM_NAME),
                        "Failed to stop vm %s" % config.VM_NAME)

    @classmethod
    def teardown_class(cls):
        """
        Removes disks, vm and SDs
        """
        logger.info('Removing vm %s', config.VM_NAME)
        if not vms.removeVm(True, config.VM_NAME, wait=True):
            raise exceptions.VMException(
                "Failed to remove vm %s" % config.VM_NAME)

        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)

        logger.info('Removing storage domains')
        assert ll_st_domains.removeStorageDomains(
            True, cls.sd_names, config.FIRST_HOST)


class TestCase284310(TestCase):
    """
    Starting version 3.3 attaching domains should activate them automatically.
    https://tcms.engineering.redhat.com/case/284310/?from_plan=5292
    """
    __test__ = True
    tcms_plan_id = '5292'
    tcms_test_case = '284310'
    sd_names = config.SD_NAMES_LIST[1:]

    @tcms(tcms_plan_id, tcms_test_case)
    def add_another_storage_domain_test(self):
        """
        Check that both storage domains were automatically activated
        after attaching them.
        """

        logger.info('Creating 2 storage domains')
        if not _create_sds():
            raise exceptions.StorageDomainException("Failed to create SDs")

        for sd in self.sd_names:
            if not ll_st_domains.attachStorageDomain(
                    True, config.DATA_CENTER_NAME, sd):
                raise exceptions.StorageDomainException(
                    "Failed to attach SD %s" % sd)

        for sd in self.sd_names:
            self.assertTrue(ll_st_domains.is_storage_domain_active(
                config.DATA_CENTER_NAME, sd))

    @classmethod
    def teardown_class(cls):
        """
        Removes SD
        """
        logger.info('Removing storage domains')
        assert ll_st_domains.removeStorageDomains(
            True, cls.sd_names, config.FIRST_HOST)


class TestUpgrade(TestCase):
    """
    Base class for upgrade testing
    """
    __test__ = False
    dc_name = None
    cluster_name = None
    sd_name_pattern = None
    storage_type = None
    dc_version = None
    dc_upgraded_version = None
    storage_format = None
    upgraded_storage_format = None
    cluster_version = "3.3"
    host = config.FIRST_HOST
    vm_name = 'vm_test'
    domain_kw = None
    if config.DATA_CENTER_TYPE == config.STORAGE_TYPE_NFS:
        sd_paths = config.PARAMETERS['data_domain_path'][1:]

    else:
        sd_luns = config.PARAMETERS['lun'][1:]

    @classmethod
    def setup_class(cls):
        """
        Prepares data-center without storages
        """
        LOGGER.info("Running class %s setup", cls.__name__)
        assert ll_datacenters.addDataCenter(True, name=cls.dc_name,
                                            storage_type=cls.storage_type,
                                            version=cls.dc_version)
        assert ll_clusters.addCluster(True, name=cls.cluster_name,
                                      cpu=config.PARAMETERS['cpu_name'],
                                      data_center=cls.dc_name,
                                      version=cls.cluster_version)
        put_host_to_cluster(cls.host, cls.cluster_name)

    @classmethod
    def teardown_class(cls):
        """
        Removes data-center, cluster, storage domains and puts hosts to
        temporary cluster
        """
        LOGGER.info("Running class %s teardown", cls.__name__)
        vms_objects = VM_API.get(absLink=False)
        up_vms = [vm.get_name() for vm in vms_objects if not
                  vm.get_status().get_state() == config.ENUMS['vm_state_down']]
        up_vms = ','.join(up_vms)
        LOGGER.info("Stopping vms")
        vms.stopVms(up_vms)
        LOGGER.info("Removing vms")
        for vm_obj in vms_objects:
            vms.removeVm(True, vm_obj.get_name())
        vdc = config.VDC
        vdc_password = config.VDC_PASSWORD
        if vdc is not None and vdc_password is not None:
            LOGGER.info('Waiting for vms to be removed')
            wait_for_tasks(
                vdc=vdc, vdc_password=vdc_password, datacenter=cls.dc_name)

        LOGGER.info('Deactivating non master storage domains')
        assert ll_st_domains.execOnNonMasterDomains(
            True, cls.dc_name, 'deactivate', 'all')
        LOGGER.info('Detaching non master storage domains')
        assert ll_st_domains.execOnNonMasterDomains(
            True, cls.dc_name, 'detach', 'all')

        _, master_name = ll_st_domains.findMasterStorageDomain(
            True, cls.dc_name)
        LOGGER.info('Deactivating master storage domains %s',
                    master_name['masterDomain'])

        assert ll_st_domains.deactivateStorageDomain(
            True, cls.dc_name, master_name['masterDomain'])

        LOGGER.info('Removing data center %s', cls.dc_name)
        assert ll_datacenters.removeDataCenter(True, cls.dc_name)

        for i in range(len(config.PARAMETERS.as_list(cls.domain_kw))):
            assert ll_st_domains.removeStorageDomain(
                True, cls.sd_name_pattern % i, cls.host)
            LOGGER.info("%s storage domain %s was removed successfully",
                        cls.storage_type, cls.sd_name_pattern % i)
        put_host_to_cluster(cls.host, config.TMP_CLUSTER_NAME)
        assert ll_clusters.removeCluster(True, cls.cluster_name)

        LOGGER.info("Class %s teardown finished", cls.__name__)

    def test_data_center_upgrade(self):
        """
        Changes DC version while installing a VM
        """
        nic = config.PARAMETERS['host_nics'][0]

        assert vms.createVm(
            True, self.vm_name, '', cluster=self.cluster_name,
            nic=nic, nicType=config.ENUMS['nic_type_virtio'],
            storageDomainName=self.sd_name_pattern % 0,
            size=TEN_GB, diskType=config.ENUMS['disk_type_system'],
            volumeFormat=config.ENUMS['format_cow'],
            diskInterface=config.INTERFACE_VIRTIO,
            bootable=True, wipe_after_delete=False,
            type=config.ENUMS['vm_type_server'], os_type="rhel6x64",
            memory=1073741824, cpu_socket=1, cpu_cores=1,
            display_type=config.ENUMS['display_type_spice'],
            network=config.PARAMETERS['mgmt_bridge'])
        assert vms.unattendedInstallation(
            True, self.vm_name, config.PARAMETERS['cobbler_profile'], nic=nic,
            cobblerAddress=config.PARAMETERS.get('cobbler_address', None),
            cobblerUser=config.PARAMETERS.get('cobbler_user', None),
            cobblerPasswd=config.PARAMETERS.get('cobbler_passwd', None))
        assert vms.waitForVMState(self.vm_name)
        # getVmMacAddress returns (bool, dict(macAddress=<desired_mac>))
        mac = vms.getVmMacAddress(True, self.vm_name, nic=nic)[1]
        mac = mac['macAddress']
        LOGGER.debug("Got mac of vm %s: %s", self.vm_name, mac)
        assert vms.removeSystem(mac)

        LOGGER.info("Upgrading data-center %s from version %s to version %s ",
                    self.dc_name, self.dc_version, self.dc_upgraded_version)
        ll_datacenters.updateDataCenter(True, datacenter=self.dc_name,
                                        version=self.dc_upgraded_version)
        sds = ll_st_domains.getDCStorages(self.dc_name, get_href=False)
        for sd_obj in sds:
            was_upgraded = ll_st_domains.checkStorageFormatVersion(
                True, sd_obj.name, self.upgraded_storage_format)
            LOGGER.info("Checking that %s was upgraded: %s", sd_obj.name,
                        was_upgraded)
            self.assertTrue(was_upgraded)


class TestUpgradeNFS(TestUpgrade):
    """
    Building NFS data center
    """
    storage_type = config.ENUMS['storage_type_nfs']
    domain_kw = 'data_domain_address'

    @classmethod
    def setup_class(cls):
        super(TestUpgradeNFS, cls).setup_class()
        for index, (address, path) in enumerate(zip(
                config.PARAMETERS.as_list('data_domain_address'),
                cls.sd_paths)):
            assert storagedomains.addNFSDomain(
                cls.host, cls.sd_name_pattern % index, cls.dc_name, address,
                path, storage_format=cls.storage_format)
            LOGGER.info("NFS storage domain %s was created successfully",
                        cls.sd_name_pattern % index)


class TestUpgradeISCSI(TestUpgrade):
    """
    Building iSCSI data center
    """
    storage_type = config.ENUMS['storage_type_iscsi']
    domain_kw = 'lun'

    @classmethod
    def setup_class(cls):
        super(TestUpgradeISCSI, cls).setup_class()
        for index, (lun_address, lun_target, lun) in enumerate(zip(
                config.PARAMETERS.as_list('lun_address'),
                config.PARAMETERS.as_list('lun_target'),
                cls.sd_luns)):
            assert storagedomains.addISCSIDataDomain(
                cls.host, cls.sd_name_pattern % index, cls.dc_name, lun,
                lun_address, lun_target, storage_format=cls.storage_format)
            LOGGER.info("iSCSI storage domains %s were created successfully",
                        cls.sd_name_pattern % index)


class TestUpgradeLocal(TestUpgrade):
    """
    Building local data center
    """
    storage_type = config.ENUMS['storage_type_local']

    @classmethod
    def setup_class(cls):
        raise NotImplementedError("Local test hasn't been implemented yet")
        # uncomment it when you implement localfs tests
        #super(TestUpgradeLocal, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        raise NotImplementedError("Local test hasn't been implemented yet")
        # uncomment it when you implement localfs tests
        #super(TestUpgradeLocal, cls).teardown_class()


class TestUpgradePosix(TestUpgrade):
    """
    Building posixfs data center
    """
    storage_type = config.ENUMS['storage_type_posixfs']

    @classmethod
    def setup_class(cls):
        raise NotImplementedError("Posix test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        #super(TestUpgradePosix, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        raise NotImplementedError("Posix test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        #super(TestUpgradePosix, cls).teardown_class()


class TestUpgradeFCP(TestUpgrade):
    """
    Building FCP data center
    """
    storage_type = config.ENUMS['storage_type_fcp']

    @classmethod
    def setup_class(cls):
        raise NotImplementedError("FCP test hasn't been implemented yet")
        # uncomment it when you implement fcp tests
        #super(TestUpgradeFCP, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        raise NotImplementedError("FCP test hasn't been implemented yet")
        # uncomment it when you implement fcp tests
        #super(TestUpgradeFCP, cls).teardown_class()


# dict to map storage type to storage class to use
TYPE_TO_CLASS = {
    config.ENUMS['storage_type_nfs']: TestUpgradeNFS,
    config.ENUMS['storage_type_iscsi']: TestUpgradeISCSI,
    config.ENUMS['storage_type_local']: TestUpgradeLocal,
    config.ENUMS['storage_type_fcp']: TestUpgradeFCP,
    config.ENUMS['storage_type_posixfs']: TestUpgradePosix,
}

storage_v3_format = config.ENUMS['storage_format_version_v3']
for dc_version in config.DC_VERSIONS:
    dc_version_name = dc_version.replace('.', '')
    for dc_upgrade_version in config.DC_UPGRADE_VERSIONS:
        if dc_version == dc_upgrade_version:
            continue
        dc_upgrade_version_name = dc_upgrade_version.replace('.', '')
        if config.DC_TYPE == config.ENUMS['storage_type_nfs']:
            storage_format = config.ENUMS['storage_format_version_v1']
        elif config.DC_TYPE == config.ENUMS['storage_type_iscsi']:
            storage_format = config.ENUMS['storage_format_version_v2']
        name_pattern = (config.DC_TYPE, dc_version_name,
                        dc_upgrade_version_name)
        class_name = "TestUpgrade%s%s%s" % name_pattern
        doc = "Test case upgrades %s datacenter from %s to %s" % name_pattern
        class_attrs = {
            '__doc__': doc,
            '__test__': True,
            'dc_name': 'dc_%s_upgrade_%s_%s' % name_pattern,
            'cluster_name': 'c_%s_upgrade_%s_%s' % name_pattern,
            'sd_name_pattern': "%s%%d_%s_%s" % name_pattern,
            'dc_version': dc_version,
            'dc_upgraded_version': dc_upgrade_version,
            'storage_format': storage_format,
            'upgraded_storage_format': storage_v3_format
        }
        new_class = type(class_name, (TYPE_TO_CLASS[config.DC_TYPE],),
                         class_attrs)
        setattr(__THIS_MODULE, class_name, new_class)
delattr(__THIS_MODULE, 'new_class')
