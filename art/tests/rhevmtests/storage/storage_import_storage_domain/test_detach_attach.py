"""
3.5 - Import Storage Domain
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_5_Storage_ImportDomain_DetachAttach
"""
import logging
import shlex
from art.rhevm_api.tests_lib.low_level.hosts import getSPMHost
import art.test_handler.exceptions as errors
import rhevmtests.storage.helpers as storage_helpers
from art.rhevm_api.tests_lib.low_level import clusters as ll_clusters
from art.rhevm_api.tests_lib.low_level import datacenters as ll_datacenters
from art.rhevm_api.tests_lib.low_level import disks as ll_disks
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.rhevm_api.tests_lib.low_level import storagedomains as ll_sd
from art.rhevm_api.tests_lib.low_level import templates as ll_templates
from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.rhevm_api.tests_lib.low_level.jobs import wait_for_jobs
from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.high_level import storagedomains
from art.rhevm_api.utils import storage_api as utils
from art.rhevm_api.utils import test_utils as test_utils
from art.test_handler.settings import opts
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr
from art.unittest_lib import StorageTest as BaseTestCase
from utilities.machine import Machine, LINUX
from rhevmtests.storage.storage_import_storage_domain import config

logger = logging.getLogger(__name__)

ENUMS = config.ENUMS
NFS = config.STORAGE_TYPE_NFS
UPDATE_OVF_INTERVAL_CMD = 'engine-config -s OvfUpdateIntervalInMinutes=%s'

VM_NAMES = dict()
IMPORT_DOMAIN = dict()
SPM_TIMEOUT = 600
SPM_SLEEP = 5
MIN_UNUSED_LUNS = 1

vmArgs = {
    'positive': True, 'vmName': config.VM_NAME,
    'vmDescription': config.VM_NAME, 'diskInterface': config.VIRTIO,
    'volumeFormat': config.COW_DISK, 'cluster': config.CLUSTER_NAME,
    'storageDomainName': None, 'installation': True, 'size': config.DISK_SIZE,
    'nic': 'nic1', 'image': config.COBBLER_PROFILE, 'useAgent': True,
    'os_type': config.ENUMS['rhel6'], 'user': config.VM_USER,
    'password': config.VM_PASSWORD, 'network': config.MGMT_BRIDGE,
}


def setup_module():
    """
    Prepares environment
    """
    global IMPORT_DOMAIN, VM_NAMES
    if not config.GOLDEN_ENV:
        logger.info("Preparing datacenter %s with hosts %s",
                    config.DATA_CENTER_NAME, config.VDC)

        datacenters.build_setup(config.PARAMETERS, config.PARAMETERS,
                                config.STORAGE_TYPE, config.TESTNAME)

    rc, masterSD = ll_sd.findMasterStorageDomain(
        True, config.DATA_CENTER_NAME
    )
    if not rc:
        raise errors.StorageDomainException(
            "Could not find master storage domain for dc %s" %
            config.DATA_CENTER_NAME
        )

    for storage_type in config.STORAGE_SELECTOR:
        VM_NAMES[storage_type] = []
        spm = ll_hosts.getSPMHost(config.HOSTS)
        sd_name = config.TESTNAME
        if storage_type in config.BLOCK_TYPES:
            if not len(config.UNUSED_LUNS) >= 1:
                raise errors.StorageDomainException(
                    "There are no unused LUNs, aborting test"
                )
            sd_name = "{0}_{1}".format(config.TESTNAME, "iSCSI")
            status_attach_and_activate = storagedomains.addISCSIDataDomain(
                spm,
                sd_name,
                config.DATA_CENTER_NAME,
                config.UNUSED_LUNS["lun_list"][0],
                config.UNUSED_LUNS["lun_addresses"][0],
                config.UNUSED_LUNS["lun_targets"][0],
                override_luns=True
            )
            if not status_attach_and_activate:
                raise errors.StorageDomainException(
                    "Creating iSCSI domain '%s' failed" % sd_name
                )
            wait_for_jobs()
        elif storage_type == NFS:
            sd_name = "{0}_{1}".format(config.TESTNAME, "NFS")
            nfs_address = config.UNUSED_DATA_DOMAIN_ADDRESSES[0]
            nfs_path = config.UNUSED_DATA_DOMAIN_PATHS[0]
            status = storagedomains.addNFSDomain(
                host=spm,
                storage=sd_name,
                data_center=config.DATA_CENTER_NAME,
                address=nfs_address,
                path=nfs_path,
                format=True
            )
            if not status:
                raise errors.StorageDomainException(
                    "Creating NFS domain '%s' failed" % sd_name
                )
        elif storage_type == config.STORAGE_TYPE_GLUSTER:
            sd_name = "{0}_{1}".format(config.TESTNAME, "Gluster")
            gluster_address = \
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0]
            gluster_path = config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0]
            status = storagedomains.addGlusterDomain(
                host=spm,
                name=sd_name,
                data_center=config.DATA_CENTER_NAME,
                address=gluster_address,
                path=gluster_path,
                vfs_type=config.ENUMS['vfs_type_glusterfs']
            )
            if not status:
                raise errors.StorageDomainException(
                    "Creating Gluster domain '%s' failed" % sd_name
                )
        wait_for_jobs()
        # This domain will be the domain to import during the whole run.
        # Deactivate it before creating the vm for the job to make sure that
        # the vm is not created on it.
        IMPORT_DOMAIN[storage_type] = sd_name
        logger.info(
            "Non-master domain to import into during test "
            "run: %s for storage type %s",
            IMPORT_DOMAIN[storage_type], storage_type
        )

        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        storagedomains.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, IMPORT_DOMAIN[storage_type]
        )
        wait_for_jobs()

        storage_domain = ll_sd.getStorageDomainNamesForType(
            config.DATA_CENTER_NAME, storage_type
        )[0]
        vm_name = config.VM_NAME % storage_type

        vmArgs['storageDomainName'] = storage_domain
        vmArgs['vmName'] = vm_name
        vmArgs['vmDescription'] = vm_name

        if not storage_helpers.create_vm_or_clone(**vmArgs):
            raise errors.VMException(
                'Unable to create vm %s for test' % vm_name
            )
        VM_NAMES[storage_type].append(vm_name)
        logger.info('Shutting down VM %s', vm_name)
        ll_vms.stop_vms_safely([vm_name])

        logger.info(
            "Attaching storage domain %s", IMPORT_DOMAIN[storage_type]
        )
        storagedomains.attach_and_activate_domain(
            config.DATA_CENTER_NAME, IMPORT_DOMAIN[storage_type]
        )
        wait_for_jobs()
    engine = Machine(
        config.VDC, config.VDC_ROOT_USER, config.VDC_PASSWORD
    ).util(LINUX)

    rc, out = engine.runCmd(shlex.split(UPDATE_OVF_INTERVAL_CMD % 1))
    if not rc:
        raise errors.HostException(
            "Filed to update OVF update interval: %s" % out
        )

    # Make sure there are no running tasks in DB before restarting
    # ovirt-engine service in order to work around bug:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1213850
    test_utils.wait_for_tasks(
        config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
    )
    logger.info("Restarting ovirt-engine service")
    test_utils.restartOvirtEngine(engine, 10, 15, 300)


