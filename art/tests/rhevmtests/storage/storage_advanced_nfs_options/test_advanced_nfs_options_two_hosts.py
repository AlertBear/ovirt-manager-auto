import logging
import pytest
import config
import helpers
from art.core_api import apis_exceptions
from art.core_api.apis_exceptions import EntityNotFound
from art.rhevm_api.tests_lib.high_level import (
    storagedomains as hl_sd,
    vms as hl_vms
)
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    templates as ll_templates,
    vms as ll_vms,
)
from art.test_handler import exceptions
from art.test_handler.settings import opts
from art.test_handler.tools import polarion
from art.unittest_lib import attr

logger = logging.getLogger(__name__)
NFS = config.STORAGE_TYPE_NFS
DEFAULT_DC_TIMEOUT = 1500


@pytest.fixture(scope='module')
def initializer_module(request):
    """
    Prepare extra host for testing
    """
    def finalizer_module():
        """Adding host back to the previous DC"""
        host_ip = config.HOST_FOR_30_DC['ip']
        host_name = config.HOST_FOR_30_DC['name']
        try:
            logger.info(
                "Trying to deactivate and remove the host %s in case there "
                "was a problem with the test's finalizer function", host_ip,
            )
            if ll_hosts.get_host_status(host_ip) == config.HOST_UP:
                ll_hosts.deactivateHost(True, host_ip)
            ll_hosts.removeHost(True, host_ip)
        except EntityNotFound:
            pass

        logger.info(
            "Attaching host %s with ip %s to cluster %s",
            host_name, host_ip, config.CLUSTER_NAME)
        if not ll_hosts.addHost(
            True, name=host_name, root_password=config.HOSTS_PW,
            cluster=config.CLUSTER_NAME, address=host_ip,
        ):
            raise exceptions.HostException("Failed to add host %s" % host_name)
        config.HOSTS.append(host_name)

    request.addfinalizer(finalizer_module)
    status, hsm_host = ll_hosts.getAnyNonSPMHost(
        config.HOSTS, cluster_name=config.CLUSTER_NAME
    )
    assert status, "Unable to get a hsm from cluster %s" % config.CLUSTER_NAME
    host_name = hsm_host['hsmHost']
    host_ip = ll_hosts.getHostIP(host_name)
    config.HOST_FOR_30_DC = {'name': host_name, 'ip': host_ip}
    assert ll_hosts.deactivateHost(True, host_name)
    assert ll_hosts.removeHost(True, host_name)
    config.HOSTS.remove(host_name)


