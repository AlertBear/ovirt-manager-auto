"""
Reconstruct master test - 2461
https://tcms.engineering.redhat.com/plan/2461
"""
import config
import logging
from art.unittest_lib import StorageTest as TestCase
from art.rhevm_api.tests_lib.low_level import clusters
from art.rhevm_api.tests_lib.low_level import datacenters
from art.rhevm_api.tests_lib.low_level import hosts
from art.rhevm_api.tests_lib.low_level import storagedomains
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.high_level.storagedomains import (
    addISCSIDataDomain, addNFSDomain,
)
from art.rhevm_api.utils.test_utils import (
    get_api, restartVdsmd, validateElementStatus, stopVdsmd, startVdsmd,
    wait_for_tasks,
)
from art.rhevm_api.utils.storage_api import (
    generateSDMetadataCorruption, restoreSDOriginalMetadata,
    blockOutgoingConnection, unblockOutgoingConnection,
)
from art.test_handler.settings import plmanager
from art.test_handler.tools import tcms  # pylint: disable=E0611

# Automatic setup and teardown on failure
automatic_rebuild = True

try:
    BZ_PLUGIN = [pl for pl in plmanager.configurables
                 if pl.name == "Bugzilla"][0]
    BZ_854140_NOT_FIXED = not BZ_PLUGIN.is_state('854140')
    BZ_958044_FIXED = BZ_PLUGIN.is_state('958044')
    BZ_967749_FIXED = BZ_PLUGIN.is_state('967749')
except IndexError:
    BZ_854140_NOT_FIXED = False
    BZ_958044_FIXED = True
    BZ_967749_FIXED = True

LOGGER = logging.getLogger(__name__)

DC_API = get_api('data_center', 'datacenters')
HOST_API = get_api('host', 'hosts')
SD_API = get_api('storage_domain', 'storagedomains')
VM_API = get_api('vm', 'vms')

GB = 1024 ** 3
MINUTE = 60
DC_PROBLEM_TIMEOUT = 600

MASTER_DOMAIN = "master_domain"
STORAGE_DOMAINS = list()

IS_ISCSI_TEST = config.STORAGE_TYPE == config.ENUMS['storage_type_iscsi']


def handle_bz_854140(dc_name, domain_name, result):
    """
    Description: Sometimes due to BZ 854140 storage domain needs to be
                 activated twice due to race. This activates the storage domain
                 for the second time if BZ is still open.
    Parameters:
        * dc_name -
        * domain_name - Name of storage domain that needs to be activated
    """
    if not result and BZ_854140_NOT_FIXED:
        LOGGER.info("There is BZ 854140, we need to activate the master "
                    "domain again.")
        return storagedomains.activateStorageDomain(
            True, datacenter=dc_name, storagedomain=domain_name)
    return True


def _raise_if_exception(results):
    """
    Raises exception if any of Future object in results has exception
    """
    for result in results:
        if result.exception():
            LOGGER.error(result.exception())
            raise result.exception()


def get_host_for_run(host_type):
    """
    Description: switch for host type
    Parameters:
        * host_type - type of the host (spm or hsm)
    Returns: name of the host for placement host
    """
    hosts_ = config.PARAMETERS.as_list('vds')
    spm_host = hosts.getSPMHost(hosts_)
    if host_type == 'spm':
        return spm_host
    elif host_type == 'hsm' and len(hosts_) > 1:
        return [host for host in hosts_ if host != spm_host][0]


def create_installing_vm(vm_name):
    """
    Description: Creates a new vm and starts installation
    Parameters:
        * vm_name - Name of the vm
    """
    LOGGER.info("Starting vm %s installation", vm_name)
    vm_args = {
        'positive': True,
        'vmDescription': '',
        'cluster': config.CLUSTER_NAME,
        'nic': config.NIC_NAME[0],
        'nicType': config.ENUMS['nic_type_virtio'],
        'storageDomainName': MASTER_DOMAIN,
        'size': 5 * GB,
        'bootable': True,
        'type': config.ENUMS['vm_type_server'],
        'os_type': "rhel6x64",
        'memory': GB,
        'cpu_socket': 1,
        'cpu_cores': 1,
        'display_type': config.ENUMS['display_type_spice'],
        'start': 'true',
        'installation': False,
        'network': config.PARAMETERS['mgmt_bridge'],
        'vmName': vm_name,
        'volumeFormat': config.ENUMS['format_cow'],
        'diskInterface': config.ENUMS['interface_virtio'],
        'volumeType': True,  # sparse volume
    }
    assert vms.createVm(**vm_args)