def teardown_module():
    """
    Clean datacenter
    """
    host = ll_hosts.getSPMHost(config.HOSTS)
    exception_flag = False
    engine = Machine(
        config.VDC, config.VDC_ROOT_USER, config.VDC_PASSWORD
    ).util(LINUX)

    rc, out = engine.runCmd(shlex.split(UPDATE_OVF_INTERVAL_CMD % 60))
    if not rc:
        logger.error("Filed to update OVF update interval: %s", out)
        exception_flag = True

    # Make sure there are no running tasks in DB before restarting
    # ovirt-engine service in order to work around bug:
    # https://bugzilla.redhat.com/show_bug.cgi?id=1213850
    test_utils.wait_for_tasks(
        config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
    )
    logger.info("Restarting ovirt-engine service")
    test_utils.restartOvirtEngine(engine, 10, 15, 300)

    for vm_names in VM_NAMES.values():
        ll_vms.safely_remove_vms(vm_names)

    for storage_domain_name in IMPORT_DOMAIN.values():
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        if not storagedomains.detach_and_deactivate_domain(
            config.DATA_CENTER_NAME, storage_domain_name
        ):
            logger.error(
                'Failed to deactivate storage domain %s',
                storage_domain_name
            )
            exception_flag = True
        if not ll_sd.removeStorageDomain(
            True, storage_domain_name, host, format='true'
        ):
            logger.error(
                'Failed to remove storage domain %s',
                storage_domain_name
            )
            exception_flag = True

    if not config.GOLDEN_ENV:
        logger.info('Cleaning datacenter')
        datacenters.clean_datacenter(
            True, config.DATA_CENTER_NAME, vdc=config.VDC,
            vdc_password=config.VDC_PASSWORD
        )

    if exception_flag:
        raise errors.TearDownException(
            "Test failed while executing teardown_module"
        )


