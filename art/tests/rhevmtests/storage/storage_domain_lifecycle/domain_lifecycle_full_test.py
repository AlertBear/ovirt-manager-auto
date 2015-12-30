import logging
from sys import modules

import config
from art.rhevm_api.tests_lib.high_level import (
    datacenters as hl_dc,
    hosts as hl_hosts,
    storagedomains as hl_sd,
)
from art.rhevm_api.tests_lib.low_level import (
    clusters as ll_clusters,
    datacenters as ll_dc,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    vms as ll_vms,
)
from art.rhevm_api.utils import iptables, storage_api, test_utils

from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, StorageTest as TestCase

from rhevmtests.storage import helpers as storage_helpers
from utilities.utils import getIpAddressByHostName


logger = logging.getLogger(__name__)
ENUMS = config.ENUMS

__THIS_MODULE = modules[__name__]

DC_API = test_utils.get_api('data_center', 'datacenters')
HOST_API = test_utils.get_api('host', 'hosts')
VM_API = test_utils.get_api('vm', 'vms')
SD_API = test_utils.get_api('storage_domain', 'storagedomains')
CLUSTER_API = test_utils.get_api('cluster', 'clusters')
CLI_CMD_DF = 'df -H'
DATA_CENTER_TIMEOUT = 60 * 5
ISCSI = config.STORAGE_TYPE_ISCSI
GLUSTER = config.STORAGE_TYPE_GLUSTER
NFS = config.STORAGE_TYPE_NFS
HOST_TO_USE = None

vm_args = {
    'positive': True,
    'vmName': None,
    'vmDescription': None,
    'cluster': config.CLUSTER_NAME,
    'nicType': config.NIC_TYPE_VIRTIO,
    'size': config.DISK_SIZE,
    'diskInterface': config.INTERFACE_VIRTIO,
    'volumeFormat': config.DISK_FORMAT_COW,
    'storageDomainName': None,
    'volumeType': True,  # sparse
    'bootable': True,
    'type': config.VM_TYPE_DESKTOP,
    'os_type': config.OS_TYPE,
    'memory': config.GB,
    'cpu_socket': config.CPU_SOCKET,
    'cpu_cores': config.CPU_CORES,
    'display_type': config.DISPLAY_TYPE,
    'start': True,
    'installation': True,
    'user': config.COBBLER_USER,
    'password': config.COBBLER_PASSWD,
    'image': config.COBBLER_PROFILE,
    'network': config.MGMT_BRIDGE,
    'useAgent': config.USE_AGENT,
}


def setup_module():
    """
    Setup the domain related information for all storage domain types
    """
    # Select the first non-SPM host, it will be moved to a new DC/Cluster setup
    global HOST_TO_USE
    status, hsm_host = ll_hosts.getAnyNonSPMHost(
        config.HOSTS, cluster_name=config.CLUSTER_NAME
    )
    if not status:
        raise exceptions.HostException(
            "Failed tp retrieve a non-SPM host on cluster '%s'" %
            config.CLUSTER_NAME
        )
    HOST_TO_USE = hsm_host['hsmHost']

    config.LIFECYCLE_ADDRESS = config.UNUSED_DATA_DOMAIN_ADDRESSES
    config.LIFECYCLE_PATH = config.UNUSED_DATA_DOMAIN_PATHS
    config.GLUSTER_LIFECYCLE_ADDRESS = (
        config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES
    )
    config.GLUSTER_LIFECYCLE_PATH = (
        config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS
    )
    config.LIFECYCLE_LUNS = config.UNUSED_LUNS
    config.LIFECYCLE_LUN_ADDRESS = config.UNUSED_LUN_ADDRESSES
    config.LIFECYCLE_LUN_TARGET = config.UNUSED_LUN_TARGETS


