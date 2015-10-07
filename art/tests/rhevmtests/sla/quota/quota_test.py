"""
Quota Test
Check different cases for quota limitations in None, Audit and Enforce mode
Include CRUD tests, different limitations of storage, memory and vcpu tests
"""
import logging
import unittest2

from art.unittest_lib import attr
from rhevmtests.sla.quota import config as c
import art.test_handler.exceptions as errors
from art.unittest_lib import SlaTest as TestCase
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.high_level.disks as hl_disks
import art.rhevm_api.tests_lib.low_level.events as ll_events
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters

from art.test_handler.tools import polarion, bz  # pylint: disable=E0611

logger = logging.getLogger(__name__)


class BaseQuotaClass(TestCase):
    """
    Base Quota Class
    """
    __test__ = False

    @classmethod
    def _create_quota_limits(
        cls, dc_name, quota_name,
        quota_cluster_limit=None,
        quota_storage_limit=None
    ):
        """
        Create quota limits on specific quota

        :param dc_name: datacenter name
        :type dc_name: str
        :param quota_name: name of quota
        :type quota_name: str
        :param quota_cluster_limit: quota cluster limit dictionary
        :type quota_cluster_limit: dict
        :param quota_storage_limit: quota storage limit dictionary
        :type quota_storage_limit: dict
        :return: True, if create quota limits action succeeds, otherwise False
        :rtype: bool
        """
        if quota_cluster_limit:
            logger.info(
                "Create cluster limitation %s under quota %s",
                quota_cluster_limit, quota_name
            )
            if not ll_datacenters.create_quota_limits(
                dc_name=dc_name,
                quota_name=quota_name,
                limit_type=c.LIMIT_TYPE_CLUSTER,
                limits_d=quota_cluster_limit
            ):
                logger.error(
                    "Failed to create cluster limitation under quota %s",
                    quota_name
                )
                return False

        if quota_storage_limit:
            logger.info(
                "Create storage limitation %s under quota %s",
                quota_storage_limit, quota_name
            )
            if not ll_datacenters.create_quota_limits(
                dc_name=dc_name,
                quota_name=quota_name,
                limit_type=c.LIMIT_TYPE_STORAGE,
                limits_d=quota_storage_limit
            ):
                logger.error(
                    "Failed to create storage limitation under quota %s",
                    quota_name
                )
                return False

        return True

    @classmethod
    def _create_quota_with_limits(
        cls, dc_name, quota_name, quota_params,
        quota_cluster_limit=None,
        quota_storage_limit=None
    ):
        """
        Create quota with some limits

        :param dc_name: datacenter name
        :type dc_name: str
        :param quota_name: name of quota
        :type quota_name: str
        :param quota_params: additional quota parameters
        :type quota_params: dict
        :param quota_cluster_limit: quota cluster limit dictionary
        :type quota_cluster_limit: dict
        :param quota_storage_limit: quota storage limit dictionary
        :type quota_storage_limit: dict
        :return: True, if create quota action success, otherwise False
        :rtype: bool
        """
        logger.info(
            "Create quota %s under datacenter %s", quota_name, dc_name
        )
        if not ll_datacenters.create_dc_quota(
                dc_name=dc_name, quota_name=quota_name, **quota_params
        ):
            logger.error(
                "Failed to create quota %s under datacenter %s",
                quota_name, dc_name
            )
            return False
        if not cls._create_quota_limits(
            dc_name=dc_name,
            quota_name=quota_name,
            quota_cluster_limit=quota_cluster_limit,
            quota_storage_limit=quota_storage_limit
        ):
            return False
        return True


@attr(tier=1)
class QuotaTestCRUD(BaseQuotaClass):
    """
    Quota CRUD test
    """
    __test__ = True

    @polarion("RHEVM3-9375")
    def test_a_create_quota(self):
        """
        Create Quota with some limits
        """
        logger.info(
            "Create quota %s with cluster and storage limits", c.QUOTA2_NAME
        )
        self.assertTrue(
            self._create_quota_with_limits(
                dc_name=c.DC_NAME_0,
                quota_name=c.QUOTA2_NAME,
                quota_params={"description": c.QUOTA2_DESC},
                quota_cluster_limit={
                    None: {c.VCPU_LIMIT: 1, c.MEMORY_LIMIT: 1024}
                },
                quota_storage_limit={None: {c.STORAGE_LIMIT: 10}}
            )
        )

    @polarion("RHEVM3-9390")
    def test_b_update_quota(self):
        """
        Update quota
        """
        logger.info("Update quota %s description", c.QUOTA2_NAME)
        self.assertTrue(
            ll_datacenters.update_dc_quota(
                dc_name=c.DC_NAME_0,
                quota_name=c.QUOTA2_NAME,
                description=c.QUOTA_DESC
            ),
            "Failed to update quota %s description" % c.QUOTA2_NAME
        )

        logger.info("Update quota %s limits", c.QUOTA2_NAME)
        self.assertTrue(
            self._create_quota_limits(
                dc_name=c.DC_NAME_0,
                quota_name=c.QUOTA2_NAME,
                quota_cluster_limit={
                    None: {c.VCPU_LIMIT: 2, c.MEMORY_LIMIT: 2048}
                },
                quota_storage_limit={None: {c.STORAGE_LIMIT: 20}}
            )
        )

    @polarion("RHEVM3-9391")
    def test_c_delete_quota(self):
        """
        Delete Quota
        """
        logger.info(
            "Remove quota %s from datacenter %s", c.QUOTA2_NAME, c.DC_NAME_0
        )
        self.assertTrue(
            ll_datacenters.delete_dc_quota(
                dc_name=c.DC_NAME_0,
                quota_name=c.QUOTA2_NAME
            ),
            "Failed to delete quota %s from datacenter %s" %
            (c.QUOTA2_NAME, c.DC_NAME_0)
        )