def setup_iscsi():
    """
    Setup iscsi module

    Adds one storage domain to datacenter and creates two unattached iSCSI data
    domains
    """
    host = config.PARAMETERS.as_list('vds')[0]
    LOGGER.info("Creating iSCSI master storage domain %s", MASTER_DOMAIN)
    assert addISCSIDataDomain(
        host,
        MASTER_DOMAIN,
        config.DATA_CENTER_NAME,
        config.PARAMETERS['master_lun'],
        config.PARAMETERS['master_lun_address'],
        config.PARAMETERS['master_lun_target'],
        override_luns=True
    )
    addresses_list = config.PARAMETERS.as_list('lun_address')
    targets_list = config.PARAMETERS.as_list('lun_target')
    for index, lun in enumerate(config.PARAMETERS.as_list('lun')):
        sd_name = "%s_%d" % (lun, index)
        STORAGE_DOMAINS.append(sd_name)
        LOGGER.info("Creating iscsi storage domain %s, %s, %s",
                    addresses_list[index], targets_list[index], lun)
        assert storagedomains.addStorageDomain(
            True, name=sd_name, type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.ENUMS['storage_type_iscsi'],
            host=host, lun=lun, lun_address=addresses_list[index],
            lun_target=targets_list[index], lun_port=3260)


def setup_nfs():
    """
    Setup nfs module

    Adds one storage domain to datacenter and creates two unattached NFS data
    domains
    """
    host = config.PARAMETERS.as_list('vds')[0]
    LOGGER.info("Creating NFS master storage domain %s", MASTER_DOMAIN)
    assert addNFSDomain(host, MASTER_DOMAIN, config.DATA_CENTER_NAME,
                        config.PARAMETERS['master_export_address'],
                        config.PARAMETERS['master_export_path'])
    address_list = config.PARAMETERS.as_list('data_domain_address')
    for index, path in \
            enumerate(config.PARAMETERS.as_list('data_domain_path')):
        sd_name = "nfs_%d" % index
        STORAGE_DOMAINS.append(sd_name)
        LOGGER.info("Creating nfs storage domain %s:%s", address_list[index],
                    path)
        assert storagedomains.addStorageDomain(
            True, name=sd_name, type=config.ENUMS['storage_dom_type_data'],
            storage_type=config.ENUMS['storage_type_nfs'],
            host=host, address=address_list[index], path=path)


def setup_module():
    """
    Prepares storage domains

    Creates datacenter and assigns the cluster that contains host,
    according to storage_domain type adds one storage domain to datacenter
    """
    host = config.PARAMETERS.as_list('vds')[0]
    LOGGER.info("Adding datacenter %s", config.DATA_CENTER_NAME)
    assert datacenters.addDataCenter(
        True, name=config.DATA_CENTER_NAME, storage_type=config.STORAGE_TYPE,
        version=config.PARAMETERS['compatibility_version'])
    LOGGER.info("Putting host to maintenance")
    assert hosts.deactivateHost(True, host)
    LOGGER.info("Assigning cluster %s to datacenter %s",
                config.CLUSTER_NAME, config.DATA_CENTER_NAME)
    assert clusters.updateCluster(
        True, cluster=config.CLUSTER_NAME, data_center=config.DATA_CENTER_NAME)
    LOGGER.info("Activating host")
    assert hosts.activateHost(True, host)
    if config.STORAGE_TYPE == config.ENUMS['storage_type_nfs']:
        setup_nfs()
    elif config.STORAGE_TYPE == config.ENUMS['storage_type_iscsi']:
        setup_iscsi()


def teardown_module():
    """
    Removes storage domains from data-center to unassigned and removes
    data-center
    """
    wait_for_tasks(config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME)
    LOGGER.info("Putting datacenter to maintenance")
    assert storagedomains.deactivateStorageDomain(
        True,
        config.DATA_CENTER_NAME,
        MASTER_DOMAIN
    )
    LOGGER.info("Removing datacenter")
    assert datacenters.removeDataCenter(True, config.DATA_CENTER_NAME)