class BasicEnvironment(BaseTestCase):
    """
    This class implements setup and teardowns of common things
    """
    __test__ = False
    # TODO: Run only on rest:
    # https://projects.engineering.redhat.com/browse/RHEVM-1654
    apis = BaseTestCase.apis - set(['cli', 'java', 'sdk'])
    polarion_test_case = None

    def setUp(self):
        """
        Create disks for case
        """
        self.test_failed = False
        self.vm_name = config.VM_NAME % self.storage
        status, master_domain = ll_sd.findMasterStorageDomain(
            True, config.DATA_CENTER_NAME
        )
        if not status:
            raise errors.StorageDomainException(
                "Unable to find master storage domain"
            )

        self.non_master = IMPORT_DOMAIN[self.storage]

    def _secure_detach_storage_domain(self, datacenter_name, domain_name):
        logger.info("Detaching storage domain %s", domain_name)
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, datacenter_name
        )
        storagedomains.detach_and_deactivate_domain(
            datacenter_name, domain_name
        )

    def _prepare_environment(self):
        disk_sd_name = ll_disks.get_disk_storage_domain_name(
            ll_vms.getVmDisks(self.vm_name)[0].get_alias()
        )
        if disk_sd_name != self.non_master:
            for vm_disk in [
                disk.get_alias() for disk in ll_vms.getVmDisks(self.vm_name)
            ]:
                ll_vms.move_vm_disk(self.vm_name, vm_disk, self.non_master)

        wait_for_jobs()

    def _create_environment(self, dc_name, cluster_name,
                            comp_version=config.COMPATIBILITY_VERSION):
        if not ll_datacenters.addDataCenter(
                True, name=dc_name, storage_type=config.STORAGE_TYPE,
                local=False, version=config.COMPATIBILITY_VERSION
        ):
            raise errors.DataCenterException(
                "Failed to create dc %s" % dc_name
            )

        logger.info("Data Center %s was created successfully", dc_name)

        if not ll_clusters.addCluster(
                True, name=cluster_name, cpu=config.CPU_NAME,
                data_center=dc_name, version=comp_version
        ):
            raise errors.ClusterException(
                "addCluster %s with cpu %s and version %s "
                "to datacenter %s failed"
                % (cluster_name, config.CPU_NAME, comp_version, dc_name)
            )
        logger.info("Cluster %s was created successfully", cluster_name)

        hsm = ll_hosts.getHSMHost(config.HOSTS)
        if not ll_hosts.deactivateHost(True, hsm):
            raise errors.HostException("Failed to deactivate host %s" % hsm)
        ll_hosts.waitForHostsStates(True, [hsm], config.HOST_MAINTENANCE)

        if not ll_hosts.updateHost(
                True, hsm, cluster=cluster_name
        ):
            raise errors.HostException("Failed to update host %s" % hsm)

        if not ll_hosts.activateHost(True, hsm):
            raise errors.HostException("Failed to activate host %s" % hsm)
        ll_hosts.waitForHostsStates(True, [hsm], config.HOST_UP)

    def _clean_environment(self, dc_name, cluster_name, sd_name):
        """
        This function is used by tearDown
        """
        spm = ll_hosts.getHost(True, dataCenter=dc_name)[1]['hostName']
        logger.info(
            'Checking if domain %s is active in dc %s', sd_name, dc_name
        )
        if ll_sd.is_storage_domain_active(dc_name, sd_name):
            logger.info('Domain %s is active in dc %s', sd_name, dc_name)

            logger.info(
                'Deactivating domain  %s in dc %s', sd_name, dc_name
            )
            logger.info(
                "Waiting for tasks before deactivating Storage Domain"
            )
            test_utils.wait_for_tasks(
                config.VDC, config.VDC_PASSWORD, dc_name
            )
            if not ll_sd.deactivateStorageDomain(True, dc_name, sd_name):
                logger.error(
                    'Unable to deactivate domain %s on dc %s',
                    sd_name, dc_name
                )
                self.test_failed = True
        logger.info(
            'Domain %s is inactive in datacenter %s', sd_name, dc_name
        )

        if not ll_datacenters.removeDataCenter(True, dc_name):
            logger.error("Failed to remove dc %s" % dc_name)
            self.test_failed = True

        if not ll_hosts.deactivateHost(True, spm):
            logger.error("Failed to deactivate host %s" % spm)
            self.test_failed = True
        ll_hosts.waitForHostsStates(True, [spm], config.HOST_MAINTENANCE)

        if not ll_hosts.updateHost(
            True, spm, cluster=config.CLUSTER_NAME
        ):
            logger.error("Failed to update host %s" % spm)
            self.test_failed = True

        if not ll_hosts.activateHost(True, spm):
            logger.error("Failed to activate host %s" % spm)
            self.test_failed = True
        ll_hosts.waitForHostsStates(True, [spm], config.HOST_UP)

        if not ll_clusters.removeCluster(True, cluster_name):
            logger.error("Failed to remove cluster %s" % cluster_name)
            self.test_failed = True

        if not ll_sd.removeStorageDomain(True, sd_name, spm, format='true'):
            logger.error("Failed to remove storage domain %s" % sd_name)
            self.test_failed = True

    def register_vm(self, vm_name):
        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names_to_register = [vm for vm in unregistered_vms if
                                (vm.get_name() == vm_name)]
        if vm_names_to_register:
            status = ll_sd.register_object(
                vm_names_to_register[0], cluster=config.CLUSTER_NAME
            )
            return status
        return False