@attr(tier=2)
class QuotaTestMode(BaseQuotaClass):
    """
    This unittest class tests quota enforced/audit mode
    """
    __test__ = False
    quota_mode = None
    quota_storage_limit = {None: {c.STORAGE_LIMIT: 20}}
    quota_cluster_limit = {None: {c.MEMORY_LIMIT: 1, c.VCPU_LIMIT: 1}}
    cluster_hard_limit_pct = None

    def _check_hotplug(self, vm_state, audit_msg_type, vm_sockets):
        """
        Check VM CPU hotplug, under different quota modes

        :param vm_state: vm state
        :type vm_state: str
        :param audit_msg_type: type of quota audit message
        :type audit_msg_type: str
        :param vm_sockets: number of vm sockets
        :type vm_sockets: int
        :raise: assertError
        """
        max_id = ll_events.get_max_event_id(None)
        logger.info("Start vm %s", c.VM_NAME)
        self.assertTrue(
            ll_vms.startVm(
                positive=True, vm=c.VM_NAME, wait_for_status=vm_state
            ),
            "Failed to start vm %s" % c.VM_NAME
        )

        compare = False if self.quota_mode == c.QUOTA_ENFORCED_MODE else True
        logger.info(
            "Update vm %s number of cpu sockets to %d", c.VM_NAME, vm_sockets
        )
        self.assertTrue(
            ll_vms.updateVm(
                positive=True,
                vm=c.VM_NAME,
                cpu_socket=vm_sockets,
                compare=compare
            ),
            "Failed to update vm %s" % c.VM_NAME
        )

        logger.info("Check quota message under events")
        self.assertTrue(self._check_quota_message(max_id, audit_msg_type))

    def _check_quota_message(self, max_id, audit_msg_type):
        """
        Check quota event message

        :param max_id: id of last event
        :type max_id: str
        :param audit_msg_type: type of quota event message
        :type audit_msg_type: str
        :return: True, if exist quota message, with id greater than max_id,
        otherwise False
        :rtype: bool
        """
        message = c.QUOTA_EVENTS[self.quota_mode][audit_msg_type]
        logger.info(
            "Waiting for event with message %s, after event with id %s",
            message, max_id
        )
        return ll_events.wait_for_event(message, start_id=max_id)

    def _check_cluster_limits(self, vm_params=None, audit_msg_type=None):
        """
        Check if vm can run under specific quota cluster limits and
        if correct audit message appear under events

        :param vm_params: update vm with given parameters
        :type vm_params: dict
        :param audit_msg_type: type of quota audit message
        :type audit_msg_type: str
        :raise: assertError
        """
        last_event_id = None
        if audit_msg_type:
            logger.info("Get id of last event")
            last_event_id = ll_events.get_max_event_id(None)
        if vm_params:
            logger.info(
                "Update vm %s with parameters: %s", c.VM_NAME, vm_params
            )
            self.assertTrue(
                ll_vms.updateVm(
                    positive=True, vm=c.VM_NAME, **vm_params
                ),
                "Failed to update vm %s" % c.VM_NAME
            )
        positive = True
        if (
            audit_msg_type and audit_msg_type == c.EXCEED_TYPE and
            self.quota_mode == c.QUOTA_ENFORCED_MODE
        ):
            positive = False
        logger.info("Start vm %s", c.VM_NAME)
        self.assertTrue(
            ll_vms.startVm(positive=positive, vm=c.VM_NAME),
            "Failed to start vm %s" % c.VM_NAME
        )
        if last_event_id:
            logger.info(
                "Check if quota message of type %s, appear under events",
                audit_msg_type
            )
            self.assertTrue(
                self._check_quota_message(last_event_id, audit_msg_type),
                "Quota message of type %s not appear under events" %
                audit_msg_type
            )

    def _check_storage_limit(self, provisioned_size, audit_msg_type=None):
        """
        Check if vm can run under specific quota storage limits and
        if correct audit message appear under events

        :param provisioned_size: size of disk
        :type provisioned_size: int
        :param audit_msg_type: type of quota audit message
        :type audit_msg_type: str
        :raise: assertError
        """
        last_event_id = None
        if audit_msg_type:
            logger.info("Get id of last event")
            last_event_id = ll_events.get_max_event_id(None)
        positive = True
        if (
            audit_msg_type and audit_msg_type == c.EXCEED_TYPE and
            self.quota_mode == c.QUOTA_ENFORCED_MODE
        ):
            positive = False
        logger.info("Get quota %s id", c.QUOTA_NAME)
        q_id = ll_datacenters.get_quota_id_by_name(
            dc_name=c.DC_NAME_0, quota_name=c.QUOTA_NAME
        )
        logger.info(
            "Add new disk %s with size of %d", c.DISK_NAME, provisioned_size
        )
        self.assertTrue(
            ll_disks.addDisk(
                positive=positive,
                alias=c.DISK_NAME,
                provisioned_size=provisioned_size,
                interface=c.DISK_INTERFACE,
                format=c.DISK_FORMAT_COW,
                storagedomain=c.STORAGE_NAME[0],
                quota=q_id
            ),
            "Failed to add new disk %s" % c.DISK_NAME
        )
        if last_event_id:
            logger.info(
                "Check if quota message of type %s, appear under events",
                audit_msg_type
            )
            self.assertTrue(
                self._check_quota_message(last_event_id, audit_msg_type),
                "Quota message of type %s not appear under events" %
                audit_msg_type
            )

    def check_limit_usage(self, limit_type, usage_type, usage):
        """
        Check if quota limit have correct value

        :param limit_type: limit type(cluster or storage)
        :type limit_type: str
        :param usage_type: usage type
        (storage: usage; cluster: vcpu_usage, memory_usage)
        :type usage_type: str
        :param usage: expected quota cluster limit usage
        :type usage: float
        """
        quota_limit_usage = ll_datacenters.get_quota_limit_usage(
            dc_name=c.DC_NAME_0,
            quota_name=c.QUOTA_NAME,
            limit_type=limit_type,
            usage=usage_type
        )
        logger.info(
            "Check if expected %s: %s equal to quota limit %s: %s",
            usage_type, usage, usage_type, quota_limit_usage
        )
        self.assertEqual(usage, quota_limit_usage)

    @classmethod
    def setup_class(cls):
        """
        1) Update datacenter quota mode
        2) Update cluster grace value
        3) Create quota limit
        4) Create new vm for test
        """
        logger.info(
            "Update datacenter %s quota mode to %s",
            c.DC_NAME_0, c.QUOTA_MODES[cls.quota_mode]
        )
        if not ll_datacenters.updateDataCenter(
            positive=True,
            datacenter=c.DC_NAME_0,
            quota_mode=c.QUOTA_MODES[cls.quota_mode]
        ):
            raise errors.DataCenterException(
                "Failed to update datacenter %s quota mode" % c.DC_NAME_0
            )
        if cls.cluster_hard_limit_pct:
            logger.info("Update quota %s cluster grace value", c.QUOTA_NAME)
            if not ll_datacenters.update_dc_quota(
                dc_name=c.DC_NAME_0,
                quota_name=c.QUOTA_NAME,
                cluster_hard_limit_pct=cls.cluster_hard_limit_pct
            ):
                raise errors.DataCenterException(
                    "Failed to update quota %s" % c.QUOTA_NAME
                )
        logger.info(
            "Create limits on quota %s", c.QUOTA_NAME
        )
        if not cls._create_quota_limits(
            dc_name=c.DC_NAME_0,
            quota_name=c.QUOTA_NAME,
            quota_cluster_limit=cls.quota_cluster_limit,
            quota_storage_limit=cls.quota_storage_limit
        ):
            raise errors.DataCenterException(
                "Failed to create cluster memory limit on quota %s" %
                c.QUOTA_NAME
            )
        logger.info("Get quota %s id", c.QUOTA_NAME)
        q_id = ll_datacenters.get_quota_id_by_name(
            dc_name=c.DC_NAME_0, quota_name=c.QUOTA_NAME
        )
        cpu_profile_id = ll_clusters.get_cpu_profile_id_by_name(
            c.CLUSTER_NAME[0], c.CLUSTER_NAME[0]
        )
        logger.info("Create new vm %s", c.VM_NAME)
        # TODO: add type as W/A for bug
        # https://bugzilla.redhat.com/show_bug.cgi?id=1253261
        # add display_type as W/A for bug
        # https://bugzilla.redhat.com/show_bug.cgi?id=1253263
        # must remove both after bugs fixed
        if not ll_vms.createVm(
            positive=True, vmName=c.VM_NAME,
            vmDescription=c.VM_DESC,
            cluster=c.CLUSTER_NAME[0],
            storageDomainName=c.STORAGE_NAME[0],
            size=c.SIZE_10_GB, memory=c.SIZE_512_MB,
            vm_quota=q_id, disk_quota=q_id, type=c.VM_TYPE_SERVER,
            nic=c.NIC_NAME[0], network=c.MGMT_BRIDGE,
            cpu_profile_id=cpu_profile_id, display_type=c.VM_DISPLAY_TYPE
        ):
            raise errors.VMException("Failed to create vm %s", c.VM_NAME)

    @classmethod
    def teardown_class(cls):
        """
        1) Stop and remove vm
        2) Delete quota limits
        3) Update quota grace value
        4) Update datacenter quota mode
        """
        ll_vms.stop_vms_safely([c.VM_NAME])
        logger.info("Remove vm %s", c.VM_NAME)
        if not ll_vms.removeVm(positive=True, vm=c.VM_NAME):
            logger.error("Failed to remove vm %s", c.VM_NAME)
        quota_limits_d = {
            c.LIMIT_TYPE_CLUSTER: cls.quota_cluster_limit,
            c.LIMIT_TYPE_STORAGE: cls.quota_storage_limit
        }
        for limit_type, limits in quota_limits_d.iteritems():
            if limits:
                logger.info(
                    "Delete %s limit on quota %s", limit_type, c.QUOTA_NAME
                )
                if not ll_datacenters.delete_quota_limits(
                    dc_name=c.DC_NAME_0,
                    quota_name=c.QUOTA_NAME,
                    limit_type=limit_type,
                    objects_names_l=[None]
                ):
                    logger.error(
                        "Failed to delete %s limit from quota %s",
                        limit_type, c.QUOTA_NAME
                    )
        logger.info("Update quota %s cluster grace value", c.QUOTA_NAME)
        if not ll_datacenters.update_dc_quota(
            dc_name=c.DC_NAME_0,
            quota_name=c.QUOTA_NAME,
            cluster_hard_limit_pct=20
        ):
            logger.error(
                "Failed to update quota %s", c.QUOTA_NAME
            )
        logger.info(
            "Update datacenter %s quota mode to %s",
            c.DC_NAME_0, c.QUOTA_MODES[c.QUOTA_NONE_MODE]
        )
        if not ll_datacenters.updateDataCenter(
            positive=True,
            datacenter=c.DC_NAME_0,
            quota_mode=c.QUOTA_MODES[c.QUOTA_NONE_MODE]
        ):
            logger.error(
                "Failed to update datacenter %s quota mode", c.DC_NAME_0
            )