class DataCenterWithSD(TestCase):
    """
    Datacenter with storage domains
    """
    __test__ = False
    automatic_rebuild = True
    host = config.HOSTS[0]
    password = config.HOSTS_PW
    master_domain = MASTER_DOMAIN
    non_master = None

    @classmethod
    def setup_class(cls):
        """
        Sets up the environment - creates vms with all disk types and formats
        """
        cls.non_master = STORAGE_DOMAINS[0]
        LOGGER.info("Attaching domain %s to datacenter %s", cls.non_master,
                    config.DATA_CENTER_NAME)
        assert storagedomains.attachStorageDomain(
            True,
            datacenter=config.DATA_CENTER_NAME,
            storagedomain=cls.non_master
        )
        assert storagedomains.activateStorageDomain(
            True,
            datacenter=config.DATA_CENTER_NAME,
            storagedomain=cls.non_master
        )
        cls.vm_name = "vm_%s" % cls.__name__
        create_installing_vm(cls.vm_name)

    @classmethod
    def teardown_class(cls):
        """
        Removes vm created in setup, deactivates and detaches non-master domain
        and leaves data-center with master domain only.
        """
        LOGGER.info("Removing vm %s", cls.vm_name)
        assert vms.removeVm(True, vm=cls.vm_name, stopVM='true')
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        non_master = storagedomains.getDCStorage(config.DATA_CENTER_NAME,
                                                 cls.non_master)
        if non_master.status.state == \
                config.ENUMS['storage_domain_state_active']:
            LOGGER.info("Deactivating storage domain %s", non_master.name)
            assert storagedomains.deactivateStorageDomain(
                True,
                config.DATA_CENTER_NAME,
                non_master.name
            )
        non_master = storagedomains.getDCStorage(
            config.DATA_CENTER_NAME,
            non_master.name
        )
        LOGGER.info("Detaching domain %s that is in %s status",
                    non_master.name, non_master.status.state)
        assert storagedomains.detachStorageDomain(
            True,
            config.DATA_CENTER_NAME,
            non_master.name
        )


class CorruptMetadata(DataCenterWithSD):
    """
    Trigger a corruption in the metadata, for example "echo 1 > metadata".
    """
    __test__ = IS_ISCSI_TEST or BZ_967749_FIXED
    tcms_plan_id = '2461'
    tcms_test_case = '87133'
    vm_name = None

    @tcms(tcms_plan_id, tcms_test_case)
    def test_metadata_corruption(self):
        """
        Makes metadata corruption, checks states of objects and restores
        metadata
        """
        LOGGER.info("Generating metadata corruption on domain %s",
                    self.master_domain)
        result, sd_obj = generateSDMetadataCorruption(
            vds_name=self.host, username=config.HOSTS_USER,
            passwd=self.password, sd_name=self.master_domain,
            md_tag=config.MASTER_VERSION_TAG, md_tag_bad_value='-1')
        LOGGER.info("sd_obj is %s", sd_obj)
        self.assertTrue(result)
        LOGGER.info("Waiting for data center recovery")
        self.assertTrue(datacenters.waitForDataCenterState(
            config.DATA_CENTER_NAME, config.ENUMS['data_center_state_contend'],
            timeout=DC_PROBLEM_TIMEOUT))
        LOGGER.info("Waiting until DC is recovered")
        self.assertTrue(
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME
            )
        )
        LOGGER.info("Waiting until old master domain %s becomes inactive",
                    self.master_domain)
        self.assertTrue(storagedomains.waitForStorageDomainStatus(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=self.master_domain,
            expectedStatus=config.ENUMS['storage_domain_state_inactive'],
            timeOut=1800))
        LOGGER.info("Checking that host %s is SPM", self.host)
        self.assertTrue(hosts.checkHostSpmStatus(True, self.host))
        LOGGER.info("Checking that domain %s is master domain",
                    self.non_master)
        self.assertTrue(storagedomains.isStorageDomainMaster(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=self.non_master))
        LOGGER.info("Validating up status of datacenter")
        self.assertTrue(validateElementStatus(
            True, element='data_center', collection='datacenters',
            elementName=config.DATA_CENTER_NAME,
            expectedStatus=config.ENUMS['data_center_state_up']))
        LOGGER.info("Validating that current master domain %s is active",
                    self.non_master)
        self.assertTrue(validateElementStatus(
            True, element='storagedomain',
            collection='storagedomains', elementName=self.non_master,
            expectedStatus=config.ENUMS['storage_domain_state_active'],
            dcName=config.DATA_CENTER_NAME))
        LOGGER.info("Trying to activate former master domain %s",
                    MASTER_DOMAIN)
        self.assertFalse(
            storagedomains.activateStorageDomain(
                True,
                datacenter=config.DATA_CENTER_NAME,
                storagedomain=MASTER_DOMAIN
            )
        )
        LOGGER.info("Restoring metadata on domain %s", MASTER_DOMAIN)
        restoreSDOriginalMetadata(sd_obj=sd_obj['sd_obj'])
        LOGGER.info("Activating former master %s", MASTER_DOMAIN)
        activate_result = storagedomains.activateStorageDomain(
            True,
            datacenter=config.DATA_CENTER_NAME,
            storagedomain=MASTER_DOMAIN
        )
        self.assertTrue(
            handle_bz_854140(
                config.DATA_CENTER_NAME,
                MASTER_DOMAIN,
                activate_result
            )
        )