@attr(tier=3)
class TestCase4831(helpers.TestCaseNFSOptions):
    """
    Tests if data center with NFS storage domains with custom NFS options works
    correctly. Performed operations:
     * moving vm to another storage domain
     * moving vm disk to another storage domain
     * migrating vm to another host
     * exporting template
     * switching SPM
     * reconstruction of master storage domain

    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_1_Storage_NFS_Options

    **Author**: Katarzyna Jachim
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '4831'
    sd_1 = 'test_%s_1' % polarion_test_case
    sd_2 = 'test_%s_2' % polarion_test_case
    sd_exp = 'test_%s_exp' % polarion_test_case
    disk_1 = 'test_%s_disk_1' % polarion_test_case
    disk_2 = 'test_%s_disk_2' % polarion_test_case
    vm_1 = 'vm_%s_1' % polarion_test_case
    vm_2 = 'vm_%s_2' % polarion_test_case
    template = 'templ_%s' % polarion_test_case
    host_for_dc = None
    master_domain = None

    # Bugzilla history:
    # 1248035: VM migration: migration failed since vdsm failed to run VM...
    # 1254230: Operation of exporting template to Export domain gets stuck
    # 1294511: Pool's template version doesn't update when set to latest
    #          and a new version is created

    @pytest.fixture(scope='class')
    def initializer_class(self, request, initializer_module):
        """
        Getting the master domain
        """
        def finalizer_class():
            """
            Clears everything which won't be cleaned with basic finalizer
            Don't add asserts, in case of errors in the test some of the
            commands may fail which is OK.
            """
            ll_vms.stop_vms_safely([self.vm_1])
            if not ll_hosts.isHostUp(True, self.host):
                ll_hosts.activateHost(True, self.host)
            try:
                ll_templates.removeTemplate(True, self.template)
            except apis_exceptions.EntityNotFound:
                pass
            try:
                ll_vms.removeVm(True, vm=self.vm_1)
            except apis_exceptions.EntityNotFound:
                pass
            try:
                ll_vms.removeVm(True, vm=self.vm_2)
            except apis_exceptions.EntityNotFound:
                pass
            ll_vms.waitForVmsGone(True, ",".join([self.vm_1, self.vm_2]))

            if self.master_domain:
                ll_sd.activateStorageDomain(
                    True, config.DATA_CENTER_NAME, self.master_domain,
                )
                ll_sd.waitForStorageDomainStatus(
                    True, config.DATA_CENTER_NAME, self.master_domain,
                    config.SD_ACTIVE, timeOut=DEFAULT_DC_TIMEOUT
                )

            for sd_remove in [self.sd_1, self.sd_2, self.sd_exp]:
                if ll_sd.checkIfStorageDomainExist(True, sd_remove):
                    self.sds_for_cleanup.append(sd_remove)
                    ll_sd.deactivateStorageDomain(
                        True, config.DATA_CENTER_NAME, sd_remove
                    )
            try:
                logger.info("Removing host %s", self.host_for_dc)
                if ll_hosts.isHostUp(True, self.host_for_dc):
                    ll_hosts.deactivateHost(True, self.host_for_dc)
                ll_hosts.waitForSPM(config.DATA_CENTER_NAME, 600, 30)
                ll_hosts.removeHost(True, self.host_for_dc)
            except apis_exceptions.EntityNotFound:
                pass
            self.cleanup_class()

        request.addfinalizer(finalizer_class)
        self.host_for_dc = config.HOST_FOR_30_DC['ip']
        logger.info("Getting master storage domain")
        found, master_domain = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME,
        )
        if not found:
            self.fail("Master storage domain was not found")
        self.master_domain = master_domain['masterDomain']
        self.initialize_parameters()

    @pytest.fixture(scope='function')
    def initializer_TestCase4831(self, request, initializer_class):
        """
        Prepares environment - creates storage domains with different
        NFS options, vms, a template etc.
        """
        sd_type = config.TYPE_DATA

        hl_sd.create_nfs_domain_with_options(
            self.sd_1, sd_type, self.host, config.NFS_ADDRESSES[0],
            config.NFS_PATHS[0], version='v3', retrans=7, timeo=700,
            datacenter=config.DATA_CENTER_NAME
        )
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_1
        )

        hl_sd.create_nfs_domain_with_options(
            self.sd_2, sd_type, self.host, config.NFS_ADDRESSES[1],
            config.NFS_PATHS[1], version='v3', retrans=8, timeo=800,
            datacenter=config.DATA_CENTER_NAME
        )
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_2
        )

        hl_sd.create_nfs_domain_with_options(
            self.sd_exp, config.EXPORT_TYPE, self.host,
            config.NFS_ADDRESSES[2], config.NFS_PATHS[2],
            datacenter=config.DATA_CENTER_NAME
        )
        assert ll_sd.activateStorageDomain(
            True, config.DATA_CENTER_NAME, self.sd_exp
        )

        assert ll_disks.addDisk(
            True, alias=self.disk_1, provisioned_size=config.DISK_SIZE,
            storagedomain=self.sd_1, format=config.RAW_DISK,
            interface=config.INTERFACE_VIRTIO, bootable=True
        )

        assert ll_disks.addDisk(
            True, alias=self.disk_2, provisioned_size=config.DISK_SIZE,
            storagedomain=self.sd_1, format=config.RAW_DISK,
            interface=config.INTERFACE_VIRTIO, bootable=True)

        assert ll_vms.addVm(
            True, name=self.vm_1, storagedomain=self.sd_1,
            cluster=config.CLUSTER_NAME, display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE
        )
        assert ll_vms.addVm(
            True, name=self.vm_2, storagedomain=self.sd_1,
            cluster=config.CLUSTER_NAME, display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE,
        )

        assert ll_disks.wait_for_disks_status(
            [self.disk_1, self.disk_2], timeout=600)

        assert ll_disks.attachDisk(True, self.disk_1, self.vm_1)
        assert ll_disks.attachDisk(True, self.disk_2, self.vm_2)

        assert ll_templates.createTemplate(
            True, vm=self.vm_1, name=self.template,
            cluster=config.CLUSTER_NAME)

        assert ll_hosts.addHost(
            True, name=self.host_for_dc, root_password=self.password,
            cluster=config.CLUSTER_NAME,
        ), "Unable to add host %s to cluster %s" % (
            self.host_for_dc, config.CLUSTER_NAME)

    def perform_standard_operations(self, vm, vm_with_disk, disk, another_std,
                                    template, export_std, datacenter):
        """
        Performs standard operations:
            * moves disks of a vm to another storage domain
            * migrates vm to another host
            * exports template
            * changes SPM host
            * rebuilds master storage domain

        **Author**: Katarzyna Jachim

        **Parameters**:
         * *vm*: vm which will be moved and migrated
         * *vm_with_disk*: vm which disk will be moved
         * *disk*: disk which should be moved
         * *another_std*: storage domain to which we will move vm/disk
         * *template*: template which will be exported
         * *export_std*: export storage domain
         * *datacenter*: data center on which we will perform operations

        **Returns**: nothing, fails the test in case of any error
        """
        self.master_domain = None
        logger.info("Moving disks of vm %s to %s", vm_with_disk, another_std)
        hl_vms.move_vm_disks(vm_with_disk, another_std)
        logger.info("Starting vm %s", vm)
        ll_vms.startVm(True, vm)
        status, host_with_vm = ll_vms.getVmHost(vm)
        host_with_vm = host_with_vm['vmHoster']
        logger.info("Current host: %s", host_with_vm)
        if not status:
            self.fail("Cannot get host with vm")

        hosts = config.HOSTS + [self.host_for_dc]
        host_2 = filter(lambda w: w != host_with_vm, hosts)[0]
        logger.info("Migrating vm %s", vm)
        if not ll_vms.migrateVm(True, vm, host_2):
            self.fail("Cannot migrate vm %s to %s" % (vm, host_2))
        logger.info("Exporting template")
        if not ll_templates.exportTemplate(
                True, template, export_std, wait=True
        ):
            self.fail(
                "Exporting template %s on %s failed" % (template, export_std)
            )

        logger.info("Changing SPM host")
        old_spm_host = ll_hosts.getSPMHost(hosts)
        if not ll_hosts.deactivateHost(True, old_spm_host):
            logger.error("Cannot deactivate host %s", old_spm_host)
            self.fail("Cannot deactivate host %s" % old_spm_host)
        ll_hosts.waitForSPM(config.DATA_CENTER_NAME, 600, 30)
        new_spm_host = ll_hosts.getSPMHost(hosts)
        logger.info("New SPM host: %s", new_spm_host)

        logger.info("Getting master storage domain")
        found, master_domain = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        if not found:
            self.fail("Master storage domain not found")
        self.master_domain = master_domain['masterDomain']
        logger.info(
            "Deactivating master storage domain %s", self.master_domain,
        )
        if not ll_sd.deactivateStorageDomain(
                True, datacenter, self.master_domain
        ):
            self.fail("Cannot deactivate master storage domain")
        found, new_master = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        if not found:
            self.fail("New master not found!")
        logger.info("New master: %s", new_master['masterDomain'])

    @polarion("RHEVM3-4831")
    @pytest.mark.usefixtures("initializer_TestCase4831")
    def test_functionality_with_custom_nfs_options(self):
        """ Tests basic data center functionality with storage domain with
        custom NFS options
        """
        self.perform_standard_operations(
            self.vm_1, self.vm_2, self.disk_2, self.sd_2, self.template,
            self.sd_exp, config.DATA_CENTER_NAME)