class CommonSetUp(BasicEnvironment):
    """
    Class for common setUp actions
    """
    def setUp(self):
        super(CommonSetUp, self).setUp()
        self._secure_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )


@attr(tier=0)
class TestCase11861(BasicEnvironment):
    """
    Detach/Attach a new Domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_DetachAttach
    """
    __test__ = True
    polarion_test_case = '11861'

    @polarion("RHEVM3-11861")
    def test_detach_attach_new_domain(self):
        """
        - Detach a domain and then re-attach it
        """
        self._secure_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )

        logger.info("Attaching storage domain %s", self.non_master)
        storagedomains.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )


@attr(tier=1)
class TestCase5297(BasicEnvironment):
    """
    create vm from imported domain's Template
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_Between_DifferentSetups
    """
    __test__ = True
    polarion_test_case = '5297'
    vm_from_template = 'vm_from_temp'
    bz = {'1138142': {'engine': ['rest', 'sdk'], 'version': ['3.5', '3.6']}}

    def setUp(self):
        self.vm_created = False
        self.template_exists = False
        self.template_name = 'temp_%s' % self.polarion_test_case
        super(TestCase5297, self).setUp()
        ll_vms.stop_vms_safely([self.vm_name])
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)

        if not ll_templates.createTemplate(
                True, vm=self.vm_name, name=self.template_name,
                cluster=config.CLUSTER_NAME, storagedomain=self.non_master
        ):
            raise errors.TemplateException(
                "Failed to create template %s from vm %s"
                % (self.template_name, self.vm_name)
            )

        self._secure_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )

    @polarion("RHEVM3-5297")
    def test_new_vm_from_imported_domain_template(self):
        """
        - import data domain
        - verify template's existence
        - create VM from template
        """
        logger.info("Attaching storage domain %s", self.non_master)
        storagedomains.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        wait_for_jobs()

        unregistered_templates = ll_sd.get_unregistered_templates(
            self.non_master
        )
        template_names = [
            template.get_name() for template in unregistered_templates
        ]
        logger.info("Unregistered templates: %s", template_names)
        template_to_register = [
            template for template in unregistered_templates if (
                template.get_name() == self.template_name
            )
        ]

        self.template_exists = ll_sd.register_object(
            template_to_register, cluster=config.CLUSTER_NAME
        )
        self.assertTrue(self.template_exists, "Template registration failed")

        self.vm_created = ll_vms.createVm(
            True, self.vm_from_template, self.vm_from_template,
            template=self.template_name, cluster=config.CLUSTER_NAME
        )
        assert self.vm_created
        ll_vms.waitForVMState(self.vm_from_template)

    def tearDown(self):
        if self.template_exists:
            if not ll_templates.removeTemplate(True, self.template_name):
                logger.error(
                    "Failed to remove template %s", self.template_name
                )
                self.test_failed = True
        wait_for_jobs()

        if self.vm_created:
            if not ll_vms.removeVm(
                True, self.vm_from_template, stopVM='true', wait='true'
            ):
                logger.error(
                    "Failed to remove vm %s", self.vm_from_template
                )
                self.test_failed = True
        wait_for_jobs()
        self.teardown_exception()


@attr(tier=1)
class TestCase5299(BasicEnvironment):
    """
    Register vm without disks
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_Between_DifferentSetups
    """
    __test__ = True
    polarion_test_case = '5299'
    vm_no_disks = "vm_without_disks"
    bz = {'1138142': {'engine': ['rest', 'sdk'], 'version': ["3.5", "3.6"]}}

    def setUp(self):
        self.vm_created = False
        super(TestCase5299, self).setUp()

        self.vm_created = ll_vms.addVm(
            True, name=self.vm_no_disks, cluster=config.CLUSTER_NAME,
            storagedomain=self.non_master
        )
        if not self.vm_created:
            raise errors.VMException(
                "Failed to create vm %s" % self.vm_no_disks
            )

        self._secure_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )

    @polarion("RHEVM3-5299")
    def test_register_vm_without_disks(self):
        """
        - Detach domain
        - Attach domain
        - Verify no vm was unregistered
        """
        logger.info("Attaching storage domain %s", self.non_master)
        storagedomains.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        wait_for_jobs()

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_to_import = [
            vm for vm in unregistered_vms if (
                vm.get_name() == self.vm_no_disks
            )
        ]
        logger.info("Unregistered vms: %s", vm_to_import)
        self.assertEqual(
            len(vm_to_import), 0, "VM with no disks was unregistered"
        )
        self.assertTrue(
            ll_vms.does_vm_exist(self.vm_no_disks),
            "VM doesn't exist after importing storage domain"
        )
        # TODO: Remove this logger before merge
        logger.info("Case finished")

    def tearDown(self):
        if self.vm_created:
            if not ll_vms.removeVm(True, self.vm_no_disks, wait='true'):
                logger.error("Failed to remove vm %s", self.vm_no_disks)
                self.test_failed = True
        self.teardown_exception()


