import config
import logging
from art.rhevm_api.tests_lib.low_level.clusters import addCluster
from art.unittest_lib import StorageTest as TestCase
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_st_domains
from art.rhevm_api.tests_lib.low_level import datacenters as ll_datacenters
from art.rhevm_api.tests_lib.low_level import clusters as ll_clusters
from art.rhevm_api.tests_lib.low_level import vms, hosts
from art.unittest_lib import attr
from art.rhevm_api.tests_lib.high_level import hosts as hi_hosts
from art.rhevm_api.tests_lib.high_level import datacenters, storagedomains
from utilities.utils import getIpAddressByHostName
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.utils.storage_api as st_api
import art.rhevm_api.utils.iptables as ip_action
from art.rhevm_api.utils.test_utils import get_api, wait_for_tasks
from rhevmtests.storage.helpers import create_vm_or_clone
from art.test_handler import exceptions
from sys import modules
from art.test_handler.settings import opts


logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

__THIS_MODULE = modules[__name__]

LOGGER = logging.getLogger(__name__)

DC_API = get_api('data_center', 'datacenters')
HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
SD_API = get_api('storage_domain', 'storagedomains')
CLUSTER_API = get_api('cluster', 'clusters')
CLI_CMD_DF = 'df -H'
TEN_GB = 10 * config.GB
DATA_CENTER_TIMEOUT = 60 * 5
NFS = config.STORAGE_TYPE_NFS

ProvisionContext = vms.ProvisionContext


def setup_module():
    """
    creates datacenter, adds hosts, clusters, storages according to
    the config file

    for this Polarion plan we need 3 SD but only one of them should be
    created on setup. the other two SDs will be created manually in the test
    cases.  In order to accomplish this behaviour, the luns and paths lists
    are saved and overridden with only one lun/path to sent as parameter to
    build_setup.  After the build_setup finish, we return to the original lists
    """
    if not config.GOLDEN_ENV:
        if config.STORAGE_TYPE == config.STORAGE_TYPE_NFS:
            domain_path = config.PATH
            config.PARAMETERS['data_domain_path'] = [domain_path[0]]
        elif config.STORAGE_TYPE == config.STORAGE_TYPE_GLUSTER:
            domain_path = config.GLUSTER_PATH
            config.PARAMETERS['gluster_data_domain_path'] = [domain_path[0]]
        else:
            luns = config.LUNS
            config.PARAMETERS['lun'] = [luns[0]]

        logger.info("Preparing datacenter %s with hosts %s",
                    config.DATA_CENTER_NAME, config.VDC)

        datacenters.build_setup(config=config.PARAMETERS,
                                storage=config.PARAMETERS,
                                storage_type=config.STORAGE_TYPE)

        if config.STORAGE_TYPE == config.STORAGE_TYPE_NFS:
            config.PARAMETERS['data_domain_path'] = domain_path
        elif config.STORAGE_TYPE == config.STORAGE_TYPE_GLUSTER:
            config.PARAMETERS['gluster_data_domain_path'] = domain_path
        else:
            config.PARAMETERS['lun'] = luns

    # LIFECYCLE_* will be the device parameters used for this tests
    if not config.GOLDEN_ENV:
        if config.STORAGE_TYPE == config.STORAGE_TYPE_NFS:
            config.LIFECYCLE_ADDRESS = config.ADDRESS
            config.LIFECYCLE_PATH = config.PATH
            config.PARAMETERS['data_domain_path'] = domain_path
        elif config.STORAGE_TYPE == config.STORAGE_TYPE_ISCSI:
            config.LIFECYCLE_LUNS = config.LUNS
            config.LIFECYCLE_LUN_ADDRESS = config.LUN_ADDRESS
            config.LIFECYCLE_LUN_TARGET = config.LUN_TARGET
            config.PARAMETERS['lun'] = luns
        elif config.STORAGE_TYPE == config.STORAGE_TYPE_GLUSTER:
            config.GLUSTER_LIFECYCLE_ADDRESS = config.GLUSTER_ADDRESS
            config.GLUSTER_LIFECYCLE_PATH = config.GLUSTER_PATH
            config.PARAMETERS['gluster_data_domain_path'] = domain_path
    else:
        config.LIFECYCLE_ADDRESS = config.UNUSED_DATA_DOMAIN_ADDRESSES
        config.LIFECYCLE_PATH = config.UNUSED_DATA_DOMAIN_PATHS
        config.GLUSTER_LIFECYCLE_ADDRESS = \
            config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES
        config.GLUSTER_LIFECYCLE_PATH = \
            config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS
        config.LIFECYCLE_LUNS = config.UNUSED_LUNS
        config.LIFECYCLE_LUN_ADDRESS = config.UNUSED_LUN_ADDRESSES
        config.LIFECYCLE_LUN_TARGET = config.UNUSED_LUN_TARGETS

    logger.info("Adding temporary cluster %s for upgrade tests to dc %s",
                config.TMP_CLUSTER_NAME, config.DATA_CENTER_NAME)
    assert addCluster(True, name=config.TMP_CLUSTER_NAME,
                      cpu=config.PARAMETERS['cpu_name'],
                      data_center=config.DATA_CENTER_NAME,
                      version=config.COMPATIBILITY_VERSION)