class BaseTestCase(TestCase):
    """
    Implement the common setup for this feature
    """
    __test__ = False
    polarion_test_case = None
    master_domain_ip = None
    engine_ip = None

    @classmethod
    def setup_class(cls):
        """
        Ensures that environment is ready for tests, validating that master
        domain is found and has an IP address, retrieves the IP address of
        the engine and the first host found under the second cluster
        """
        logger.info("DC name is: '%s'", config.DATA_CENTER_NAME)
        found, master_domain = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        if not found:
            raise exceptions.StorageDomainException(
                "Could not find master storage domain on Data center '%s'" %
                config.DATA_CENTER_NAME
            )
        master_domain = master_domain['masterDomain']
        logger.info("Master domain found : %s", master_domain)

        found, cls.master_domain_ip = ll_sd.getDomainAddress(
            True, master_domain
        )
        if not found:
            raise exceptions.StorageDomainException(
                "Could not find the IP address for the master storage domain "
                "host '%s'" % master_domain
            )
        cls.master_domain_ip = cls.master_domain_ip['address']
        logger.info("Master domain ip found : %s", cls.master_domain_ip)

        cls.engine_ip = getIpAddressByHostName(config.VDC)
        cls.first_host_ip = ll_hosts.getHostIP(HOST_TO_USE)


class CommonCase(TestCase):
    """
    Common setup and teardown functions used with the majority of the tests
    """
    def setUp(self):
        """
        Sets up storage parameters
        """
        self.sd_names = ["%s_%s_%s" % (self.storage, config.TESTNAME, idx) for
                         idx in range(config.EXTRA_SD_INDEX)][1:]
        self.sd_addresses = config.LIFECYCLE_ADDRESS[1:]
        self.sd_paths = config.LIFECYCLE_PATH[1:]

    def tearDown(self):
        """
        Remove storage domains
        """
        logger.info(
            "Waiting for tasks before deactivating/removing the storage domain"
        )
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        logger.info("Removing storage domains")
        if not ll_sd.removeStorageDomains(True, self.sd_names, HOST_TO_USE):
            TestCase.test_failed = True
            logger.error(
                "Failed to remove storage domains '%s'", self.sd_names
            )
        # The teardown_exception is called from the child class that uses
        # this function


def _create_sds(sd_type, host):
    """
    Helper function for creating two storage domains
    Return: False if not all the storage domains were created,
            True otherwise
    """
    status = True
    sd_args = {
        'type': config.TYPE_DATA,
        'storage_type': sd_type,
        'host': host
    }
    for index in range(1, config.EXTRA_SD_INDEX):
        sd_args['name'] = "%s_%s_%s" % (sd_type, config.TESTNAME, index)
        if sd_type == ISCSI:
            sd_args['lun'] = config.LIFECYCLE_LUNS[index]
            sd_args['lun_address'] = config.LIFECYCLE_LUN_ADDRESS[index]
            sd_args['lun_target'] = config.LIFECYCLE_LUN_TARGET[index]
            sd_args['lun_port'] = config.LUN_PORT
            sd_args['override_luns'] = True
        elif sd_type == NFS:
            sd_args['address'] = config.LIFECYCLE_ADDRESS[index]
            sd_args['path'] = config.LIFECYCLE_PATH[index]
        elif sd_type == GLUSTER:
            sd_args['address'] = config.GLUSTER_LIFECYCLE_ADDRESS[index]
            sd_args['path'] = config.GLUSTER_LIFECYCLE_PATH[index]
            sd_args['vfs_type'] = ENUMS['vfs_type_glusterfs']

        logger.info("Creating storage domain with parameters: %s", sd_args)
        status = ll_sd.addStorageDomain(True, **sd_args) and status

    return status


@attr(tier=4)
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
        assert iptables.block_and_wait(
            self.engine_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.first_host_ip, HOST_TO_USE, config.HOST_NONRESPONSIVE
        )

        assert iptables.unblock_and_wait(
            self.engine_ip, config.HOSTS_USER, config.HOSTS_PW,
            self.first_host_ip, HOST_TO_USE
        )

    @classmethod
    def teardown_class(cls):
        """
        Unblock all connections that were blocked during the test
        """
        def check_dc_and_host_state():
            """ Checks whether DC and host used are available"""
            return (
                ll_dc.waitForDataCenterState(
                    config.DATA_CENTER_NAME, timeout=DATA_CENTER_TIMEOUT
                ) and ll_hosts.isHostUp(True, HOST_TO_USE)
            )

        if not check_dc_and_host_state():
            logger.info("Unblocking connections, something went wrong")
            try:
                storage_api.unblockOutgoingConnection(
                    cls.engine_ip, config.HOSTS_USER, config.HOSTS_PW,
                    cls.first_host_ip
                )
            except exceptions.NetworkException, msg:
                logging.info("Connection already unblocked. Reason: %s", msg)

        if not check_dc_and_host_state():
            cls.test_failed = True
            logger.error(
                "Could not successfully restore the Data center state and "
                "host within the timeout period"
            )

        cls.teardown_exception()