class TestDeleteQuotaInUseAudit(QuotaTestMode):
    """
    Negative: Delete quota in use under audit quota
    """
    __test__ = True
    quota_mode = c.QUOTA_AUDIT_MODE

    @polarion("RHEVM3-9406")
    def test_n_delete_quota_in_use(self):
        """
        Delete quota in use
        """
        self.assertFalse(
            ll_datacenters.delete_dc_quota(
                dc_name=c.DC_NAME_0, quota_name=c.QUOTA_NAME
            )
        )


class TestDeleteQuotaInUseEnforced(QuotaTestMode):
    """
    Negative: Delete quota in use under enforced quota
    """
    __test__ = True
    quota_mode = c.QUOTA_ENFORCED_MODE

    @polarion("RHEVM3-9447")
    def test_n_delete_quota_in_use(self):
        """
        Delete quota in use
        """
        self.assertFalse(
            ll_datacenters.delete_dc_quota(
                dc_name=c.DC_NAME_0, quota_name=c.QUOTA_NAME
            )
        )


class TestQuotaCluster(QuotaTestMode):
    """
    Parent class for quota cluster limits tests
    """
    __test__ = False

    def tearDown(self):
        """
        Safely stop vm
        """
        ll_vms.stop_vms_safely(vms_list=[c.VM_NAME])
        logger.info("Update vm %s socket and cores number", c.VM_NAME)
        if not ll_vms.updateVm(
            positive=True, vm=c.VM_NAME, cpu_socket=1, cpu_cores=1
        ):
            logger.error("Failed to update vm %s", c.VM_NAME)