class WrongMasterVersion(DataCenterWithSD):
    """
    Edit the master domain's metadata.
    Change the master version to another number.
    Delete the checksum.
    """
    __test__ = IS_ISCSI_TEST or BZ_967749_FIXED
    tcms_plan_id = '2461'
    tcms_test_case = '87245'
    vm_name = None

    @tcms(tcms_plan_id, tcms_test_case)
    def test_changed_master_version(self):
        """
        Changes master version, checks states and gets state back
        """
        LOGGER.info("Changing master version to 999")
        result, sd_obj = generateSDMetadataCorruption(
            vds_name=self.host, username=config.HOSTS_USER,
            passwd=self.password, sd_name=self.master_domain,
            md_tag=config.MASTER_VERSION_TAG, md_tag_bad_value='999')
        self.assertTrue(result)
        LOGGER.info("Waiting for inactive master storage")
        self.assertTrue(storagedomains.waitForStorageDomainStatus(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=self.master_domain,
            expectedStatus=config.ENUMS['storage_domain_state_inactive'],
            timeOut=DC_PROBLEM_TIMEOUT))
        LOGGER.info("Waiting for datacenter to come up")
        self.assertTrue(
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME
            )
        )
        LOGGER.info("Checking that host is spm")
        self.assertTrue(hosts.checkHostSpmStatus(True, self.host))
        LOGGER.info("Checking that another storage domain was selected as "
                    "master")
        self.assertTrue(storagedomains.isStorageDomainMaster(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=self.non_master))
        LOGGER.info("Validating former master storage domain is inactive")
        self.assertTrue(validateElementStatus(
            True, element='storagedomain',
            collection='storagedomains', elementName=self.master_domain,
            expectedStatus=config.ENUMS['storage_domain_state_inactive'],
            dcName=config.DATA_CENTER_NAME))
        LOGGER.info("Waiting for current master to come up")
        self.assertTrue(storagedomains.waitForStorageDomainStatus(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=self.non_master,
            expectedStatus=config.ENUMS['storage_domain_state_active'],
            timeOut=60))
        LOGGER.info("Activating former master - should fail")
        self.assertFalse(storagedomains.activateStorageDomain(
            True, datacenter=config.DATA_CENTER_NAME,
            storagedomain=self.master_domain))
        LOGGER.info("Restoring original metadata")
        restoreSDOriginalMetadata(sd_obj=sd_obj['sd_obj'])
        LOGGER.info("Activating former master with restored metadata")
        self.assertTrue(storagedomains.activateStorageDomain(
            True, datacenter=config.DATA_CENTER_NAME,
            storagedomain=self.master_domain))
        LOGGER.info("Validating former master is active")
        self.assertTrue(validateElementStatus(
            True, element='storagedomain', collection='storagedomains',
            elementName=self.master_domain,
            expectedStatus=config.ENUMS['storage_domain_state_active'],
            dcName=config.DATA_CENTER_NAME))