@attr(tier=1)
class TestCase5300(BasicEnvironment):
    """
    import domain, preview snapshots and create vm from a snapshot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_Between_DifferentSetups
    """
    __test__ = True
    polarion_test_case = '5300'
    cloned_vm = 'cloned_vm'

    def setUp(self):
        self.snap_desc = 'snap_%s' % self.polarion_test_case
        self.previewed = False
        super(TestCase5300, self).setUp()
        self._prepare_environment()

        if not ll_vms.addSnapshot(True, self.vm_name, self.snap_desc):
            errors.SnapshotException(
                "Failed to create snapshot %s" % self.snap_desc
            )
        wait_for_jobs()

        self._secure_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )

    @polarion("RHEVM3-5300")
    def test_detach_attach_new_domain(self):
        """
        - create vm + disk
        - install OS, create snapshot
        - detach the domain
        - attach data domain and register the vm
        - verify snapshot exists
        - preview snapshot
        - create vm from snapshot
        """
        logger.info("Attaching storage domain %s", self.non_master)
        storagedomains.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        wait_for_jobs()

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        logger.info("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            unregistered_vms[0], cluster=config.CLUSTER_NAME
        )
        wait_for_jobs()

        assert self.snap_desc in [
            snap.get_description() for snap in ll_vms.get_vm_snapshots(
                self.vm_name
            )
        ]
        self.previewed = ll_vms.preview_snapshot(
            True, self.vm_name, self.snap_desc, ensure_vm_down=True
        )
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, config.SNAPSHOT_IN_PREVIEW, self.snap_desc
        )
        assert self.previewed
        ll_vms.undo_snapshot_preview(True, self.vm_name)
        ll_vms.wait_for_vm_snapshots(
            self.vm_name, config.SNAPSHOT_OK, self.snap_desc
        )
        self.previewed = False

        logger.info(
            "Creating vm %s from snapshot %s", self.cloned_vm, self.snap_desc
        )
        assert ll_vms.cloneVmFromSnapshot(
            True, name=self.cloned_vm, cluster=config.CLUSTER_NAME,
            vm=self.vm_name, snapshot=self.snap_desc,
            storagedomain=self.non_master,
        )

    def tearDown(self):
        if self.previewed:
            if not ll_vms.undo_snapshot_preview(True, self.vm_name):
                logger.error("Failed to undo snapshot of vm")
                self.test_failed = True
            ll_vms.wait_for_vm_snapshots(
                self.vm_name, [config.SNAPSHOT_OK], [self.snap_desc]
            )
        if not ll_vms.removeVm(True, self.cloned_vm, stopVM=True):
            logger.error("Failed to remove cloned vm %s", self.cloned_vm)
            self.test_failed = True
        wait_for_jobs()
        if not ll_vms.removeSnapshot(True, self.vm_name, self.snap_desc):
            logger.error("Failed to remove snapshot %s", self.snap_desc)
            self.test_failed = True
        wait_for_jobs()
        target_domain = ll_disks.get_other_storage_domain(
            ll_vms.getVmDisks(self.vm_name)[0].get_alias(), self.vm_name
        )
        for vm_disk in [
                disk.get_alias() for disk in ll_vms.getVmDisks(self.vm_name)
        ]:
                ll_vms.move_vm_disk(self.vm_name, vm_disk, target_domain)
        wait_for_jobs()
        self.teardown_exception()


@attr(tier=3)
class TestCase5302(BasicEnvironment):
    """
    IP block during import domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_Between_DifferentSetups
    """
    __test__ = True
    polarion_test_case = '5302'

    def setUp(self):
        self.imported = False
        super(TestCase5302, self).setUp()

        self._secure_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        self.host_ip = ll_hosts.getHostIP(config.HOSTS[0])

    @polarion("RHEVM3-5302")
    def test_block_connection_during_import(self):
        """
        - verify that there are no IP blocks from vdsm->engine
          or engine->vdsm
        - import data domain to another DC
        - during the operation add IP block from host to engine's IP
        """
        logger.info('Checking if domain %s is attached to dc %s',
                    self.non_master, config.DATA_CENTER_NAME)

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )

        if self.non_master not in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]:
            logger.info(
                'Attaching domain %s to dc %s' % (
                    self.non_master, config.DATA_CENTER_NAME
                )
            )
            ll_sd.attachStorageDomain(
                True, config.DATA_CENTER_NAME, self.non_master, wait=False
            )

            assert utils.blockOutgoingConnection(
                self.host_ip, config.HOSTS_USER, config.HOSTS_PW, config.VDC
            )

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )
        if self.non_master in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]:
            self.imported = True
            # TODO: Expected results are not clear

    def tearDown(self):
        utils.unblockOutgoingConnection(
            self.host_ip, config.HOSTS_USER, config.HOSTS_PW, config.VDC
        )
        ll_datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)
        if self.imported:
            logger.info(
                'Activating domain %s on dc %s',
                self.non_master, config.DATA_CENTER_NAME
            )

            if not ll_sd.activateStorageDomain(
                    True, config.DATA_CENTER_NAME, self.non_master
            ):
                logger.error(
                    'Unable to activate domain %s on dc %s'
                    % (self.non_master, config.DATA_CENTER_NAME)
                )
                self.test_failed = True
            logger.info('Domain %s is active' % self.non_master)

        else:
            logger.info("Attaching storage domain %s", self.non_master)
            if not storagedomains.attach_and_activate_domain(
                config.DATA_CENTER_NAME, self.non_master
            ):
                logger.error(
                    'Unable to attach and activate domain %s on dc %s'
                    % (self.non_master, config.DATA_CENTER_NAME)
                )
                self.test_failed = True
        self.teardown_exception()