def teardown_module():
    """
    Removes created datacenter, storages etc.
    """
    logger.info("Putting host %s back to cluster %s",
                config.FIRST_HOST, config.CLUSTER_NAME)
    put_host_to_cluster(config.FIRST_HOST, config.CLUSTER_NAME)
    logger.info("Removing cluster %s", config.TMP_CLUSTER_NAME)
    ll_clusters.removeCluster(True, config.TMP_CLUSTER_NAME)

    if not config.GOLDEN_ENV:
        datacenters.clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )


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
    polarion_test_case = None
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
        cls.first_host_ip = hosts.getHostIP(config.FIRST_HOST)


def _create_sds(storage_type, host):
    """
    Helper function for creating two storage domains
    Return: False if not all the storage domains were created,
            True otherwise
    """
    status = True
    sd_args = {'type': ENUMS['storage_dom_type_data'],
               'storage_type': storage_type,
               'host': host}

    for index in range(1, config.EXTRA_SD_INDEX):
        sd_args['name'] = config.LIFECYCLE_DOMAIN_NAMES[index]
        if storage_type == config.STORAGE_TYPE_ISCSI:
            sd_args['lun'] = config.LIFECYCLE_LUNS[index]
            sd_args['lun_address'] = config.LIFECYCLE_LUN_ADDRESS[index]
            sd_args['lun_target'] = config.LIFECYCLE_LUN_TARGET[index]
            sd_args['lun_port'] = config.LUN_PORT
            sd_args['override_luns'] = True
        elif storage_type == config.STORAGE_TYPE_NFS:
            sd_args['address'] = config.LIFECYCLE_ADDRESS[index]
            sd_args['path'] = config.LIFECYCLE_PATH[index]
        elif storage_type == config.STORAGE_TYPE_GLUSTER:
            sd_args['address'] = config.GLUSTER_LIFECYCLE_ADDRESS[index]
            sd_args['path'] = config.GLUSTER_LIFECYCLE_PATH[index]
            sd_args['vfs_type'] = config.ENUMS['vfs_type_glusterfs']

        logger.info('Creating storage domain with parameters: %s', sd_args)
        status = ll_st_domains.addStorageDomain(True, **sd_args) and status

    return status


def _create_vm(vm_name, vm_description, disk_interface,
               sparse=True, volume_format=config.COW_DISK,
               vm_type=config.VM_TYPE_DESKTOP,
               storageDomainName=None):
    """
    helper function for creating vm (passes common arguments, mostly taken
    from the configuration file)
    """
    logger.info("Creating VM %s" % vm_name)
    return create_vm_or_clone(
        True, vm_name, vm_description, cluster=config.CLUSTER_NAME,
        nic=config.NIC_NAME[0], storageDomainName=storageDomainName,
        size=config.DISK_SIZE,
        diskType=config.DISK_TYPE_SYSTEM,
        volumeType=sparse, volumeFormat=volume_format,
        diskInterface=disk_interface, memory=config.GB,
        cpu_socket=config.CPU_SOCKET,
        cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
        user=config.VMS_LINUX_USER, password=config.VMS_LINUX_PW,
        type=vm_type, installation=True, slim=True,
        image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
        useAgent=config.USE_AGENT)