class FailedReconstructWith2Domains(DataCenterWithSD):
    """
    Trigger reconstruct master.
    Interrupt the reconstruct operation in the middle.

    Verify that rollback is performed.
    Verify that another reconstruct is performed.
    Verify that data center has an SPM.
    Verify that data center has a master.
    Verify that data center is Up.
    """
    __test__ = IS_ISCSI_TEST or BZ_967749_FIXED
    tcms_plan_id = '2461'
    tcms_test_case = '87241'

    @tcms(tcms_plan_id, tcms_test_case)
    def test_reconstruct(self):
        """
        Corrupts metadata, waits for reconstruction and restarts vdsm - that
        should cause reconstruct to fail and perform new reconstruct that
        should succeed.
        """
        LOGGER.info("Creating MDT corruption, setting %s to -1",
                    config.MASTER_VERSION_TAG)
        result, sd_obj = generateSDMetadataCorruption(
            vds_name=self.host, username=config.HOSTS_USER,
            passwd=self.password, sd_name=self.master_domain,
            md_tag=config.MASTER_VERSION_TAG, md_tag_bad_value='-1')
        self.assertTrue(result)
        LOGGER.info("Waiting for DC to come to problematic")
        self.assertTrue(
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME,
                config.ENUMS['data_center_state_problematic'],
                timeout=DC_PROBLEM_TIMEOUT
            )
        )
        LOGGER.info("Triggering reconstruct failure")
        self.assertTrue(restartVdsmd(self.host, self.password))
        LOGGER.info("Waiting for DC to come to problematic")
        self.assertTrue(
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME,
                config.ENUMS['data_center_state_problematic'],
                timeout=DC_PROBLEM_TIMEOUT
            )
        )
        LOGGER.info("Waiting for DC becoming up")
        self.assertTrue(
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME
            )
        )
        LOGGER.info("Checking that host is SPM")
        self.assertTrue(hosts.checkHostSpmStatus(True, self.host))
        LOGGER.info("Checking that domain %s is master domain",
                    self.non_master)
        self.assertTrue(storagedomains.isStorageDomainMaster(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=self.non_master))
        LOGGER.info("Checking that domain %s is not a master domain",
                    self.non_master)
        self.assertFalse(storagedomains.isStorageDomainMaster(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=self.master_domain))
        LOGGER.info("Restoring original metadata")
        restoreSDOriginalMetadata(sd_obj=sd_obj['sd_obj'])
        LOGGER.info("Activating former master")
        self.assertTrue(storagedomains.activateStorageDomain(
            True, datacenter=config.DATA_CENTER_NAME,
            storagedomain=self.master_domain))