@attr(tier=1)
class TestCase5193(BasicEnvironment):
    """
    test mounted meta-data files when attaching a file domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_DetachAttach
    """
    __test__ = NFS in opts['storages']
    storages = set([NFS])
    polarion_test_case = '5193'
    __test__ = config.STORAGE_TYPE is config.STORAGE_TYPE_NFS

    def setUp(self):
        super(TestCase5193, self).setUp()
        self._prepare_environment()
        self._secure_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        wait_for_jobs()

    @polarion("RHEVM3-5193")
    def test_attach_file_domain(self):
        """
        - detach an nfs domain
        - attach an nfs domain on different dc
        - register the vms
        """
        logger.info("Attaching storage domain %s", self.non_master)
        storagedomains.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        wait_for_jobs()

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        logger.info("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            unregistered_vms[0], cluster=config.CLUSTER_NAME
        )
        wait_for_jobs([ENUMS['job_detach_storage_domain']])


@attr(tier=1)
class TestCase5194(BasicEnvironment):
    """
    test lv's existence when importing a block domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_DetachAttach
    """
    __test__ = BaseTestCase.storage in config.BLOCK_TYPES
    polarion_test_case = '5194'

    def setUp(self):
        super(TestCase5194, self).setUp()
        self._prepare_environment()
        self._secure_detach_storage_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        wait_for_jobs()

    @polarion("RHEVM3-5194")
    def test_lv_exists_after_import_block_domain(self):
        """
        - detach block domain
        - attach the block domain to different dc (execute lvs,vgs)
        - register vms and disks
        """
        logger.info("Attaching storage domain %s", self.non_master)
        storagedomains.attach_and_activate_domain(
            config.DATA_CENTER_NAME, self.non_master
        )
        wait_for_jobs()

        unregistered_vms = ll_sd.get_unregistered_vms(self.non_master)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        logger.info("Unregistered vms: %s", vm_names)
        self.assertTrue(
            ll_sd.register_object(
                unregistered_vms[0], cluster=config.CLUSTER_NAME
            ),
            "Failed to register vm %s" % unregistered_vms[0]
        )
        wait_for_jobs()

        self.assertTrue(ll_vms.startVms(
            [self.vm_name], wait_for_status=config.VM_UP
        ), "VM %s failed to restart" % self.vm_name)

    def tearDown(self):
        ll_vms.stop_vms_safely([self.vm_name])
        ll_vms.waitForVMState(self.vm_name, config.VM_DOWN)
        target_domain = ll_disks.get_other_storage_domain(
            ll_vms.getVmDisks(self.vm_name)[0].get_alias(), self.vm_name
        )
        for vm_disk in [
            disk.get_alias() for disk in ll_vms.getVmDisks(self.vm_name)
        ]:
            ll_vms.move_vm_disk(self.vm_name, vm_disk, target_domain)
        wait_for_jobs()


@attr(tier=3)
class TestCase5205(CommonSetUp):
    """
    detach/attach domain during vdsm/engine restart
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_DetachAttach
    """
    __test__ = True
    polarion_test_case = '5205'

    def _restart_component(self, restart_function, *args):
        logger.info(
            'Checking if domain %s is attached to dc %s' % (
                self.non_master, config.DATA_CENTER_NAME
            )
        )

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )

        if self.non_master not in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]:
            logger.info(
                'Attaching domain %s to dc %s' % (
                    self.non_master, config.DATA_CENTER_NAME
                )
            )
            ll_sd.attachStorageDomain(
                True, config.DATA_CENTER_NAME, self.non_master, wait=False,
                compare=False
            )

            assert restart_function(*args)
            ll_datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )
        self.imported = self.non_master in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]

    @polarion("RHEVM3-5205")
    def test_restart_vdsm_during_import_domain(self):
        """
        - import data domain on different dc
        - during the operation restart vdsm
        """
        self._restart_component(
            test_utils.restartVdsmd, config.HOSTS[0], config.HOSTS_PW
        )

    @polarion("RHEVM3-5205")
    def test_restart_engine_during_import_domain(self):
        """
        - import data domain on different dc
        - Restart the engine during the Import domain operation
        """
        self._restart_component(
            test_utils.restartOvirtEngine, config.VDC_HOST, 10, 15, 300
        )

    def tearDown(self):
        if self.imported:
            logger.info('Activating domain %s on dc %s'
                        % (self.non_master, config.DATA_CENTER_NAME))

            if not ll_sd.activateStorageDomain(
                    True, config.DATA_CENTER_NAME, self.non_master
            ):
                logger.error(
                    'Unable to activate domain %s on dc %s'
                    % (self.non_master, config.DATA_CENTER_NAME)
                )
                self.test_failed = True
            logger.info('Domain %s is active' % self.non_master)

        else:
            logger.info("Attaching storage domain %s", self.non_master)
            storagedomains.attach_and_activate_domain(
                config.DATA_CENTER_NAME, self.non_master
            )
        self.teardown_exception()