@attr(tier=2)
class TestCase4817(CommonCase):
    """
    Test check if creating storage domains with defined values is working
    properly

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '4817'
    nfs_retrans = 5
    nfs_timeout = 10
    nfs_version = 'v3'
    mount_options = 'sync'

    @polarion("RHEVM3-4817")
    def test_create_sd_with_defined_values(self):
        """
        Check if creating an NFS storage domain with predefined values works
        """
        version = None
        mount_options = None
        for sd_name, sd_address, sd_path in zip(
            self.sd_names, self.sd_addresses, self.sd_paths
        ):
            logger.info(
                "Creating storage domain #%s with values: "
                "retrans = %d, timeout = %d, vers = %s",
                sd_name, self.nfs_retrans, self.nfs_timeout, version
            )

            storage = ll_sd.NFSStorage(
                name=sd_name,
                address=sd_address,
                path=sd_path,
                timeout_to_set=self.nfs_timeout,
                retrans_to_set=self.nfs_retrans,
                mount_options_to_set=mount_options,
                vers_to_set=version,
                expected_timeout=self.nfs_timeout,
                expected_retrans=self.nfs_retrans,
                expected_vers=version,
                expected_mount_options=mount_options,
                sd_type=config.TYPE_DATA
            )

            if not ll_hosts.isHostUp(True, HOST_TO_USE):
                ll_hosts.activateHost(True, HOST_TO_USE)

            hl_sd.create_nfs_domain_and_verify_options(
                [storage], host=HOST_TO_USE, password=config.HOSTS_PW,
                datacenter=config.DATA_CENTER_NAME
            )

            version = self.nfs_version
            mount_options = self.mount_options

    def tearDown(self):
        """
        Remove storage domains
        """
        super(TestCase4817, self).tearDown()

        host_ip = ll_hosts.getHostIP(HOST_TO_USE)
        logger.info("Getting info about mounted resources")
        mounted_resources = ll_sd.get_mounted_nfs_resources(
            host=host_ip, password=config.HOSTS_PW
        )

        for sd_address, sd_path in zip(self.sd_addresses, self.sd_paths):
            if (sd_address, sd_path) in mounted_resources.keys():
                TestCase.test_failed = True
                logger.error(
                    "Mount of %s:%s was found on %s, although SD was removed",
                    sd_address, sd_path, HOST_TO_USE
                )

        self.teardown_exception()


@attr(tier=2)
class TestCase4815(CommonCase):
    """
    Ensure that incorrect and conflicting parameters for creating a storage
    domain are blocked

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])

    polarion_test_case = '4815'

    sds_params = list()
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

    @polarion("RHEVM3-4815")
    def test_create_sd_with_defined_values(self):
        """
        test check if bad and conflict parameters for creating storage
        domain are blocked
        """
        for sd_params in self.sds_params:
            logger.info(
                "creating storage domain with values: "
                "retrans = %s, timeout = %d, vers = %s, mount_optiones = %s",
                sd_params['nfs_retrans'], sd_params['nfs_timeout'],
                sd_params['nfs_version'], sd_params['mount_options']
            )

            storage = ll_sd.NFSStorage(
                name=self.sd_names[1],
                address=self.sd_addresses[1],
                path=self.sd_paths[1],
                timeout_to_set=sd_params['nfs_timeout'],
                retrans_to_set=sd_params['nfs_retrans'],
                mount_options_to_set=sd_params['mount_options'],
                vers_to_set=sd_params['nfs_version'],
                expected_timeout=sd_params['nfs_timeout'],
                expected_retrans=sd_params['nfs_retrans'],
                expected_vers=sd_params['nfs_version'],
                sd_type=config.TYPE_DATA
            )

            if not ll_hosts.isHostUp(True, HOST_TO_USE):
                ll_hosts.activateHost(True, HOST_TO_USE)

            logger.info(
                "Attempt to create domain %s with wrong params ", storage.name
            )
            hl_sd.create_nfs_domain_with_options(
                name=storage.name, sd_type=storage.sd_type,
                host=HOST_TO_USE, address=storage.address,
                path=storage.path, version=storage.vers_to_set,
                retrans=storage.retrans_to_set, timeo=storage.timeout_to_set,
                mount_options=storage.mount_options_to_set,
                datacenter=config.DATA_CENTER_NAME, positive=False
            )

    def tearDown(self):
        """
        Removes Storage domains
        """
        super(TestCase4815, self).tearDown()
        self.teardown_exception()