class ReconstructWith2UnreachableDomainsAnd1ReachableDomain(DataCenterWithSD):
    """
    Data center with 3 data domains.
    Disconnect from 2 domains using iptables.

    Verify that reconstruct fails on the 2nd domain.
    Verify that reconstruct succeeds on the 3rd domain.
    Verify that data center is operational.
    """

    __test__ = BZ_958044_FIXED
    tcms_plan_id = '2461'
    tcms_test_case = '87244'
    is_blocked = False

    @classmethod
    def setup_class(cls):
        """
        Attaches two storage domains
        """
        cls.non_master2 = STORAGE_DOMAINS[1]
        LOGGER.info("Attaching domain %s to datacenter %s", cls.non_master2,
                    config.DATA_CENTER_NAME)
        assert storagedomains.attachStorageDomain(
            True,
            datacenter=config.DATA_CENTER_NAME,
            storagedomain=cls.non_master2
        )
        assert storagedomains.activateStorageDomain(
            True,
            datacenter=config.DATA_CENTER_NAME,
            storagedomain=cls.non_master2
        )
        LOGGER.info("Deactivating master domain %s in order to have master "
                    "domain on domain that is on same server as other one",
                    cls.master_domain)
        assert storagedomains.deactivateStorageDomain(
            True, config.DATA_CENTER_NAME, cls.master_domain)
        LOGGER.info("Activating former master %s", cls.master_domain)
        assert storagedomains.activateStorageDomain(
            True,
            datacenter=config.DATA_CENTER_NAME,
            storagedomain=cls.master_domain
        )
        super(
            ReconstructWith2UnreachableDomainsAnd1ReachableDomain,
            cls
        ).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Detaches third domain
        """
        LOGGER.info("Running teardown of test case %s with is_blocked "
                    "variable set to %s", cls.__name__, cls.is_blocked)
        if cls.is_blocked:
            LOGGER.info("Unblocking connection from %s to %s", cls.host,
                        config.STORAGE_SERVERS[0])
            unblockOutgoingConnection(cls.host, config.HOSTS_USER,
                                      cls.password, config.STORAGE_SERVERS[0])
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME, config.ENUMS['data_center_state_up'],
                timeout=300)
        super(ReconstructWith2UnreachableDomainsAnd1ReachableDomain,
              cls).teardown_class()
        wait_for_tasks(config.VDC, config.VDC_PASSWORD,
                       config.DATA_CENTER_NAME)
        non_master = storagedomains.getDCStorage(
            config.DATA_CENTER_NAME, cls.non_master2)
        if non_master.status.state == \
                config.ENUMS['storage_domain_state_active']:
            LOGGER.info("Deactivating storage domain %s", non_master.name)
            assert storagedomains.deactivateStorageDomain(
                True,
                config.DATA_CENTER_NAME,
                non_master.name
            )
        non_master = storagedomains.getDCStorage(
            config.DATA_CENTER_NAME,
            non_master.name
        )
        LOGGER.info("Detaching domain %s that is in %s status",
                    non_master.name, non_master.status.state)
        assert storagedomains.detachStorageDomain(
            True,
            config.DATA_CENTER_NAME,
            non_master.name
        )

    @tcms(tcms_plan_id, tcms_test_case)
    def test_reconstruct_on_third_domain(self):
        """
        Block connection to master domain and one non-master domain.
        Reconstruct should be performed on the third domain that still has
        access to host
        """
        storages = storagedomains.getDCStorages(config.DATA_CENTER_NAME, False)
        cur_master = [sd for sd in storages if sd.get_master()][0]
        non_master_name = self.non_master2 \
            if cur_master.name == self.non_master else self.non_master
        future_master_name = self.master_domain
        LOGGER.info("Blocking outgoing connection from host %s to server %s",
                    self.host, config.STORAGE_SERVERS[0])
        self.assertTrue(blockOutgoingConnection(self.host, config.HOSTS_USER,
                        self.password, config.STORAGE_SERVERS[0]))
        self.is_blocked = True
        LOGGER.info("Waiting until connected non-master %s goes active",
                    future_master_name)
        self.assertTrue(storagedomains.waitForStorageDomainStatus(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=future_master_name,
            expectedStatus=config.ENUMS['storage_domain_state_active'],
            timeOut=DC_PROBLEM_TIMEOUT))
        LOGGER.info("Waiting until current master %s is inactive",
                    cur_master.name)
        self.assertTrue(storagedomains.waitForStorageDomainStatus(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=cur_master.name,
            expectedStatus=config.ENUMS['storage_domain_state_inactive'],
            timeOut=1800))
        LOGGER.info("Waiting until other non-master %s is inactive",
                    non_master_name)
        self.assertTrue(storagedomains.waitForStorageDomainStatus(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=non_master_name,
            expectedStatus=config.ENUMS['storage_domain_state_inactive'],
            timeOut=1800))
        LOGGER.info(
            "Waiting for DC %s to come up",
            config.DATA_CENTER_NAME
        )
        self.assertTrue(
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME
            )
        )
        LOGGER.info("Validating host %s is up", self.host)
        host_obj = HOST_API.find(self.host)
        LOGGER.debug("Host %s has status %s", self.host, host_obj.status.state)
        self.assertTrue(host_obj.status.state == config.ENUMS['host_state_up'])
        LOGGER.info("Waiting until current master %s is inactive",
                    cur_master.name)
        self.assertTrue(storagedomains.waitForStorageDomainStatus(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=cur_master.name,
            expectedStatus=config.ENUMS['storage_domain_state_inactive'],
            timeOut=1800))
        LOGGER.info("Waiting until other non-master %s is inactive",
                    non_master_name)
        self.assertTrue(storagedomains.waitForStorageDomainStatus(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=non_master_name,
            expectedStatus=config.ENUMS['storage_domain_state_inactive'],
            timeOut=1800))
        LOGGER.info("Unblocking connection from %s to %s", self.host,
                    config.STORAGE_SERVERS[0])
        self.assertTrue(unblockOutgoingConnection(self.host, config.HOSTS_USER,
                        self.password, config.STORAGE_SERVERS[0]))
        self.is_blocked = False
        LOGGER.info("Validating host %s is up", self.host)
        host_obj = HOST_API.find(self.host)
        self.assertTrue(host_obj.status.state == config.ENUMS['host_state_up'])
        LOGGER.info("Checking host is SPM")
        self.assertTrue(hosts.checkHostSpmStatus(True, self.host))
        LOGGER.info("Activating storage domain %s that had troubles",
                    cur_master.name)
        activate_result = storagedomains.activateStorageDomain(
            True, datacenter=config.DATA_CENTER_NAME,
            storagedomain=cur_master.name)
        self.assertTrue(
            handle_bz_854140(
                config.DATA_CENTER_NAME,
                cur_master.name,
                activate_result
            )
        )
        LOGGER.info("Activating storage domain %s that was in troubles",
                    non_master_name)
        activate_result = storagedomains.activateStorageDomain(
            True, datacenter=config.DATA_CENTER_NAME,
            storagedomain=non_master_name)
        self.assertTrue(
            handle_bz_854140(
                config.DATA_CENTER_NAME,
                non_master_name,
                activate_result
            )
        )


class FailedReconstructWith1Domain(DataCenterWithSD):
    """
    Configure a data center with only one (master) data storage domain.
    Initiate failure on the data storage domain.

    Verify that reconstruct master fails nicely and produces a relevant error.
    """

    __test__ = True
    tcms_plan_id = '2461'
    tcms_test_case = '50031'
    is_blocked = False

    @classmethod
    def setup_class(cls):
        """
        Creates a vm
        """
        cls.vm_name = "vm_%s" % cls.__name__
        create_installing_vm(cls.vm_name)

    @classmethod
    def teardown_class(cls):
        """
        Removes created vm
        """
        if cls.is_blocked:
            LOGGER.info("Unblocking connection from %s to %s", cls.host,
                        config.STORAGE_SERVERS[-1])
            unblockOutgoingConnection(cls.host, config.HOSTS_USER,
                                      cls.password, config.STORAGE_SERVERS[-1])
        LOGGER.info("Removing vm %s", cls.vm_name)
        assert vms.removeVm(True, vm=cls.vm_name, stopVM='true')

    @tcms(tcms_plan_id, tcms_test_case)
    def test_failed_reconstruct(self):
        """
        Blocks the connection from host to master storage domain, host should
        go to non-operational. After unblocking connection everything should
        work.
        """
        LOGGER.info("Blocking outgoing connection from host %s to server %s",
                    self.host, config.STORAGE_SERVERS[-1])
        self.assertTrue(blockOutgoingConnection(
            self.host, config.HOSTS_USER, self.password,
            config.STORAGE_SERVERS[-1]))
        self.is_blocked = True
        LOGGER.info("Waiting for DC to come to maintenance")
        self.assertTrue(
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME,
                config.ENUMS['data_center_state_problematic'],
                timeout=DC_PROBLEM_TIMEOUT
            )
        )
        LOGGER.info("Waiting until host is connecting")
        self.assertTrue(hosts.waitForHostsStates(
            True, self.host,
            states=config.ENUMS['search_host_state_connecting']))
        LOGGER.info("Waiting until host is up")
        self.assertTrue(hosts.waitForHostsStates(
            True, self.host,
            states=config.ENUMS['search_host_state_up']))
        LOGGER.info("Validating that DC is still problematic")
        dc_obj = DC_API.find(config.DATA_CENTER_NAME)
        LOGGER.info("DC is %s", dc_obj.status.state)
        self.assertTrue(
            dc_obj.status.state ==
            config.ENUMS['data_center_state_problematic'])
        LOGGER.info("Waiting for master storage domain %s to become inactive",
                    self.master_domain)
        self.assertTrue(storagedomains.waitForStorageDomainStatus(
            True, dataCenterName=config.DATA_CENTER_NAME,
            storageDomainName=self.master_domain,
            expectedStatus=config.ENUMS['storage_domain_state_inactive'],
            timeOut=1800))
        LOGGER.info("Unblocking connection from %s to %s", self.host,
                    config.STORAGE_SERVERS[-1])
        self.assertTrue(unblockOutgoingConnection(self.host, config.HOSTS_USER,
                        self.password, config.STORAGE_SERVERS[-1]))
        self.is_blocked = False
        LOGGER.info("Waiting for master domain to become active")
        self.assertTrue(
            storagedomains.waitForStorageDomainStatus(
                True, dataCenterName=config.DATA_CENTER_NAME,
                storageDomainName=self.master_domain,
                expectedStatus=config.ENUMS['storage_domain_state_active'],
                timeOut=1800))
        LOGGER.info("Waiting until DC is up")
        self.assertTrue(
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME
            )
        )
        LOGGER.info("Validating that host is up")
        host_obj = HOST_API.find(self.host)
        self.assertTrue(host_obj.status.state == config.ENUMS['host_state_up'])
        LOGGER.info("Validate master domain %s is UP", self.master_domain)
        sd_obj = storagedomains.getDCStorage(config.DATA_CENTER_NAME,
                                             self.master_domain)
        self.assertTrue(
            sd_obj.status.state == config.ENUMS['storage_domain_state_active'])
        LOGGER.info("Validate that DC is UP")
        dc_obj = DC_API.find(config.DATA_CENTER_NAME)
        LOGGER.info("DC is %s", dc_obj.status.state)
        self.assertTrue(
            dc_obj.status.state == config.ENUMS['data_center_state_up'])


class SPMStopsResponding(DataCenterWithSD):
    """
    Run "service vdsmd stop" on the SPM host.
    Or disconnect SPM host from RHEVM using iptables.

    Verify that host becomes Non Responsive.
    Verify that host is fenced after to the configured timeout.
    """

    tcms_plan_id = '2347'
    tcms_test_case = '68535'
    is_blocked = False

    @classmethod
    def setup_class(cls):
        """
        Creates a vm
        """
        cls.vm_name = "vm_%s" % cls.__name__
        create_installing_vm(cls.vm_name)

    @classmethod
    def teardown_class(cls):
        """
        Removes created vm
        """
        if cls.is_blocked:
            LOGGER.info("Starting vdsm on %s", cls.host)
            startVdsmd(cls.host, cls.password)
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME, config.ENUMS['data_center_state_up'],
                timeout=300)
        LOGGER.info("Removing vm %s", cls.vm_name)
        assert vms.removeVm(True, vm=cls.vm_name, stopVM='true')

    @tcms(tcms_plan_id, tcms_test_case)
    def test_spm_stops_responding(self):
        """
        Stops vdsm daemon on SPM. It should go to non-responsive due to broken
        communication between rhevm and vdsm. DC should be maintenance. After
        daemon starts, everything should go up.
        """
        LOGGER.info("Stopping vdsm on host %s", self.host)
        self.assertTrue(stopVdsmd(self.host, self.password))
        self.is_blocked = True
        LOGGER.info("Waiting until host is non-responsive")
        self.assertTrue(
            hosts.waitForHostsStates(
                True, self.host,
                states=config.ENUMS['search_host_state_non_responsive']))
        LOGGER.info("Waiting for DC to come to maintenance")
        self.assertTrue(datacenters.waitForDataCenterState(
            config.DATA_CENTER_NAME,
            config.ENUMS['data_center_state_problematic'],
            timeout=DC_PROBLEM_TIMEOUT))
        LOGGER.info("Waiting for master storage domain %s to become inactive",
                    self.master_domain)
        self.assertTrue(
            storagedomains.waitForStorageDomainStatus(
                True, dataCenterName=config.DATA_CENTER_NAME,
                storageDomainName=self.master_domain,
                expectedStatus=config.ENUMS['storage_domain_state_unknown'],
                timeOut=1800))
        LOGGER.info("Starting vdsm on host %s", self.host)
        self.assertTrue(startVdsmd(self.host, self.password))
        self.is_blocked = False
        LOGGER.info("Waiting for master domain to become active")
        self.assertTrue(
            storagedomains.waitForStorageDomainStatus(
                True,
                dataCenterName=config.DATA_CENTER_NAME,
                storageDomainName=self.master_domain,
                expectedStatus=config.ENUMS['storage_domain_state_active'],
                timeOut=1800))
        LOGGER.info("Waiting until DC is up")
        self.assertTrue(
            datacenters.waitForDataCenterState(
                config.DATA_CENTER_NAME
            )
        )
        LOGGER.info("Validating that host is up")
        host_obj = HOST_API.find(self.host)
        self.assertTrue(host_obj.status.state == config.ENUMS['host_state_up'])
        LOGGER.info("Validate master domain %s is UP", self.master_domain)
        sd_obj = storagedomains.getDCStorage(config.DATA_CENTER_NAME,
                                             self.master_domain)
        self.assertTrue(
            sd_obj.status.state == config.ENUMS['storage_domain_state_active'])
        LOGGER.info("Validate that DC is UP")
        dc_obj = DC_API.find(config.DATA_CENTER_NAME)
        LOGGER.info("DC is %s", dc_obj.status.state)
        self.assertTrue(
            dc_obj.status.state == config.ENUMS['data_center_state_up'])