@attr(tier=3)
class TestCase5304(CommonSetUp):
    """
    Import domain during host reboot
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_Between_DifferentSetups
    """
    __test__ = True
    polarion_test_case = '5304'
    bz = {'1210771': {'engine': ['rest', 'sdk'], 'version': ["3.5", "3.6"]}}

    @polarion("RHEVM3-5304")
    def test_reboot_host_during_import_domain(self):
        """
        - Import data domain to different dc
        - Reboot host during the Import domain operation
        """
        logger.info('Checking if domain %s is attached to dc %s'
                    % (self.non_master, config.DATA_CENTER_NAME))

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )

        if self.non_master not in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]:
            logger.info(
                'Attaching domain %s to dc %s' % (
                    self.non_master, config.DATA_CENTER_NAME
                )
            )
            ll_sd.attachStorageDomain(
                True, config.DATA_CENTER_NAME, self.non_master, wait=False
            )

        assert ll_hosts.rebootHost(
            True, config.HOSTS[0], config.HOSTS_USER, config.HOSTS_PW
        )
        ll_datacenters.waitForDataCenterState(config.DATA_CENTER_NAME)

        non_master_domains = ll_sd.findNonMasterStorageDomains(
            True, config.DATA_CENTER_NAME
        )
        self.imported = self.non_master in [
            sd['nonMasterDomains'] for sd in non_master_domains
        ]
        self.assertFalse(
            self.imported, "Storage domain %s was imported" % self.non_master
        )

    def tearDown(self):
        if self.imported:
            logger.info('Activating domain %s on dc %s'
                        % (self.non_master, config.DATA_CENTER_NAME))

            if not ll_sd.activateStorageDomain(
                    True, config.DATA_CENTER_NAME, self.non_master
            ):
                logger.error(
                    'Unable to activate domain %s on dc %s'
                    % (self.non_master, config.DATA_CENTER_NAME)
                )
                self.test_failed = True
            logger.info('Domain %s is active' % self.non_master)

        else:
            logger.info("Attaching storage domain %s", self.non_master)
            storagedomains.attach_and_activate_domain(
                config.DATA_CENTER_NAME, self.non_master
            )

        self.register_vm(config.VM_NAME)
        wait_for_jobs()
        self.teardown_exception()


@attr(tier=1)
class TestCase5201(BasicEnvironment):
    """
    Initialize DC from an unattached imported domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_DetachAttach
    TODO: __test__ = False due to
    which is needed for importing block storage domain
    """
    __test__ = False
    polarion_test_case = '5201'
    dc_name = 'test_dc'
    cluster_name = 'test_cluster'

    def setUp(self):
        self.test_vm = 'test_vm_%s' % self.polarion_test_case
        super(TestCase5201, self).setUp()
        self._add_storage()
        self._create_environment(self.dc_name, self.cluster_name)

        vmArgs['storageDomainName'] = self.sd_name
        vmArgs['vmName'] = self.test_vm
        vmArgs['vmDescription'] = self.test_vm
        vmArgs['installation'] = False
        self.vm_created = storage_helpers.create_vm_or_clone(**vmArgs)

        if not self.vm_created:
            raise errors.VMException(
                'Unable to create vm %s for test' % self.test_vm
            )
        self._secure_detach_storage_domain(
            config.DATA_CENTER_NAME, self.sd_name
        )
        if not ll_sd.removeStorageDomain(
                True, self.sd_name, self.spm, format='false'
        ):
            raise errors.StorageDomainException(
                "Failed to remove storage domain" % self.sd_name)

    @polarion("RHEVM3-5201")
    def test_initialize_dc_with_imported_domain(self):
        """
        - Configure 2 DCs: DC1 with 2 storage domains
          and DC2 without a storage domain
        - Create a VM with a disk on the non-master domain in DC1
        - Detach the domain which holds the disk from DC1
        - Remove it from the setup
        - Import it back again
        - Attach the domain to DC2 as the first domain (initialize DC)
        - Import the VM to DC2
        """
        status = False
        if self.storage == config.STORAGE_TYPE_ISCSI:
            status = ll_sd.importBlockStorageDomain(
                self.spm, lun_address=config.UNUSED_LUNS["lun_addresses"][0],
                lun_target=config.UNUSED_LUNS["lun_targets"][0]
            )

        elif self.storage == config.STORAGE_TYPE_NFS:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, NFS,
                config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_DATA_DOMAIN_PATHS[0], self.spm
            )
        elif self.storage == config.STORAGE_TYPE_GLUSTER:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, config.STORAGE_TYPE_GLUSTER,
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0], self.spm
            )
        self.assertTrue(status, "Failed to import storage domain")
        logger.info("Attaching storage domain %s", self.sd_name)
        storagedomains.attach_and_activate_domain(
            self.dc_name, self.sd_name
        )
        wait_for_jobs()

        unregistered_vms = ll_sd.get_unregistered_vms(self.sd_name)
        vm_names = [vm.get_name() for vm in unregistered_vms]
        logger.info("Unregistered vms: %s", vm_names)
        assert ll_sd.register_object(
            unregistered_vms[0], cluster=self.cluster_name
        )
        wait_for_jobs()

    def tearDown(self):
        self._clean_environment(
            self.dc_name, self.cluster_name, self.storage_domain
        )
        self.teardown_exception()