@attr(tier=2)
class TestCase11581(CommonCase):
    """
    Ensure that creating disks of different types works with a guest OS across
    different storage domains

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Sanity
    """
    __test__ = True
    polarion_test_case = '11581'
    interface = config.VIRTIO
    formats = [config.COW_DISK, config.RAW_DISK]
    num_of_disks = 2

    @classmethod
    def setup_class(cls):
        """
        Create a VM to use within the tests
        """
        cls.first_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, cls.storage
        )[0]
        logger.info("Creating vm and installing OS on it")
        create_vm_args = vm_args.copy()
        create_vm_args['vmName'] = config.LIFECYCLE_VM
        create_vm_args['vmDescription'] = config.LIFECYCLE_VM
        create_vm_args['diskInterface'] = config.INTERFACE_VIRTIO_SCSI
        create_vm_args['storageDomainName'] = cls.first_domain
        if not storage_helpers.create_vm_or_clone(**create_vm_args):
            raise exceptions.VMException(
                "Failed to create VM '%s'" % config.LIFECYCLE_VM
            )

        logger.info("Shutting down VM '%s'", config.LIFECYCLE_VM)
        if not ll_vms.stopVm(True, config.LIFECYCLE_VM):
            raise exceptions.VMException(
                "Failed to shutdown VM '%s'" % config.LIFECYCLE_VM
            )

    def setUp(self):
        """
        Configure storage parameters
        """
        super(TestCase11581, self).setUp()

        logger.info("Creating a pair of storage domains")
        self.assertTrue(
            _create_sds(self.storage, HOST_TO_USE),
            "Failed to create Storage domains"
        )

        for sd in self.sd_names:
            self.assertTrue(
                ll_sd.attachStorageDomain(True, config.DATA_CENTER_NAME, sd),
                "Failed to attach storage domain '%s'" % sd
            )

    @polarion("RHEVM3-11581")
    def test_multiple_disks_on_different_sd(self):
        """
        creates disks on different SD
        """
        logger.info("Adding new disks")
        for sd in self.sd_names:
            for index in range(self.num_of_disks):
                logger.info(
                    "Add new disk - format %s, interface %s",
                    self.formats[index], self.interface
                )
                if self.formats[index] == config.RAW_DISK:
                    policy_allocation = False
                else:
                    # policy_allocation = True --> sparse
                    policy_allocation = True
                self.assertTrue(
                    ll_vms.addDisk(
                        True, config.LIFECYCLE_VM, config.GB, True, sd,
                        type=ENUMS['disk_type_data'],
                        interface=self.interface,
                        format=self.formats[index], sparse=policy_allocation
                    ), "Failed to add disk"
                )

        self.assertTrue(
            ll_vms.startVm(True, config.LIFECYCLE_VM),
            "Failed to start vm %s" % config.LIFECYCLE_VM
        )

        self.assertTrue(
            ll_vms.stopVm(True, config.LIFECYCLE_VM),
            "Failed to stop vm %s" % config.LIFECYCLE_VM
        )

    def tearDown(self):
        """
        Removes storage domains created in test case
        """
        super(TestCase11581, self).tearDown()
        self.teardown_exception()

    @classmethod
    def teardown_class(cls):
        """
        Remove VM created for the test case
        """
        logger.info("Removing vm %s", config.LIFECYCLE_VM)
        if not ll_vms.safely_remove_vms([config.LIFECYCLE_VM]):
            cls.test_failed = True
            logger.error("Failed to remove vm %s" % config.LIFECYCLE_VM)

        cls.teardown_exception()


