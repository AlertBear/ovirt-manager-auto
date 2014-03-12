"""
Storage domain upgrade
TCMS plan:
"""

import logging
from nose.tools import istest
from sys import modules
from art.unittest_lib import BaseTestCase as TestCase

import art.rhevm_api.tests_lib.low_level.clusters as llclusters
import art.rhevm_api.tests_lib.low_level.datacenters as lldatacenters
import art.rhevm_api.tests_lib.low_level.hosts as llhosts
import art.rhevm_api.tests_lib.low_level.storagedomains as llstoragedomains
import art.rhevm_api.tests_lib.low_level.vms as llvms
import art.rhevm_api.tests_lib.high_level.storagedomains as hlstoragedomains
from art.rhevm_api.utils.test_utils import get_api, wait_for_tasks
import config

__THIS_MODULE = modules[__name__]

LOGGER = logging.getLogger(__name__)

DC_API = get_api('data_center', 'datacenters')
HOST_API = get_api('host', 'hosts')
VM_API = get_api('vm', 'vms')
SD_API = get_api('storage_domain', 'storagedomains')
CLUSTER_API = get_api('cluster', 'clusters')

GB = 1024 ** 3
TEN_GB = 10 * GB


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
        wait_for_tasks(config.SETUP_ADDRESS, config.SETUP_PASSWORD,
                       dc_obj.name)
    if host_obj.status.state != config.ENUMS['host_state_maintenance']:
        assert llhosts.deactivateHost(True, host)
    assert llhosts.updateHost(True, host, cluster=cluster)
    assert llhosts.activateHost(True, host)


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
    cluster_version = "3.2"
    host = config.PARAMETERS.as_list('vds')[0]
    vm_name = 'vm_test'
    domain_kw = None

    @classmethod
    def setup_class(cls):
        """
        Prepares data-center without storages
        """
        LOGGER.info("Running class %s setup", cls.__name__)
        assert lldatacenters.addDataCenter(True, name=cls.dc_name,
                                           storage_type=cls.storage_type,
                                           version=cls.dc_version)
        assert llclusters.addCluster(True, name=cls.cluster_name,
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
        vms = VM_API.get(absLink=False)
        up_vms = [vm.name for vm in vms
                  if vm.status.state != config.ENUMS['vm_state_down']]
        llvms.stopVms(",".join(up_vms))
        for vm_obj in vms:
            llvms.removeVm(True, vm_obj.name)
        vdc = config.VDC
        vdc_password = config.VDC_PASSWORD
        if vdc is not None and vdc_password is not None:
            LOGGER.info('Waiting for vms to be removed')
            wait_for_tasks(
                vdc=vdc, vdc_password=vdc_password, datacenter=cls.dc_name)
        assert llstoragedomains.execOnNonMasterDomains(
            True, cls.dc_name, 'deactivate', 'all')
        assert llstoragedomains.execOnNonMasterDomains(
            True, cls.dc_name, 'detach', 'all')
        _, master_name = llstoragedomains.findMasterStorageDomain(
            True, cls.dc_name)
        assert llstoragedomains.deactivateStorageDomain(
            True, cls.dc_name, master_name['masterDomain'])
        assert lldatacenters.removeDataCenter(True, cls.dc_name)
        put_host_to_cluster(cls.host, config.TMP_CLUSTER_NAME)
        assert llclusters.removeCluster(True, cls.cluster_name)
        for i in range(len(config.PARAMETERS.as_list(cls.domain_kw))):
            assert llstoragedomains.removeStorageDomain(
                True, cls.sd_name_pattern % i, cls.host)
            LOGGER.info("%s storage domain %s was removed successfully",
                        cls.storage_type, cls.sd_name_pattern % i)
        LOGGER.info("Class %s teardown finished", cls.__name__)

    @istest
    def test_data_center_upgrade(self):
        """
        Changes DC version while installing a VM
        """
        nic = config.PARAMETERS['host_nics'][0]
        assert llvms.createVm(
            True, self.vm_name, '', cluster=self.cluster_name,
            nic=nic, nicType=config.ENUMS['nic_type_virtio'],
            storageDomainName=self.sd_name_pattern % 0,
            size=TEN_GB, diskType=config.ENUMS['disk_type_system'],
            volumeFormat=config.ENUMS['format_cow'],
            diskInterface=config.ENUMS['interface_ide'],
            bootable=True, wipe_after_delete=False,
            type=config.ENUMS['vm_type_server'], os_type="rhel6x64",
            memory=1073741824, cpu_socket=1, cpu_cores=1,
            display_type=config.ENUMS['display_type_spice'],
            network=config.PARAMETERS['mgmt_bridge'])
        assert llvms.unattendedInstallation(
            True, self.vm_name, config.PARAMETERS['cobbler_profile'], nic=nic,
            cobblerAddress=config.PARAMETERS.get('cobbler_address', None),
            cobblerUser=config.PARAMETERS.get('cobbler_user', None),
            cobblerPasswd=config.PARAMETERS.get('cobbler_passwd', None))
        assert llvms.waitForVMState(self.vm_name)
        # getVmMacAddress returns (bool, dict(macAddress=<desired_mac>))
        mac = llvms.getVmMacAddress(True, self.vm_name, nic=nic)[1]
        mac = mac['macAddress']
        LOGGER.debug("Got mac of vm %s: %s", self.vm_name, mac)
        assert llvms.removeSystem(mac)

        LOGGER.info("Upgrading data-center %s from version %s to version %s ",
                    self.dc_name, self.dc_version, self.dc_upgraded_version)
        lldatacenters.updateDataCenter(True, datacenter=self.dc_name,
                                       version=self.dc_upgraded_version)
        sds = llstoragedomains.getDCStorages(self.dc_name, get_href=False)
        for sd_obj in sds:
            was_upgraded = llstoragedomains.checkStorageFormatVersion(
                True, sd_obj.name, self.upgraded_storage_format)
            LOGGER.info("Checking that %s was upgraded: %s", sd_obj.name,
                        was_upgraded)
            self.assertTrue(was_upgraded)
        assert llvms.waitForIP(self.vm_name)


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
                config.PARAMETERS.as_list('data_domain_path'))):
            assert hlstoragedomains.addNFSDomain(
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
                config.PARAMETERS.as_list('lun'))):
            assert hlstoragedomains.addISCSIDataDomain(
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
            'upgraded_storage_format':
            config.ENUMS['storage_format_version_v3']
        }
        new_class = type(class_name, (TYPE_TO_CLASS[config.DC_TYPE],),
                         class_attrs)
        setattr(__THIS_MODULE, class_name, new_class)
delattr(__THIS_MODULE, 'new_class')