class TestQuotaAuditModeMemory(TestQuotaCluster):
    """
    Check cluster memory limit under audit quota
    """
    __test__ = True
    quota_mode = c.QUOTA_AUDIT_MODE
    quota_cluster_limit = {None: {c.MEMORY_LIMIT: 1, c.VCPU_LIMIT: -1}}
    cluster_hard_limit_pct = 50

    @polarion("RHEVM3-9428")
    def test_a_quota_memory_limit(self):
        """
        Check under grace memory limit
        """
        self._check_cluster_limits()

    @polarion("RHEVM3-9430")
    def test_b_quota_memory_limit_in_grace(self):
        """
        Check in grace memory limit
        """
        self._check_cluster_limits(
            vm_params={c.VM_MEMORY: c.SIZE_1280_MB},
            audit_msg_type=c.GRACE_TYPE
        )

    @polarion("RHEVM3-9433")
    def test_c_quota_memory_limit_over_grace(self):
        """
        Check over grace memory limit
        """
        self._check_cluster_limits(
            vm_params={c.VM_MEMORY: c.SIZE_2_GB}, audit_msg_type=c.EXCEED_TYPE
        )


class TestQuotaEnforcedModeMemory(TestQuotaCluster):
    """
    Check cluster memory limit under enforced quota
    """
    __test__ = True
    quota_mode = c.QUOTA_ENFORCED_MODE
    quota_cluster_limit = {None: {c.MEMORY_LIMIT: 1, c.VCPU_LIMIT: -1}}
    cluster_hard_limit_pct = 50

    @polarion("RHEVM3-9418")
    def test_a_quota_memory_limit(self):
        """
        Check under grace memory limit
        """
        self._check_cluster_limits()

    @polarion("RHEVM3-9419")
    def test_b_quota_memory_limit_in_grace(self):
        """
        Check in grace memory limit
        """
        self._check_cluster_limits(
            vm_params={c.VM_MEMORY: c.SIZE_1280_MB},
            audit_msg_type=c.GRACE_TYPE
        )

    @polarion("RHEVM3-9409")
    def test_c_quota_memory_limit_over_grace(self):
        """
        Check over grace memory limit
        """
        self._check_cluster_limits(
            vm_params={c.VM_MEMORY: c.SIZE_2_GB}, audit_msg_type=c.EXCEED_TYPE
        )