@attr(tier=3)
class TestCase11598(BaseTestCase):
    """
    * Block connection from engine to host.
    * Wait until host goes to non-responsive.
    * Unblock connection.
    * Check that the host is UP again.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11598'

    @polarion("RHEVM3-11598")
    def test_disconnect_engine_from_host(self):
        """
        Block connection from one engine to host.
        Wait until host goes to non-responsive.
        Unblock connection.
        Check that the host is UP again.
        """
        assert ip_action.block_and_wait(self.engine_ip, config.HOSTS_USER,
                                        config.HOSTS_PW, self.first_host_ip,
                                        config.FIRST_HOST,
                                        config.HOST_NONRESPONSIVE)

        assert ip_action.unblock_and_wait(self.engine_ip, config.HOSTS_USER,
                                          config.HOSTS_PW, self.first_host_ip,
                                          config.FIRST_HOST)

    @classmethod
    def teardown_class(cls):
        """
        unblock all connections that were blocked during the test
        """
        def everything_ok():
            return (
                ll_datacenters.waitForDataCenterState(
                    config.DATA_CENTER_NAME, timeout=DATA_CENTER_TIMEOUT) and
                hosts.isHostUp(True, config.FIRST_HOST)
            )

        if not everything_ok():
            logger.info('Unblocking connections, something went wront')
            try:
                st_api.unblockOutgoingConnection(cls.engine_ip,
                                                 config.HOSTS_USER,
                                                 config.HOSTS_PW,
                                                 cls.first_host_ip)
            except exceptions.NetworkException, msg:
                logging.info("Connection already unblocked. reason: %s", msg)

        assert everything_ok()


@attr(tier=1)
class TestCase4817(TestCase):
    """
    test check if creating storage domain with defined values
    is working properly

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = (NFS in opts['storages'])
    storages = set([NFS])
    polarion_test_case = '4817'
    nfs_retrans = 5
    nfs_timeout = 10
    nfs_version = 'v3'
    mount_options = 'sync'
    sd_names = config.LIFECYCLE_DOMAIN_NAMES[1:]

    @polarion("RHEVM3-4817")
    def test_create_sd_with_defined_values(self):
        """
        test checks if creating NFS SD with defined values work fine
        """
        version = None
        mount_options = None
        for index in range(1, config.EXTRA_SD_INDEX):
            logger.info("creating storage domain #%s with values:"
                        "retrans = %d, timeout = %d, vers = %s",
                        index,
                        self.nfs_retrans,
                        self.nfs_timeout,
                        version)

            storage = ll_st_domains.NFSStorage(
                name=config.LIFECYCLE_DOMAIN_NAMES[index],
                address=config.LIFECYCLE_ADDRESS[index],
                path=config.LIFECYCLE_PATH[index],
                timeout_to_set=self.nfs_timeout,
                retrans_to_set=self.nfs_retrans,
                mount_options_to_set=mount_options,
                vers_to_set=version,
                expected_timeout=self.nfs_timeout,
                expected_retrans=self.nfs_retrans,
                expected_vers=version,
                expected_mount_options=mount_options,
                sd_type=ENUMS['storage_dom_type_data'])

            if not hosts.isHostUp(True, config.FIRST_HOST):
                hosts.activateHost(True, config.FIRST_HOST)

            storagedomains.create_nfs_domain_and_verify_options(
                [storage], host=config.FIRST_HOST,
                password=config.HOSTS_PW,
                datacenter=config.DATA_CENTER_NAME)

            version = self.nfs_version
            mount_options = self.mount_options

    @classmethod
    def teardown_class(cls):
        """
        Remove storage domains
        """
        logger.info("Waiting for tasks before deactivating/removing the "
                    "storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        logger.info('Removing storage domains')
        assert ll_st_domains.removeStorageDomains(
            True, cls.sd_names, config.FIRST_HOST)

        host_ip = hosts.getHostIP(config.FIRST_HOST)
        logger.info("Getting info about mounted resources")
        mounted_resources = ll_st_domains.get_mounted_nfs_resources(
            host=host_ip,
            password=config.HOSTS_PW)

        for index in range(1, config.EXTRA_SD_INDEX):
            if ((config.LIFECYCLE_ADDRESS[index], config.LIFECYCLE_PATH[index])
                    in mounted_resources.keys()):
                raise exceptions.StorageDomainException(
                    "Mount of %s:%s was found on %s, although SD was removed" %
                    config.LIFECYCLE_ADDRESS[index],
                    config.LIFECYCLE_PATH[index],
                    config.FIRST_HOST,
                    config.LIFECYCLE_DOMAIN_NAMES[index])


@attr(tier=1)
class TestCase4815(TestCase):
    """
    test check if bad and conflict parameters for creating storage
    domain are blocked

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = (NFS in opts['storages'])
    storages = set([NFS])

    polarion_test_case = '4815'

    sds_params = []
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'vers=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'nfsvers=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'protocol_version=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'vfs_type=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'retrans=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 6,
        'nfs_timeout': 10,
        'mount_options': 'timeo=4',
    })
    sds_params.append({
        'nfs_version': 'v4',
        'nfs_retrans': 'A',
        'nfs_timeout': 10,
        'mount_options': None,
    })

    sd_names = config.LIFECYCLE_DOMAIN_NAMES[1:]

    @polarion("RHEVM3-4815")
    def test_create_sd_with_defined_values(self):
        """
        test check if bad and conflict parameters for creating storage
        domain are blocked
        """
        for sd_params in self.sds_params:
            logger.info("creating storage domain with values:"
                        "retrans = %s, timeout = %d, vers = %s, "
                        "mount_optiones = %s",
                        sd_params['nfs_retrans'],
                        sd_params['nfs_timeout'],
                        sd_params['nfs_version'],
                        sd_params['mount_options'])

            storage = ll_st_domains.NFSStorage(
                name=config.LIFECYCLE_DOMAIN_NAMES[1],
                address=config.LIFECYCLE_ADDRESS[1],
                path=config.LIFECYCLE_PATH[1],
                timeout_to_set=sd_params['nfs_timeout'],
                retrans_to_set=sd_params['nfs_retrans'],
                mount_options_to_set=sd_params['mount_options'],
                vers_to_set=sd_params['nfs_version'],
                expected_timeout=sd_params['nfs_timeout'],
                expected_retrans=sd_params['nfs_retrans'],
                expected_vers=sd_params['nfs_version'],
                sd_type=ENUMS['storage_dom_type_data'])

            if not hosts.isHostUp(True, config.FIRST_HOST):
                hosts.activateHost(True, config.FIRST_HOST)

            logger.info("Attempt to create domain %s with wrong params ",
                        storage.name)
            storagedomains.create_nfs_domain_with_options(
                name=storage.name, sd_type=storage.sd_type,
                host=config.FIRST_HOST, address=storage.address,
                path=storage.path, version=storage.vers_to_set,
                retrans=storage.retrans_to_set, timeo=storage.timeout_to_set,
                mount_options=storage.mount_options_to_set,
                datacenter=config.DATA_CENTER_NAME,
                positive=False)

    @classmethod
    def teardown_class(cls):
        """
        Removes Storage domains
        """
        logger.info("Waiting for tasks before deactivating/removing the "
                    "storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        logger.info('Removing storage domains')
        assert ll_st_domains.removeStorageDomains(
            True, cls.sd_names, config.FIRST_HOST)


@attr(tier=1)
class TestCase11581(TestCase):
    """
    test checks if creating vm disks on different storage
    domain works fine and the disks are functional within guest OS
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11581'
    sd_names = config.LIFECYCLE_DOMAIN_NAMES[1:]
    interfaces = [config.INTERFACE_VIRTIO, config.INTERFACE_IDE]
    formats = [ENUMS['format_cow'], ENUMS['format_raw']]
    num_of_disks = 2

    @classmethod
    def setup_class(cls):
        cls.first_domain = ll_st_domains.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage)[0]
        logger.info('Creating vm and installing OS on it')
        if not _create_vm(config.LIFECYCLE_VM,
                          config.LIFECYCLE_VM,
                          config.INTERFACE_VIRTIO_SCSI,
                          storageDomainName=cls.first_domain):
            raise exceptions.VMException("Failed to create VM")

        logger.info('Creating 2 storage domains')
        if not _create_sds(cls.storage, config.FIRST_HOST):
            raise exceptions.StorageDomainException("Failed to create SDs")

        for sd in cls.sd_names:
            if not ll_st_domains.attachStorageDomain(
                    True, config.DATA_CENTER_NAME, sd):
                raise exceptions.StorageDomainException(
                    "Failed to attach SD %s" % sd)

        logger.info('Shutting down VM %s', config.LIFECYCLE_VM)
        if not vms.stopVm(True, config.LIFECYCLE_VM):
            raise exceptions.VMException("Failed to shutdown vm %s"
                                         % config.LIFECYCLE_VM)

    @polarion("RHEVM3-11581")
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
                self.assertTrue(vms.addDisk(True, config.LIFECYCLE_VM,
                                            config.DISK_SIZE, True, sd,
                                            type=ENUMS['disk_type_data'],
                                            interface=self.interfaces[index],
                                            format=self.formats[index],
                                            sparse=policy_allocation),
                                "Failed to add disk")

        self.assertTrue(vms.startVm(True, config.LIFECYCLE_VM),
                        "Failed to start vm %s" % config.LIFECYCLE_VM)

        self.assertTrue(vms.stopVm(True, config.LIFECYCLE_VM),
                        "Failed to stop vm %s" % config.LIFECYCLE_VM)

    @classmethod
    def teardown_class(cls):
        """
        Removes disks, vm and SDs
        """
        logger.info('Removing vm %s', config.LIFECYCLE_VM)
        if not vms.safely_remove_vms([config.LIFECYCLE_VM]):
            raise exceptions.VMException(
                "Failed to remove vm %s" % config.LIFECYCLE_VM)

        logger.info("Waiting for tasks before deactivating/removing the "
                    "storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)

        logger.info('Removing storage domains')
        assert ll_st_domains.removeStorageDomains(
            True, cls.sd_names, config.FIRST_HOST)


@attr(tier=1)
class TestCase11784(TestCase):
    """
    Starting version 3.3 attaching domains should activate them automatically.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Multiple_Storage_Domains_General
    """
    __test__ = True
    polarion_test_case = '11784'
    sd_names = config.LIFECYCLE_DOMAIN_NAMES[1:]

    @polarion("RHEVM3-11784")
    def test_add_another_storage_domain_test(self):
        """
        Check that both storage domains were automatically activated
        after attaching them.
        """

        logger.info('Creating 2 storage domains')
        if not _create_sds(self.storage, config.FIRST_HOST):
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
        logger.info("Waiting for tasks before deactivating/removing the "
                    "storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        logger.info('Removing storage domains')
        assert ll_st_domains.removeStorageDomains(
            True, cls.sd_names, config.FIRST_HOST)


@attr(tier=1)
class TestUpgrade(TestCase):
    """
    Base class for upgrade testing
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Storage_Domain_Live_Upgrade
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
    cluster_version = config.COMP_VERSION
    host = config.FIRST_HOST
    vm_name = 'TestUpgrade_vm_test'
    domain_kw = None
    polarion_test_case = '11743'

    @classmethod
    def setup_class(cls):
        """
        Prepares Data center without storage
        """
        if cls.storage == config.STORAGE_TYPE_NFS:
            cls.sd_paths = config.LIFECYCLE_PATH[1:]
            cls.sd_address = config.LIFECYCLE_ADDRESS[1:]
        elif cls.storage == config.STORAGE_TYPE_GLUSTER:
            cls.sd_paths = config.GLUSTER_LIFECYCLE_PATH[1:]
            cls.sd_address = config.GLUSTER_LIFECYCLE_ADDRESS[1:]
        else:
            cls.sd_luns = config.LIFECYCLE_LUNS[1:]
            cls.sd_luns_address = config.LIFECYCLE_LUN_ADDRESS[1:]
            cls.sd_luns_target = config.LIFECYCLE_LUN_TARGET[1:]

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
        LOGGER.info("Remove vm %s", cls.vm_name)
        vms.safely_remove_vms([cls.vm_name])

        LOGGER.info("Waiting for tasks before deactivating the storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD, cls.dc_name)
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
        LOGGER.info("Waiting for tasks before deactivating the storage domain")
        wait_for_tasks(config.VDC, config.VDC_PASSWORD, cls.dc_name)
        assert ll_st_domains.deactivateStorageDomain(
            True, cls.dc_name, master_name['masterDomain'])

        LOGGER.info('Removing data center %s', cls.dc_name)
        assert ll_datacenters.removeDataCenter(True, cls.dc_name)

        # there number of domains created for dc test always 1 less than total
        # number of storage devices defined since other cases (not upgrade)
        # use the additional storage device for their own domain
        for i in range(len(config.PARAMETERS.as_list(cls.domain_kw)) - 1):
            assert ll_st_domains.removeStorageDomain(
                True, cls.sd_name_pattern % i, cls.host, 'true'
            )
            LOGGER.info("%s storage domain %s was removed successfully",
                        cls.storage_type, cls.sd_name_pattern % i)
        put_host_to_cluster(cls.host, config.TMP_CLUSTER_NAME)
        assert ll_clusters.removeCluster(True, cls.cluster_name)

        LOGGER.info("Class %s teardown finished", cls.__name__)

    @polarion("RHEVM3-11743")
    def test_data_center_upgrade(self):
        """
        Changes DC version while installing a VM
        """
        nic = config.NIC_NAME[0]
        assert vms.createVm(
            True, self.vm_name, '', cluster=self.cluster_name,
            nic=nic, nicType=config.ENUMS['nic_type_virtio'],
            storageDomainName=self.sd_name_pattern % 0,
            size=TEN_GB, diskType=config.ENUMS['disk_type_system'],
            volumeFormat=config.ENUMS['format_cow'],
            diskInterface=config.INTERFACE_VIRTIO,
            bootable=True, wipe_after_delete=False,
            type=config.ENUMS['vm_type_server'], os_type="rhel6x64",
            memory=config.GB, cpu_socket=1, cpu_cores=1,
            display_type=config.DISPLAY_TYPE,
            network=config.MGMT_BRIDGE)
        try:
            assert vms.unattendedInstallation(
                True, self.vm_name, config.COBBLER_PROFILE, nic=nic)
            assert vms.waitForVMState(self.vm_name)
            # getVmMacAddress returns (bool, dict(macAddress=<desired_mac>))
            mac = vms.getVmMacAddress(True, self.vm_name, nic=nic)[1]
            mac = mac['macAddress']
            LOGGER.debug("Got mac of vm %s: %s", self.vm_name, mac)
        finally:
            ProvisionContext.clear()

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
        logger.info("Adding nfs storage domains needed for tests")
        logger.info("Addresses: %s, Paths: %s", cls.sd_address, cls.sd_paths)
        for index, (address, path) in enumerate(zip(
                cls.sd_address,
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
                cls.sd_luns_address,
                cls.sd_luns_target,
                cls.sd_luns)):
            assert storagedomains.addISCSIDataDomain(
                cls.host, cls.sd_name_pattern % index, cls.dc_name, lun,
                lun_address, lun_target, storage_format=cls.storage_format,
                override_luns=True
            )
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
        # super(TestUpgradeLocal, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        raise NotImplementedError("Local test hasn't been implemented yet")
        # uncomment it when you implement localfs tests
        # super(TestUpgradeLocal, cls).teardown_class()


class TestUpgradePosix(TestUpgrade):
    """
    Building posixfs data center
    """
    storage_type = config.ENUMS['storage_type_posixfs']

    @classmethod
    def setup_class(cls):
        raise NotImplementedError("Posix test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        # super(TestUpgradePosix, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        raise NotImplementedError("Posix test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        # super(TestUpgradePosix, cls).teardown_class()


class TestUpgradeGluster(TestUpgrade):
    """
    Building glusterfs data center
    """
    storage_type = config.ENUMS['storage_type_gluster']

    @classmethod
    def setup_class(cls):
        logger.warning("Gluster test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        # super(TestUpgradePosix, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        logger.warning("Gluster test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        # super(TestUpgradePosix, cls).teardown_class()


class TestUpgradeFCP(TestUpgrade):
    """
    Building FCP data center
    """
    storage_type = config.ENUMS['storage_type_fcp']

    @classmethod
    def setup_class(cls):
        raise NotImplementedError("FCP test hasn't been implemented yet")
        # uncomment it when you implement fcp tests
        # super(TestUpgradeFCP, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        raise NotImplementedError("FCP test hasn't been implemented yet")
        # uncomment it when you implement fcp tests
        # super(TestUpgradeFCP, cls).teardown_class()


# dict to map storage type to storage class to use
TYPE_TO_CLASS = {
    config.ENUMS['storage_type_nfs']: TestUpgradeNFS,
    config.ENUMS['storage_type_iscsi']: TestUpgradeISCSI,
    config.ENUMS['storage_type_local']: TestUpgradeLocal,
    config.ENUMS['storage_type_fcp']: TestUpgradeFCP,
    config.ENUMS['storage_type_posixfs']: TestUpgradePosix,
    config.ENUMS['storage_type_gluster']: TestUpgradeGluster,
}

storage_v3_format = config.ENUMS['storage_format_version_v3']
for storage_type in config.STORAGE_SELECTOR:
    logger.debug("Generating TestUpgrade for storage type %s", storage_type)
    if storage_type == config.STORAGE_TYPE_GLUSTER:
        # TODO: Implement TestUpgradeGluster (3.3 and up)
        continue
    for dc_version in config.DC_VERSIONS:
        dc_version_name = dc_version.replace('.', '')
        for dc_upgrade_version in config.DC_UPGRADE_VERSIONS:
            if dc_version == dc_upgrade_version:
                continue
            dc_upgrade_version_name = dc_upgrade_version.replace('.', '')
            storage_format = None
            if storage_type == config.ENUMS['storage_type_iscsi']:
                storage_format = config.ENUMS['storage_format_version_v2']
            elif storage_type == config.ENUMS['storage_type_nfs']:
                storage_format = config.ENUMS['storage_format_version_v1']
            elif storage_type == config.ENUMS['storage_type_gluster']:
                storage_format = config.ENUMS['storage_format_version_v1']

            name_pattern = (storage_type, dc_version_name,
                            dc_upgrade_version_name)
            class_name = "TestUpgrade%s%s%s" % name_pattern
            doc = ("Test case upgrades %s datacenter from %s to %s"
                   % name_pattern)
            class_attrs = {
                '__doc__': doc,
                '__test__': True,
                'dc_name': 'dc_%s_upgrade_%s_%s' % name_pattern,
                'cluster_name': 'c_%s_upgrade_%s_%s' % name_pattern,
                'sd_name_pattern': "%s%%d_%s_%s" % name_pattern,
                'dc_version': dc_version,
                'dc_upgraded_version': dc_upgrade_version,
                'storage_format': storage_format,
                'upgraded_storage_format': storage_v3_format,
                'storages': set([storage_type]),
            }
            new_class = type(class_name, (TYPE_TO_CLASS[storage_type],),
                             class_attrs)
            setattr(__THIS_MODULE, class_name, new_class)
    delattr(__THIS_MODULE, 'new_class')