@attr(tier=2)
class TestCase11784(CommonCase):
    """
    Starting version 3.3 attaching domains should activate them automatically.
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_Multiple_Storage_Domains_General
    """
    __test__ = True
    polarion_test_case = '11784'

    def setUp(self):
        """
        Sets up storage parameters
        """
        super(TestCase11784, self).setUp()

        logger.info("Creating a pair of storage domains")
        self.assertTrue(
            _create_sds(self.storage, HOST_TO_USE),
            "Failed to create Storage domains"
        )

    @polarion("RHEVM3-11784")
    def test_add_another_storage_domain_test(self):
        """
        Check that both storage domains were automatically activated
        after attaching them
        """
        for sd in self.sd_names:
            self.assertTrue(
                ll_sd.attachStorageDomain(True, config.DATA_CENTER_NAME, sd),
                "Failed to attach SD %s" % sd
            )
            self.assertTrue(
                ll_sd.is_storage_domain_active(config.DATA_CENTER_NAME, sd)
            )

    def tearDown(self):
        """
        Removes storage domains created for this test
        """
        super(TestCase11784, self).tearDown()
        self.teardown_exception()


@attr(tier=2)
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
    cluster_version = config.COMPATIBILITY_VERSION
    host = None
    vm_name = 'TestUpgrade_vm_test'
    domain_kw = None
    polarion_test_case = '11743'

    @classmethod
    def setup_class(cls):
        """
        Prepares Data center without storage
        """
        logger.info("Running class %s setup", cls.__name__)
        if cls.storage == NFS:
            cls.sd_paths = config.LIFECYCLE_PATH[1:]
            cls.sd_address = config.LIFECYCLE_ADDRESS[1:]
        elif cls.storage == GLUSTER:
            cls.sd_paths = config.GLUSTER_LIFECYCLE_PATH[1:]
            cls.sd_address = config.GLUSTER_LIFECYCLE_ADDRESS[1:]
        else:
            cls.sd_luns = config.LIFECYCLE_LUNS[1:]
            cls.sd_luns_address = config.LIFECYCLE_LUN_ADDRESS[1:]
            cls.sd_luns_target = config.LIFECYCLE_LUN_TARGET[1:]

        cls.host = HOST_TO_USE
        cls.host_ip = ll_hosts.getHostIP(cls.host)

        logger.info(
            "Retrieve the first host from the 2nd cluster (in original Data "
            "center)"
        )
        if not ll_dc.addDataCenter(
            True, name=cls.dc_name, storage_type=cls.storage_type,
            version=cls.dc_version
        ):
            raise exceptions.DataCenterException(
                "Failed to create Data center '%s'" % cls.dc_name
            )

        if not ll_clusters.addCluster(
            True, name=cls.cluster_name, cpu=config.PARAMETERS['cpu_name'],
            data_center=cls.dc_name, version=cls.cluster_version
        ):
            raise exceptions.ClusterException(
                "Failed to create Cluster '%s'" % cls.cluster_name
            )

        logger.info("Move the host into the newly created cluster")
        if not hl_hosts.move_host_to_another_cluster(
            cls.host, cls.cluster_name
        ):
            raise exceptions.ClusterException(
                "Could not move host '%s' into cluster '%s'" % (
                    cls.host, cls.cluster_name
                )
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove Data Center, cluster, storage domains and migrates hosts to a
        temporary cluster
        """
        logger.info("Running class %s teardown", cls.__name__)
        logger.info("Remove vm %s", cls.vm_name)
        ll_vms.safely_remove_vms([cls.vm_name])

        status = hl_dc.clean_datacenter(
            True, cls.dc_name, formatExpStorage='true', vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )
        if not status:
            cls.test_failed = True
            logger.error(
                "Failed to clean Data center '%s'", cls.dc_name
            )

        logger.info(
            "Re-add the moved host back into its original cluster/data center"
        )
        if not ll_hosts.addHost(
            True, cls.host, address=cls.host_ip, wait=True, reboot=False,
            cluster=config.CLUSTER_NAME, root_password=config.VDC_ROOT_PASSWORD
        ):
            cls.test_failed = True
            logger.error(
                "Could not add host '%s' back into cluster '%s'",
                cls.host, config.CLUSTER_NAME
            )

        cls.teardown_exception()
        logger.info("Class %s teardown finished", cls.__name__)

    @polarion("RHEVM3-11743")
    def test_data_center_upgrade(self):
        """
        Changes DC version while installing a VM
        """
        create_vm_args = vm_args.copy()
        create_vm_args['vmName'] = self.vm_name
        create_vm_args['vmDescription'] = self.vm_name
        create_vm_args['cluster'] = self.cluster_name
        create_vm_args['storageDomainName'] = self.sd_name_pattern % 0
        assert storage_helpers.create_vm_or_clone(**create_vm_args)

        logger.info(
            "Upgrading Data Center %s from version %s to version %s ",
            self.dc_name, self.dc_version, self.dc_upgraded_version
        )
        ll_dc.updateDataCenter(
            True, datacenter=self.dc_name, version=self.dc_upgraded_version
        )
        sds = ll_sd.getDCStorages(self.dc_name, get_href=False)
        for sd_obj in sds:
            was_upgraded = ll_sd.checkStorageFormatVersion(
                True, sd_obj.name, self.upgraded_storage_format
            )
            logger.info(
                "Checking that %s was upgraded: %s", sd_obj.name, was_upgraded
            )
            self.assertTrue(was_upgraded)


class TestUpgradeNFS(TestUpgrade):
    """
    Building NFS data center
    """
    storage_type = NFS
    domain_kw = 'data_domain_address'

    @classmethod
    def setup_class(cls):
        """
        Create NFS storage domains for upgrade tests
        """
        super(TestUpgradeNFS, cls).setup_class()
        logger.info("Adding NFS storage domains needed for tests")
        logger.info("Addresses: %s, Paths: %s", cls.sd_address, cls.sd_paths)
        for index, (address, path) in enumerate(
            zip(cls.sd_address, cls.sd_paths)
        ):
            if not hl_sd.addNFSDomain(
                cls.host, cls.sd_name_pattern % index, cls.dc_name, address,
                path, storage_format=cls.storage_format
            ):
                raise exceptions.StorageDomainException(
                    "Failed to create NFS Storage domain '%s'" %
                    cls.sd_name_pattern % index
                )
            logger.info(
                "NFS storage domain %s was created successfully",
                cls.sd_name_pattern % index
            )


class TestUpgradeISCSI(TestUpgrade):
    """
    Building iSCSI data center
    """
    storage_type = ISCSI
    domain_kw = 'lun'

    @classmethod
    def setup_class(cls):
        """
        Create iSCSI storage domains for upgrade tests
        """
        super(TestUpgradeISCSI, cls).setup_class()
        for index, (lun_address, lun_target, lun) in enumerate(
            zip(cls.sd_luns_address, cls.sd_luns_target, cls.sd_luns)
        ):
            if not hl_sd.addISCSIDataDomain(
                cls.host, cls.sd_name_pattern % index, cls.dc_name, lun,
                lun_address, lun_target, storage_format=cls.storage_format,
                override_luns=True
            ):
                raise exceptions.StorageDomainException(
                    "Failed to create iSCSI Storage domain '%s'" %
                    cls.sd_name_pattern % index
                )
            logger.info(
                "iSCSI storage domains %s were created successfully",
                cls.sd_name_pattern % index
            )


class TestUpgradeLocal(TestUpgrade):
    """
    Building local data center
    """
    storage_type = config.STORAGE_TYPE_LOCAL

    @classmethod
    def setup_class(cls):
        """ Local file storage setup """
        raise NotImplementedError("Local test hasn't been implemented yet")
        # uncomment it when you implement localfs tests
        # super(TestUpgradeLocal, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """ Local file storage teardown """
        raise NotImplementedError("Local test hasn't been implemented yet")
        # uncomment it when you implement localfs tests
        # super(TestUpgradeLocal, cls).teardown_class()


class TestUpgradePosix(TestUpgrade):
    """
    Building posixfs data center
    """
    storage_type = config.STORAGE_TYPE_POSIX

    @classmethod
    def setup_class(cls):
        """ POSIX file storage setup """
        raise NotImplementedError("Posix test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        # super(TestUpgradePosix, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """ POSIX file storage teardown """
        raise NotImplementedError("Posix test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        # super(TestUpgradePosix, cls).teardown_class()


class TestUpgradeGluster(TestUpgrade):
    """
    Building glusterfs data center
    """
    storage_type = GLUSTER

    @classmethod
    def setup_class(cls):
        """ Gluster file storage setup """
        logger.warning("Gluster test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        # super(TestUpgradePosix, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """ Gluster file storage teardown """
        logger.warning("Gluster test hasn't been implemented yet")
        # uncomment it when you implement posix tests
        # super(TestUpgradePosix, cls).teardown_class()


class TestUpgradeFCP(TestUpgrade):
    """
    Building FCP data center
    """
    storage_type = config.STORAGE_TYPE_FCP

    @classmethod
    def setup_class(cls):
        """ Fiber Channel file storage setup """
        raise NotImplementedError("FCP test hasn't been implemented yet")
        # uncomment it when you implement fcp tests
        # super(TestUpgradeFCP, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """ Fiber Channel file storage setup """
        raise NotImplementedError("FCP test hasn't been implemented yet")
        # uncomment it when you implement fcp tests
        # super(TestUpgradeFCP, cls).teardown_class()


# dict to map storage type to storage class to use
TYPE_TO_CLASS = {
    NFS: TestUpgradeNFS,
    ISCSI: TestUpgradeISCSI,
    config.STORAGE_TYPE_LOCAL: TestUpgradeLocal,
    config.STORAGE_TYPE_FCP: TestUpgradeFCP,
    config.STORAGE_TYPE_POSIX: TestUpgradePosix,
    GLUSTER: TestUpgradeGluster,
}

storage_v3_format = ENUMS['storage_format_version_v3']
for storage_type in config.STORAGE_SELECTOR:
    logger.debug("Generating TestUpgrade for storage type %s", storage_type)
    if storage_type == GLUSTER:
        # TODO: Implement TestUpgradeGluster (3.3 and up)
        continue
    for dc_version in config.DC_VERSIONS:
        dc_version_name = dc_version.replace('.', '')
        for dc_upgrade_version in config.DC_UPGRADE_VERSIONS:
            if dc_version == dc_upgrade_version:
                continue
            dc_upgrade_version_name = dc_upgrade_version.replace('.', '')
            storage_format = None
            if storage_type == ISCSI:
                storage_format = ENUMS['storage_format_version_v2']
            elif storage_type == NFS:
                storage_format = ENUMS['storage_format_version_v1']
            elif storage_type == GLUSTER:
                storage_format = ENUMS['storage_format_version_v1']

            name_pattern = (
                storage_type, dc_version_name, dc_upgrade_version_name
            )
            class_name = "TestUpgrade%s%s%s" % name_pattern
            doc = (
                "Test case upgrades %s Data Center from %s to %s" %
                name_pattern
            )
            class_attrs = {
                '__doc__': doc,
                '__test__': True,
                'dc_name': 'dc_%s_upgrade_%s_%s' % name_pattern,
                'cluster_name': 'cluster_%s_upgrade_%s_%s' % name_pattern,
                'sd_name_pattern': "sd_%s_%%d_%s_%s" % name_pattern,
                'dc_version': dc_version,
                'dc_upgraded_version': dc_upgrade_version,
                'storage_format': storage_format,
                'upgraded_storage_format': storage_v3_format,
                'storages': set([storage_type]),
            }
            new_class = type(
                class_name, (TYPE_TO_CLASS[storage_type],), class_attrs
            )
            setattr(__THIS_MODULE, class_name, new_class)
    delattr(__THIS_MODULE, 'new_class')