@attr(tier=1)
class TestCase12207(BasicEnvironment):
    """
    Initialize DC from a destroyed domain
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_5_Storage_ImportDomain_DetachAttach

    TODO: __test__ = False due to
    https://projects.engineering.redhat.com/browse/RHEVM-2141
    which is needed for importing block storage domain
    """
    __test__ = False
    polarion_test_case = '12207'
    dc_name = 'test_dc'
    cluster_name = 'test_cluster'

    def setUp(self):
        self.test_vm = 'test_vm_%s' % self.polarion_test_case
        super(TestCase12207, self).setUp()
        self._add_storage()
        self._create_environment(self.dc_name, self.cluster_name)

        vmArgs['storageDomainName'] = self.sd_name
        vmArgs['vmName'] = self.test_vm
        vmArgs['vmDescription'] = self.test_vm
        vmArgs['installation'] = False
        self.vm_created = storage_helpers.create_vm_or_clone(**vmArgs)

        if not self.vm_created:
            raise errors.VMException(
                'Unable to create vm %s for test' % self.test_vm
            )
        test_utils.wait_for_tasks(
            config.VDC, config.VDC_PASSWORD, config.DATA_CENTER_NAME
        )
        logger.info(
            'Deactivating domain  %s in dc %s', self.sd_name,
            config.DATA_CENTER_NAME
        )
        if not ll_sd.deactivateStorageDomain(
                True, config.DATA_CENTER_NAME, self.sd_name
        ):
            raise errors.StorageDomainException(
                'Unable to deactivate domain %s on dc %s',
                self.sd_name, config.DATA_CENTER_NAME
            )
        host_to_use = getSPMHost(config.HOSTS)
        if not ll_sd.removeStorageDomain(
                True, self.sd_name, host_to_use, destroy=True
        ):
            raise errors.StorageDomainException(
                "Failed to destroy storage domain" % self.sd_name)

    def test_initialize_dc_with_destroyed_domain(self):
        """
        - Configure 2 DCs: DC1 with 2 storage domains
          and DC2 without a storage domain
        - Create a VM with a disk on the non-master domain in DC1
        - Destroy the domain which holds the disk from DC1
        - Import it back again
        - Attach the domain to DC2 as the first domain (initialize DC)
        """
        status = False
        if self.storage == config.STORAGE_TYPE_ISCSI:
            status = ll_sd.importBlockStorageDomain(
                self.spm, lun_address=config.UNUSED_LUNS["lun_addresses"][0],
                lun_target=config.UNUSED_LUNS["lun_targets"][0]
            )

        elif self.storage == config.STORAGE_TYPE_NFS:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, NFS,
                config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_DATA_DOMAIN_PATHS[0], self.spm
            )
        elif self.storage == config.STORAGE_TYPE_GLUSTER:
            status = ll_sd.importStorageDomain(
                True, config.TYPE_DATA, config.STORAGE_TYPE_GLUSTER,
                config.UNUSED_GLUSTER_DATA_DOMAIN_ADDRESSES[0],
                config.UNUSED_GLUSTER_DATA_DOMAIN_PATHS[0], self.spm
            )
        self.assertTrue(status, "Failed to import storage domain")
        logger.info("Attaching storage domain %s", self.sd_name)
        self.assertRaises(
            errors.StorageDomainException,
            storagedomains.attach_and_activate_domain(
                self.dc_name, self.sd_name
            ), "Initialize data center with destroyed domain should fail"
        )

    def tearDown(self):
        self._clean_environment(
            self.dc_name, self.cluster_name, self.storage_domain
        )
        self.teardown_exception()