class TestQuotaAuditModeCPU(TestQuotaCluster):
    """
    Check cluster vcpu limit under audit quota
    """
    __test__ = True
    quota_mode = c.QUOTA_AUDIT_MODE
    quota_cluster_limit = {
        None: {
            c.VCPU_LIMIT: c.MINIMAL_CPU_LIMIT,
            c.MEMORY_LIMIT: c.DEFAULT_MEMORY_LIMIT
        }
    }
    cluster_hard_limit_pct = 100

    @polarion("RHEVM3-9434")
    def test_a_quota_vcpu_limit(self):
        """
        Check under grace vcpu limit
        """
        self._check_cluster_limits()

    @polarion("RHEVM3-9437")
    def test_b_quota_vcpu_limit_in_grace(self):
        """
        Check in grace vcpu limit
        """
        self._check_cluster_limits(
            vm_params={c.VM_CPU_CORES: c.NUM_OF_CPUS[c.GRACE_TYPE]},
            audit_msg_type=c.GRACE_TYPE
        )

    @unittest2.skipIf(c.PPC_ARCH, c.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-9438")
    def test_c_quota_vcpu_limit_over_grace(self):
        """
        Check over grace vcpu limit
        """
        self._check_cluster_limits(
            vm_params={c.VM_CPU_CORES: c.NUM_OF_CPUS[c.EXCEED_TYPE]},
            audit_msg_type=c.EXCEED_TYPE
        )

    @unittest2.skipIf(c.PPC_ARCH, c.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12366")
    def test_d_quota_vcpu_hotplug_in_grace_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(c.VM_UP, c.GRACE_TYPE, c.NUM_OF_CPUS[c.GRACE_TYPE])

    @unittest2.skipIf(c.PPC_ARCH, c.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12367")
    def test_e_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            c.VM_UP, c.EXCEED_TYPE, c.NUM_OF_CPUS[c.EXCEED_TYPE]
        )

    @unittest2.skipIf(c.PPC_ARCH, c.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12364")
    @bz({"1167081": {c.BZ_ENGINE: None, c.BZ_VERSION: [c.VERSION_35]}})
    def test_f_quota_vcpu_hotplug_in_grace_vm_powering_up(self):
        """
        Hotplug additional vCPU, when vm is powering up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(
            c.VM_POWER_UP, c.GRACE_TYPE, c.NUM_OF_CPUS[c.GRACE_TYPE]
        )

    @unittest2.skipIf(c.PPC_ARCH, c.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12365")
    @bz({"1167081": {c.BZ_ENGINE: None, c.BZ_VERSION: [c.VERSION_35]}})
    def test_g_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm is powering up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            c.VM_POWER_UP, c.EXCEED_TYPE, c.NUM_OF_CPUS[c.EXCEED_TYPE]
        )


class TestQuotaEnforcedModeCPU(TestQuotaCluster):
    """
    Check cluster vcpu limit under enforced quota
    """
    __test__ = True
    quota_mode = c.QUOTA_ENFORCED_MODE
    quota_cluster_limit = {
        None: {
            c.VCPU_LIMIT: c.MINIMAL_CPU_LIMIT,
            c.MEMORY_LIMIT: c.DEFAULT_MEMORY_LIMIT
        }
    }
    cluster_hard_limit_pct = 100

    @polarion("RHEVM3-9408")
    def test_a_quota_vcpu_limit(self):
        """
        Check under grace vcpu limit
        """
        self._check_cluster_limits()

    @polarion("RHEVM3-9402")
    def test_b_quota_vcpu_limit_in_grace(self):
        """
        Check in grace vcpu limit
        """
        self._check_cluster_limits(
            vm_params={c.VM_CPU_CORES: c.NUM_OF_CPUS[c.GRACE_TYPE]},
            audit_msg_type=c.GRACE_TYPE
        )

    @polarion("RHEVM3-9403")
    def test_c_quota_vcpu_limit_over_grace(self):
        """
        Check over grace vcpu limit
        """
        self._check_cluster_limits(
            vm_params={c.VM_CPU_CORES: c.NUM_OF_CPUS[c.EXCEED_TYPE]},
            audit_msg_type=c.EXCEED_TYPE
        )

    @unittest2.skipIf(c.PPC_ARCH, c.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12370")
    def test_d_quota_vcpu_hotplug_in_grace_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(
            c.VM_UP, c.GRACE_TYPE, c.NUM_OF_CPUS[c.GRACE_TYPE]
        )

    @unittest2.skipIf(c.PPC_ARCH, c.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12371")
    def test_e_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            c.VM_UP, c.EXCEED_TYPE, c.NUM_OF_CPUS[c.EXCEED_TYPE]
        )

    @unittest2.skipIf(c.PPC_ARCH, c.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12368")
    @bz({"1167081": {c.BZ_ENGINE: None, c.BZ_VERSION: [c.VERSION_35]}})
    def test_f_quota_vcpu_hotplug_in_grace_vm_powering_up(self):
        """
        Hotplug additional vCPU, when vm is powering up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(
            c.VM_POWER_UP, c.GRACE_TYPE, c.NUM_OF_CPUS[c.GRACE_TYPE]
        )

    @unittest2.skipIf(c.PPC_ARCH, c.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12369")
    @bz({"1167081": {c.BZ_ENGINE: None, c.BZ_VERSION: [c.VERSION_35]}})
    def test_g_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm is powering up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            c.VM_POWER_UP, c.EXCEED_TYPE, c.NUM_OF_CPUS[c.EXCEED_TYPE]
        )


class TestQuotaStorage(QuotaTestMode):
    """
    Base class to check quota storage limits
    """
    __test__ = False

    def tearDown(self):
        """
        If disk exist, remove it
        """
        logger.info("Check if disk %s exist", c.DISK_NAME)
        if ll_disks.checkDiskExists(True, c.DISK_NAME):
            logger.info("Delete disk %s", c.DISK_NAME)
            if not hl_disks.delete_disks([c.DISK_NAME]):
                logger.error("Failed to remove disk %s", c.DISK_NAME)


class TestQuotaAuditModeStorage(TestQuotaStorage):
    """
    Check storage limitation under audit quota
    """
    __test__ = True
    quota_mode = c.QUOTA_AUDIT_MODE

    @polarion("RHEVM3-9440")
    def test_a_quota_storage_limit(self):
        """
        Check under grace storage limit
        """
        self._check_storage_limit(provisioned_size=c.SIZE_10_GB)

    @polarion("RHEVM3-9443")
    def test_b_quota_storage_limit_in_grace(self):
        """
        Check in grace storage limit
        """
        self._check_storage_limit(
            provisioned_size=c.SIZE_14_GB, audit_msg_type=c.GRACE_TYPE
        )

    @polarion("RHEVM3-9446")
    def test_c_quota_storage_limit_over_grace(self):
        """
        Check over grace storage limit
        """
        self._check_storage_limit(
            provisioned_size=c.SIZE_15_GB, audit_msg_type=c.EXCEED_TYPE
        )


class TestQuotaEnforcedModeStorage(TestQuotaStorage):
    """
    Check storage limitation under audit quota
    """
    __test__ = True
    quota_mode = c.QUOTA_ENFORCED_MODE

    @polarion("RHEVM3-9405")
    def test_a_quota_storage_limit(self):
        """
        Check under grace storage limit
        """
        self._check_storage_limit(provisioned_size=c.SIZE_10_GB)

    @polarion("RHEVM3-9407")
    def test_b_quota_storage_limit_in_grace(self):
        """
        Check in grace storage limit
        """
        self._check_storage_limit(
            provisioned_size=c.SIZE_14_GB, audit_msg_type=c.GRACE_TYPE
        )

    @polarion("RHEVM3-9404")
    def test_c_quota_storage_limit_over_grace(self):
        """
        Check over grace storage limit
        """
        self._check_storage_limit(
            provisioned_size=c.SIZE_15_GB, audit_msg_type=c.EXCEED_TYPE
        )


class TestQuotaConsumptionRunOnceVM(QuotaTestMode):
    """
    Run vm once and check quota consumption
    """
    __test__ = True
    quota_mode = c.QUOTA_AUDIT_MODE
    quota_cluster_limit = {
        None: {
            c.VCPU_LIMIT: c.DEFAULT_CPU_LIMIT,
            c.MEMORY_LIMIT: c.DEFAULT_MEMORY_LIMIT
        }
    }

    @polarion("RHEVM3-9396")
    def test_run_vm_once(self):
        """
        Run vm once and check quota consumption
        """
        logger.info("Run once vm %s", c.VM_NAME)
        self.assertTrue(
            ll_vms.runVmOnce(positive=True, vm=c.VM_NAME),
            "Failed to run vm %s once" % c.VM_NAME
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.MEMORY_USAGE,
            usage=c.DEFAULT_MEMORY_USAGE
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.VCPU_USAGE,
            usage=c.DEFAULT_CPU_USAGE
        )


class TestQuotaConsumptionSnapshot(QuotaTestMode):
    """
    Make snapshot and check quota consumption
    """
    __test__ = True
    quota_mode = c.QUOTA_AUDIT_MODE

    @polarion("RHEVM3-9397")
    def test_make_snapshot(self):
        """
        Make snapshot and check quota consumption
        """
        logger.info("Start vm %s", c.VM_NAME)
        self.assertTrue(
            ll_vms.startVm(positive=True, vm=c.VM_NAME),
            "Failed to start vm %s" % c.VM_NAME
        )
        logger.info("Create snapshot from vm %s", c.VM_NAME)
        self.assertTrue(
            ll_vms.addSnapshot(
                positive=True, vm=c.VM_NAME, description=c.VM_SNAPSHOT
            ),
            "Failed to create snapshot from vm %s" % c.VM_NAME
        )
        quota_limit_usage = ll_datacenters.get_quota_limit_usage(
            dc_name=c.DC_NAME_0,
            quota_name=c.QUOTA_NAME,
            limit_type=c.LIMIT_TYPE_STORAGE,
            usage=c.STORAGE_USAGE
        )
        logger.info(
            "Check if quota %s storage usage greater than %dGB",
            c.QUOTA_NAME, c.DEFAULT_DISK_USAGE
        )
        self.assertTrue(
            quota_limit_usage > c.DEFAULT_DISK_USAGE,
            "Quota %s storage usage less or equal to %d" %
            (c.QUOTA_NAME, c.DEFAULT_DISK_USAGE)
        )


class TestQuotaConsumptionTemplate(QuotaTestMode):
    """
    Create template from vm, remove it and check quota consumption
    """
    __test__ = True
    quota_mode = c.QUOTA_AUDIT_MODE

    @polarion("RHEVM3-9394")
    def test_a_template_consumption(self):
        """
        Create template from vm, remove it and check quota consumption
        """
        logger.info("Create template from vm %s", c.VM_NAME)
        self.assertTrue(
            ll_templates.createTemplate(
                positive=True, vm=c.VM_NAME,
                name=c.TEMPLATE_NAME, cluster=c.CLUSTER_NAME[0]
            ),
            "Failed to create template from vm %s" % c.VM_NAME
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_STORAGE,
            usage_type=c.STORAGE_USAGE,
            usage=c.FULL_DISK_USAGE
        )
        logger.info("Remove template %s", c.TEMPLATE_NAME)
        self.assertTrue(
            ll_templates.removeTemplate(
                positive=True, template=c.TEMPLATE_NAME
            ),
            "Failed to remove template %s" % c.TEMPLATE_NAME
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_STORAGE,
            usage_type=c.STORAGE_USAGE,
            usage=c.DEFAULT_DISK_USAGE
        )

    @classmethod
    def teardown_class(cls):
        """
        Check if template still exist and remove it
        """
        logger.info("Check if template %s exist", c.TEMPLATE_NAME)
        if ll_templates.check_template_existence(c.TEMPLATE_NAME):
            logger.info("Try to remove template %s", c.TEMPLATE_NAME)
            if not ll_templates.removeTemplate(
                positive=True, template=c.TEMPLATE_NAME
            ):
                logger.error("Failed to remove template %s", c.TEMPLATE_NAME)
        super(TestQuotaConsumptionTemplate, cls).teardown_class()


class TestQuotaConsumptionVmWithDisk(QuotaTestMode):
    """
    Create and remove vm with disk and check quota consumption
    """
    __test__ = True
    quota_mode = c.QUOTA_AUDIT_MODE

    @polarion("RHEVM3-9393")
    def test_vm_with_disk_consumption(self):
        """
        Check storage quota consumption, when add or remove vm with disk
        """
        logger.info("Get quota %s id", c.QUOTA_NAME)
        q_id = ll_datacenters.get_quota_id_by_name(
            dc_name=c.DC_NAME_0, quota_name=c.QUOTA_NAME
        )
        cpu_profile_id = ll_clusters.get_cpu_profile_id_by_name(
            c.CLUSTER_NAME[0], c.CLUSTER_NAME[0]
        )
        logger.info("Create new vm %s", c.VM_NAME)
        self.assertTrue(
            ll_vms.createVm(
                positive=True, vmName=c.TMP_VM_NAME,
                vmDescription=c.VM_DESC,
                cluster=c.CLUSTER_NAME[0],
                storageDomainName=c.STORAGE_NAME[0],
                size=c.SIZE_10_GB, memory=c.SIZE_512_MB,
                vm_quota=q_id, disk_quota=q_id,
                nic=c.NIC_NAME[0], network=c.MGMT_BRIDGE,
                cpu_profile_id=cpu_profile_id,
                display_type=c.VM_DISPLAY_TYPE
            ),
            "Failed to create new vm %s" % c.TMP_VM_NAME
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_STORAGE,
            usage_type=c.STORAGE_USAGE,
            usage=c.FULL_DISK_USAGE
        )
        logger.info("Remove vm %s", c.TMP_VM_NAME)
        self.assertTrue(
            ll_vms.removeVm(positive=True, vm=c.TMP_VM_NAME),
            "Failed to remove vm %s" % c.TMP_VM_NAME
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_STORAGE,
            usage_type=c.STORAGE_USAGE,
            usage=c.DEFAULT_DISK_USAGE
        )

    @classmethod
    def teardown_class(cls):
        """
        Check if vm exist and remove it
        """
        logger.info("Check if vm %s exist", c.TMP_VM_NAME)
        if ll_vms.does_vm_exist(vm_name=c.TMP_VM_NAME):
            logger.info("Remove vm %s", c.TMP_VM_NAME)
            if not ll_vms.removeVm(positive=True, vm=c.TMP_VM_NAME):
                logger.error("Failed to remove vm %s", c.TMP_VM_NAME)
        super(TestQuotaConsumptionVmWithDisk, cls).teardown_class()


class TestQuotaConsumptionBasicVmActions(QuotaTestMode):
    """
    Run basic vm actions and check quota consumption
    """
    __test__ = True
    quota_mode = c.QUOTA_AUDIT_MODE
    quota_cluster_limit = {
        None: {
            c.VCPU_LIMIT: c.DEFAULT_CPU_LIMIT,
            c.MEMORY_LIMIT: c.DEFAULT_MEMORY_LIMIT
        }
    }

    @polarion("RHEVM3-9395")
    def test_run_basic_vm_actions(self):
        """
        Run basic vm actions and check quota consumption
        """
        logger.info("Start vm %s", c.VM_NAME)
        self.assertTrue(
            ll_vms.startVm(positive=True, vm=c.VM_NAME),
            "Failed to start vm %s" % c.VM_NAME
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.MEMORY_USAGE,
            usage=c.DEFAULT_MEMORY_USAGE
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.VCPU_USAGE,
            usage=c.DEFAULT_CPU_USAGE
        )
        logger.info(
            "Wait until vm %s state will not equal to %s", c.VM_NAME, c.VM_UP
        )
        self.assertTrue(
            ll_vms.waitForVmsStates(positive=True, names=c.VM_NAME),
            "Vm %s still not have state %s" % (c.VM_NAME, c.VM_UP)
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.MEMORY_USAGE,
            usage=c.DEFAULT_MEMORY_USAGE
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.VCPU_USAGE,
            usage=c.DEFAULT_CPU_USAGE
        )
        logger.info("Suspend vm %s", c.VM_NAME)
        self.assertTrue(
            ll_vms.suspendVm(positive=True, vm=c.VM_NAME),
            "Failed to suspend vm %s" % c.VM_NAME
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.MEMORY_USAGE,
            usage=c.ZERO_USAGE
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.VCPU_USAGE,
            usage=c.ZERO_USAGE
        )
        logger.info("Start vm %s", c.VM_NAME)
        self.assertTrue(
            ll_vms.startVm(positive=True, vm=c.VM_NAME),
            "Failed to start vm %s" % c.VM_NAME
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.MEMORY_USAGE,
            usage=c.DEFAULT_MEMORY_USAGE
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.VCPU_USAGE,
            usage=c.DEFAULT_CPU_USAGE
        )
        logger.info("Stop vm %s", c.VM_NAME)
        self.assertTrue(
            ll_vms.stopVm(positive=True, vm=c.VM_NAME),
            "Failed to stop vm %s" % c.VM_NAME
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.MEMORY_USAGE,
            usage=c.ZERO_USAGE
        )
        self.check_limit_usage(
            limit_type=c.LIMIT_TYPE_CLUSTER,
            usage_type=c.VCPU_USAGE,
            usage=c.ZERO_USAGE
        )
