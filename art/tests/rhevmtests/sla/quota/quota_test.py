"""
Quota Test
Check different cases for quota limitations in None, Audit and Enforce mode
Include CRUD tests, different limitations of storage, memory and vcpu tests
"""
import logging
import pytest

import config as conf
from art.unittest_lib import attr
import art.test_handler.exceptions as errors
from art.unittest_lib import SlaTest as TestCase
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.high_level.disks as hl_disks
import art.rhevm_api.tests_lib.low_level.events as ll_events
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters

from art.test_handler.tools import polarion, bz

logger = logging.getLogger(__name__)


def setup_module(module):
    """
    1) Clean all events
    2) Create datacenter quota
    """
    logger.info("Remove all events from engine")
    sql = "DELETE FROM audit_log"
    conf.ENGINE.db.psql(sql)
    if not ll_datacenters.create_dc_quota(
        dc_name=conf.DC_NAME_0, quota_name=conf.QUOTA_NAME
    ):
        raise errors.DataCenterException()


def teardown_module(module):
    """
    1) Set datacenter quota mode to none
    2) Delete datacenter quota
    """
    logger.info(
        "Update datacenter %s quota mode to %s",
        conf.DC_NAME_0, conf.QUOTA_MODES[conf.QUOTA_NONE_MODE]
    )
    if not ll_datacenters.update_datacenter(
        positive=True,
        datacenter=conf.DC_NAME_0,
        quota_mode=conf.QUOTA_MODES[conf.QUOTA_NONE_MODE]
    ):
        logger.error(
            "Failed to update datacenter %s quota mode", conf.DC_NAME_0
        )
    ll_datacenters.delete_dc_quota(
        dc_name=conf.DC_NAME_0, quota_name=conf.QUOTA_NAME
    )


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
                limit_type=conf.LIMIT_TYPE_CLUSTER,
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
                limit_type=conf.LIMIT_TYPE_STORAGE,
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

    @bz({"1348559": {}})
    @polarion("RHEVM3-9375")
    def test_a_create_quota(self):
        """
        Create Quota with some limits
        """
        logger.info(
            "Create quota %s with cluster and storage limits", conf.QUOTA2_NAME
        )
        assert self._create_quota_with_limits(
            dc_name=conf.DC_NAME_0,
            quota_name=conf.QUOTA2_NAME,
            quota_params={"description": conf.QUOTA2_DESC},
            quota_cluster_limit={
                None: {conf.VCPU_LIMIT: 1, conf.MEMORY_LIMIT: 1024}
            },
            quota_storage_limit={None: {conf.STORAGE_LIMIT: 10}}
        )

    @bz({"1348559": {}})
    @polarion("RHEVM3-9390")
    def test_b_update_quota(self):
        """
        Update quota
        """
        logger.info("Update quota %s description", conf.QUOTA2_NAME)
        assert ll_datacenters.update_dc_quota(
            dc_name=conf.DC_NAME_0,
            quota_name=conf.QUOTA2_NAME,
            description=conf.QUOTA_DESC
        ), "Failed to update quota %s description" % conf.QUOTA2_NAME

        logger.info("Update quota %s limits", conf.QUOTA2_NAME)
        assert self._create_quota_limits(
            dc_name=conf.DC_NAME_0,
            quota_name=conf.QUOTA2_NAME,
            quota_cluster_limit={
                None: {conf.VCPU_LIMIT: 2, conf.MEMORY_LIMIT: 2048}
            },
            quota_storage_limit={None: {conf.STORAGE_LIMIT: 20}}
        )

    @bz({"1348559": {}})
    @polarion("RHEVM3-9391")
    def test_c_delete_quota(self):
        """
        Delete Quota
        """
        logger.info(
            "Remove quota %s from datacenter %s",
            conf.QUOTA2_NAME, conf.DC_NAME_0
        )
        assert ll_datacenters.delete_dc_quota(
            dc_name=conf.DC_NAME_0,
            quota_name=conf.QUOTA2_NAME
        ), "Failed to delete quota %s from datacenter %s" % (
            conf.QUOTA2_NAME, conf.DC_NAME_0
        )


@attr(tier=2)
class QuotaTestMode(BaseQuotaClass):
    """
    This unittest class tests quota enforced/audit mode
    """
    __test__ = False
    quota_mode = None
    quota_storage_limit = {None: {conf.STORAGE_LIMIT: 20}}
    quota_cluster_limit = {None: {conf.MEMORY_LIMIT: 1, conf.VCPU_LIMIT: 1}}
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
        max_id = ll_events.get_max_event_id()
        logger.info("Start vm %s", conf.VM_NAME)
        assert ll_vms.startVm(
            positive=True, vm=conf.VM_NAME, wait_for_status=vm_state
        ), "Failed to start vm %s" % conf.VM_NAME

        compare = (
            False if self.quota_mode == conf.QUOTA_ENFORCED_MODE else True
        )
        logger.info(
            "Update vm %s number of cpu sockets to %d",
            conf.VM_NAME, vm_sockets
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME,
            cpu_socket=vm_sockets,
            compare=compare
        ), "Failed to update vm %s" % conf.VM_NAME

        logger.info("Check quota message under events")
        assert self._check_quota_message(max_id, audit_msg_type)

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
        message = conf.QUOTA_EVENTS[self.quota_mode][audit_msg_type]
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
            last_event_id = ll_events.get_max_event_id()
        if vm_params:
            logger.info(
                "Update vm %s with parameters: %s", conf.VM_NAME, vm_params
            )
            assert ll_vms.updateVm(
                positive=True, vm=conf.VM_NAME, **vm_params
            ), "Failed to update vm %s" % conf.VM_NAME
        positive = True
        if (
            audit_msg_type and audit_msg_type == conf.EXCEED_TYPE and
            self.quota_mode == conf.QUOTA_ENFORCED_MODE
        ):
            positive = False
        logger.info("Start vm %s", conf.VM_NAME)
        assert ll_vms.startVm(
            positive=positive, vm=conf.VM_NAME
        ), "Failed to start vm %s" % conf.VM_NAME
        if last_event_id:
            logger.info(
                "Check if quota message of type %s, appear under events",
                audit_msg_type
            )
            assert self._check_quota_message(
                last_event_id, audit_msg_type
            ), "Quota message of type %s not appear under events" % (
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
            last_event_id = ll_events.get_max_event_id()
        positive = True
        if (
            audit_msg_type and audit_msg_type == conf.EXCEED_TYPE and
            self.quota_mode == conf.QUOTA_ENFORCED_MODE
        ):
            positive = False
        logger.info("Get quota %s id", conf.QUOTA_NAME)
        q_id = ll_datacenters.get_quota_id_by_name(
            dc_name=conf.DC_NAME_0, quota_name=conf.QUOTA_NAME
        )
        logger.info(
            "Add new disk %s with size of %d", conf.DISK_NAME, provisioned_size
        )
        assert ll_disks.addDisk(
            positive=positive,
            alias=conf.DISK_NAME,
            provisioned_size=provisioned_size,
            interface=conf.DISK_INTERFACE,
            format=conf.DISK_FORMAT_COW,
            storagedomain=conf.STORAGE_NAME[0],
            quota=q_id
        ), "Failed to add new disk %s" % conf.DISK_NAME
        if last_event_id:
            logger.info(
                "Check if quota message of type %s, appear under events",
                audit_msg_type
            )
            assert self._check_quota_message(last_event_id, audit_msg_type), (
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
            dc_name=conf.DC_NAME_0,
            quota_name=conf.QUOTA_NAME,
            limit_type=limit_type,
            usage=usage_type
        )
        logger.info(
            "Check if expected %s: %s equal to quota limit %s: %s",
            usage_type, usage, usage_type, quota_limit_usage
        )
        assert usage == quota_limit_usage

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
            conf.DC_NAME_0, conf.QUOTA_MODES[cls.quota_mode]
        )
        if not ll_datacenters.update_datacenter(
            positive=True,
            datacenter=conf.DC_NAME_0,
            quota_mode=conf.QUOTA_MODES[cls.quota_mode]
        ):
            raise errors.DataCenterException(
                "Failed to update datacenter %s quota mode" % conf.DC_NAME_0
            )
        if cls.cluster_hard_limit_pct:
            logger.info("Update quota %s cluster grace value", conf.QUOTA_NAME)
            if not ll_datacenters.update_dc_quota(
                dc_name=conf.DC_NAME_0,
                quota_name=conf.QUOTA_NAME,
                cluster_hard_limit_pct=cls.cluster_hard_limit_pct
            ):
                raise errors.DataCenterException(
                    "Failed to update quota %s" % conf.QUOTA_NAME
                )
        logger.info(
            "Create limits on quota %s", conf.QUOTA_NAME
        )
        if not cls._create_quota_limits(
            dc_name=conf.DC_NAME_0,
            quota_name=conf.QUOTA_NAME,
            quota_cluster_limit=cls.quota_cluster_limit,
            quota_storage_limit=cls.quota_storage_limit
        ):
            raise errors.DataCenterException(
                "Failed to create cluster memory limit on quota %s" %
                conf.QUOTA_NAME
            )
        logger.info("Get quota %s id", conf.QUOTA_NAME)
        q_id = ll_datacenters.get_quota_id_by_name(
            dc_name=conf.DC_NAME_0, quota_name=conf.QUOTA_NAME
        )
        cpu_profile_id = ll_clusters.get_cpu_profile_id_by_name(
            conf.CLUSTER_NAME[0], conf.CLUSTER_NAME[0]
        )
        logger.info("Create new vm %s", conf.VM_NAME)
        if not ll_vms.createVm(
            positive=True, vmName=conf.VM_NAME,
            vmDescription=conf.VM_DESC,
            cluster=conf.CLUSTER_NAME[0],
            storageDomainName=conf.STORAGE_NAME[0],
            provisioned_size=conf.SIZE_10_GB, memory=conf.SIZE_512_MB,
            memory_guaranteed=conf.SIZE_512_MB,
            vm_quota=q_id, disk_quota=q_id,
            nic=conf.NIC_NAME[0], network=conf.MGMT_BRIDGE,
            cpu_profile_id=cpu_profile_id
        ):
            raise errors.VMException("Failed to create vm %s", conf.VM_NAME)

    @classmethod
    def teardown_class(cls):
        """
        1) Stop and remove vm
        2) Delete quota limits
        3) Update quota grace value
        4) Update datacenter quota mode
        """
        ll_vms.stop_vms_safely([conf.VM_NAME])
        logger.info("Remove vm %s", conf.VM_NAME)
        if not ll_vms.removeVm(positive=True, vm=conf.VM_NAME):
            logger.error("Failed to remove vm %s", conf.VM_NAME)
        quota_limits_d = {
            conf.LIMIT_TYPE_CLUSTER: cls.quota_cluster_limit,
            conf.LIMIT_TYPE_STORAGE: cls.quota_storage_limit
        }
        for limit_type, limits in quota_limits_d.iteritems():
            if limits:
                logger.info(
                    "Delete %s limit on quota %s", limit_type, conf.QUOTA_NAME
                )
                if not ll_datacenters.delete_quota_limits(
                    dc_name=conf.DC_NAME_0,
                    quota_name=conf.QUOTA_NAME,
                    limit_type=limit_type,
                    objects_names_l=[None]
                ):
                    logger.error(
                        "Failed to delete %s limit from quota %s",
                        limit_type, conf.QUOTA_NAME
                    )
        logger.info("Update quota %s cluster grace value", conf.QUOTA_NAME)
        if not ll_datacenters.update_dc_quota(
            dc_name=conf.DC_NAME_0,
            quota_name=conf.QUOTA_NAME,
            cluster_hard_limit_pct=20
        ):
            logger.error(
                "Failed to update quota %s", conf.QUOTA_NAME
            )
        logger.info(
            "Update datacenter %s quota mode to %s",
            conf.DC_NAME_0, conf.QUOTA_MODES[conf.QUOTA_NONE_MODE]
        )
        if not ll_datacenters.update_datacenter(
            positive=True,
            datacenter=conf.DC_NAME_0,
            quota_mode=conf.QUOTA_MODES[conf.QUOTA_NONE_MODE]
        ):
            logger.error(
                "Failed to update datacenter %s quota mode", conf.DC_NAME_0
            )


class TestDeleteQuotaInUseAudit(QuotaTestMode):
    """
    Negative: Delete quota in use under audit quota
    """
    __test__ = True
    quota_mode = conf.QUOTA_AUDIT_MODE

    @polarion("RHEVM3-9406")
    def test_n_delete_quota_in_use(self):
        """
        Delete quota in use
        """
        assert not ll_datacenters.delete_dc_quota(
            dc_name=conf.DC_NAME_0, quota_name=conf.QUOTA_NAME
        )


class TestDeleteQuotaInUseEnforced(QuotaTestMode):
    """
    Negative: Delete quota in use under enforced quota
    """
    __test__ = True
    quota_mode = conf.QUOTA_ENFORCED_MODE

    @polarion("RHEVM3-9447")
    def test_n_delete_quota_in_use(self):
        """
        Delete quota in use
        """
        assert not ll_datacenters.delete_dc_quota(
            dc_name=conf.DC_NAME_0, quota_name=conf.QUOTA_NAME
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
        ll_vms.stop_vms_safely(vms_list=[conf.VM_NAME])
        logger.info("Update vm %s socket and cores number", conf.VM_NAME)
        if not ll_vms.updateVm(
            positive=True, vm=conf.VM_NAME, cpu_socket=1, cpu_cores=1
        ):
            logger.error("Failed to update vm %s", conf.VM_NAME)


class TestQuotaAuditModeMemory(TestQuotaCluster):
    """
    Check cluster memory limit under audit quota
    """
    __test__ = True
    quota_mode = conf.QUOTA_AUDIT_MODE
    quota_cluster_limit = {None: {conf.MEMORY_LIMIT: 1, conf.VCPU_LIMIT: -1}}
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
            vm_params={conf.VM_MEMORY: conf.SIZE_1280_MB},
            audit_msg_type=conf.GRACE_TYPE
        )

    @polarion("RHEVM3-9433")
    def test_c_quota_memory_limit_over_grace(self):
        """
        Check over grace memory limit
        """
        self._check_cluster_limits(
            vm_params={conf.VM_MEMORY: conf.SIZE_2_GB},
            audit_msg_type=conf.EXCEED_TYPE
        )


class TestQuotaEnforcedModeMemory(TestQuotaCluster):
    """
    Check cluster memory limit under enforced quota
    """
    __test__ = True
    quota_mode = conf.QUOTA_ENFORCED_MODE
    quota_cluster_limit = {None: {conf.MEMORY_LIMIT: 1, conf.VCPU_LIMIT: -1}}
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
            vm_params={conf.VM_MEMORY: conf.SIZE_1280_MB},
            audit_msg_type=conf.GRACE_TYPE
        )

    @polarion("RHEVM3-9409")
    def test_c_quota_memory_limit_over_grace(self):
        """
        Check over grace memory limit
        """
        self._check_cluster_limits(
            vm_params={conf.VM_MEMORY: conf.SIZE_2_GB},
            audit_msg_type=conf.EXCEED_TYPE
        )


class TestQuotaAuditModeCPU(TestQuotaCluster):
    """
    Check cluster vcpu limit under audit quota
    """
    __test__ = True
    quota_mode = conf.QUOTA_AUDIT_MODE
    quota_cluster_limit = {
        None: {
            conf.VCPU_LIMIT: conf.MINIMAL_CPU_LIMIT,
            conf.MEMORY_LIMIT: conf.DEFAULT_MEMORY_LIMIT
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
            vm_params={conf.VM_CPU_CORES: conf.NUM_OF_CPUS[conf.GRACE_TYPE]},
            audit_msg_type=conf.GRACE_TYPE
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-9438")
    def test_c_quota_vcpu_limit_over_grace(self):
        """
        Check over grace vcpu limit
        """
        self._check_cluster_limits(
            vm_params={conf.VM_CPU_CORES: conf.NUM_OF_CPUS[conf.EXCEED_TYPE]},
            audit_msg_type=conf.EXCEED_TYPE
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12366")
    def test_d_quota_vcpu_hotplug_in_grace_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(
            conf.VM_UP, conf.GRACE_TYPE, conf.NUM_OF_CPUS[conf.GRACE_TYPE]
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12367")
    def test_e_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            conf.VM_UP, conf.EXCEED_TYPE, conf.NUM_OF_CPUS[conf.EXCEED_TYPE]
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12364")
    @bz(
        {"1167081": {conf.BZ_ENGINE: None, conf.BZ_VERSION: [conf.VERSION_35]}}
    )
    def test_f_quota_vcpu_hotplug_in_grace_vm_powering_up(self):
        """
        Hotplug additional vCPU, when vm is powering up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(
            conf.VM_POWER_UP,
            conf.GRACE_TYPE,
            conf.NUM_OF_CPUS[conf.GRACE_TYPE]
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12365")
    @bz(
        {"1167081": {conf.BZ_ENGINE: None, conf.BZ_VERSION: [conf.VERSION_35]}}
    )
    def test_g_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm is powering up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            conf.VM_POWER_UP,
            conf.EXCEED_TYPE,
            conf.NUM_OF_CPUS[conf.EXCEED_TYPE]
        )


class TestQuotaEnforcedModeCPU(TestQuotaCluster):
    """
    Check cluster vcpu limit under enforced quota
    """
    __test__ = True
    quota_mode = conf.QUOTA_ENFORCED_MODE
    quota_cluster_limit = {
        None: {
            conf.VCPU_LIMIT: conf.MINIMAL_CPU_LIMIT,
            conf.MEMORY_LIMIT: conf.DEFAULT_MEMORY_LIMIT
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
            vm_params={conf.VM_CPU_CORES: conf.NUM_OF_CPUS[conf.GRACE_TYPE]},
            audit_msg_type=conf.GRACE_TYPE
        )

    @polarion("RHEVM3-9403")
    def test_c_quota_vcpu_limit_over_grace(self):
        """
        Check over grace vcpu limit
        """
        self._check_cluster_limits(
            vm_params={conf.VM_CPU_CORES: conf.NUM_OF_CPUS[conf.EXCEED_TYPE]},
            audit_msg_type=conf.EXCEED_TYPE
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12370")
    def test_d_quota_vcpu_hotplug_in_grace_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(
            conf.VM_UP, conf.GRACE_TYPE, conf.NUM_OF_CPUS[conf.GRACE_TYPE]
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12371")
    def test_e_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            conf.VM_UP, conf.EXCEED_TYPE, conf.NUM_OF_CPUS[conf.EXCEED_TYPE]
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12368")
    @bz(
        {"1167081": {conf.BZ_ENGINE: None, conf.BZ_VERSION: [conf.VERSION_35]}}
    )
    def test_f_quota_vcpu_hotplug_in_grace_vm_powering_up(self):
        """
        Hotplug additional vCPU, when vm is powering up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(
            conf.VM_POWER_UP,
            conf.GRACE_TYPE,
            conf.NUM_OF_CPUS[conf.GRACE_TYPE]
        )

    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12369")
    @bz(
        {"1167081": {conf.BZ_ENGINE: None, conf.BZ_VERSION: [conf.VERSION_35]}}
    )
    def test_g_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm is powering up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            conf.VM_POWER_UP,
            conf.EXCEED_TYPE,
            conf.NUM_OF_CPUS[conf.EXCEED_TYPE]
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
        logger.info("Check if disk %s exist", conf.DISK_NAME)
        if ll_disks.checkDiskExists(True, conf.DISK_NAME):
            logger.info("Delete disk %s", conf.DISK_NAME)
            if not hl_disks.delete_disks([conf.DISK_NAME]):
                logger.error("Failed to remove disk %s", conf.DISK_NAME)


class TestQuotaAuditModeStorage(TestQuotaStorage):
    """
    Check storage limitation under audit quota
    """
    __test__ = True
    quota_mode = conf.QUOTA_AUDIT_MODE

    @polarion("RHEVM3-9440")
    def test_a_quota_storage_limit(self):
        """
        Check under grace storage limit
        """
        self._check_storage_limit(provisioned_size=conf.SIZE_10_GB)

    @polarion("RHEVM3-9443")
    def test_b_quota_storage_limit_in_grace(self):
        """
        Check in grace storage limit
        """
        self._check_storage_limit(
            provisioned_size=conf.SIZE_14_GB, audit_msg_type=conf.GRACE_TYPE
        )

    @polarion("RHEVM3-9446")
    def test_c_quota_storage_limit_over_grace(self):
        """
        Check over grace storage limit
        """
        self._check_storage_limit(
            provisioned_size=conf.SIZE_15_GB, audit_msg_type=conf.EXCEED_TYPE
        )


class TestQuotaEnforcedModeStorage(TestQuotaStorage):
    """
    Check storage limitation under audit quota
    """
    __test__ = True
    quota_mode = conf.QUOTA_ENFORCED_MODE

    @polarion("RHEVM3-9405")
    def test_a_quota_storage_limit(self):
        """
        Check under grace storage limit
        """
        self._check_storage_limit(provisioned_size=conf.SIZE_10_GB)

    @polarion("RHEVM3-9407")
    def test_b_quota_storage_limit_in_grace(self):
        """
        Check in grace storage limit
        """
        self._check_storage_limit(
            provisioned_size=conf.SIZE_14_GB, audit_msg_type=conf.GRACE_TYPE
        )

    @polarion("RHEVM3-9404")
    def test_c_quota_storage_limit_over_grace(self):
        """
        Check over grace storage limit
        """
        self._check_storage_limit(
            provisioned_size=conf.SIZE_15_GB, audit_msg_type=conf.EXCEED_TYPE
        )


class TestQuotaConsumptionRunOnceVM(QuotaTestMode):
    """
    Run vm once and check quota consumption
    """
    __test__ = True
    quota_mode = conf.QUOTA_AUDIT_MODE
    quota_cluster_limit = {
        None: {
            conf.VCPU_LIMIT: conf.DEFAULT_CPU_LIMIT,
            conf.MEMORY_LIMIT: conf.DEFAULT_MEMORY_LIMIT
        }
    }

    @polarion("RHEVM3-9396")
    def test_run_vm_once(self):
        """
        Run vm once and check quota consumption
        """
        logger.info("Run once vm %s", conf.VM_NAME)
        assert ll_vms.runVmOnce(
            positive=True, vm=conf.VM_NAME
        ), "Failed to run vm %s once" % conf.VM_NAME
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.MEMORY_USAGE,
            usage=conf.DEFAULT_MEMORY_USAGE
        )
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.VCPU_USAGE,
            usage=conf.DEFAULT_CPU_USAGE
        )


class TestQuotaConsumptionSnapshot(QuotaTestMode):
    """
    Make snapshot and check quota consumption
    """
    __test__ = True
    quota_mode = conf.QUOTA_AUDIT_MODE

    @polarion("RHEVM3-9397")
    def test_make_snapshot(self):
        """
        Make snapshot and check quota consumption
        """
        logger.info("Start vm %s", conf.VM_NAME)
        assert ll_vms.startVm(
            positive=True, vm=conf.VM_NAME
        ), "Failed to start vm %s" % conf.VM_NAME
        logger.info("Create snapshot from vm %s", conf.VM_NAME)
        assert ll_vms.addSnapshot(
            positive=True, vm=conf.VM_NAME, description=conf.VM_SNAPSHOT
        ), "Failed to create snapshot from vm %s" % conf.VM_NAME
        quota_limit_usage = ll_datacenters.get_quota_limit_usage(
            dc_name=conf.DC_NAME_0,
            quota_name=conf.QUOTA_NAME,
            limit_type=conf.LIMIT_TYPE_STORAGE,
            usage=conf.STORAGE_USAGE
        )
        logger.info(
            "Check if quota %s storage usage greater than %dGB",
            conf.QUOTA_NAME, conf.DEFAULT_DISK_USAGE
        )
        assert quota_limit_usage > conf.DEFAULT_DISK_USAGE, (
            "Quota %s storage usage less or equal to %d" %
            (conf.QUOTA_NAME, conf.DEFAULT_DISK_USAGE)
        )


class TestQuotaConsumptionTemplate(QuotaTestMode):
    """
    Create template from vm, remove it and check quota consumption
    """
    __test__ = True
    quota_mode = conf.QUOTA_AUDIT_MODE

    @bz({"1323595": {}})
    @polarion("RHEVM3-9394")
    def test_a_template_consumption(self):
        """
        Create template from vm, remove it and check quota consumption
        """
        logger.info("Create template from vm %s", conf.VM_NAME)
        assert ll_templates.createTemplate(
            positive=True, vm=conf.VM_NAME,
            name=conf.TEMPLATE_NAME, cluster=conf.CLUSTER_NAME[0]
        ), "Failed to create template from vm %s" % conf.VM_NAME
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_STORAGE,
            usage_type=conf.STORAGE_USAGE,
            usage=conf.FULL_DISK_USAGE
        )
        logger.info("Remove template %s", conf.TEMPLATE_NAME)
        assert ll_templates.removeTemplate(
            positive=True, template=conf.TEMPLATE_NAME
        ), "Failed to remove template %s" % conf.TEMPLATE_NAME
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_STORAGE,
            usage_type=conf.STORAGE_USAGE,
            usage=conf.DEFAULT_DISK_USAGE
        )

    @classmethod
    def teardown_class(cls):
        """
        Check if template still exist and remove it
        """
        logger.info("Check if template %s exist", conf.TEMPLATE_NAME)
        if ll_templates.check_template_existence(conf.TEMPLATE_NAME):
            logger.info("Try to remove template %s", conf.TEMPLATE_NAME)
            if not ll_templates.removeTemplate(
                positive=True, template=conf.TEMPLATE_NAME
            ):
                logger.error(
                    "Failed to remove template %s", conf.TEMPLATE_NAME
                )
        super(TestQuotaConsumptionTemplate, cls).teardown_class()


class TestQuotaConsumptionVmWithDisk(QuotaTestMode):
    """
    Create and remove vm with disk and check quota consumption
    """
    __test__ = True
    quota_mode = conf.QUOTA_AUDIT_MODE

    @polarion("RHEVM3-9393")
    def test_vm_with_disk_consumption(self):
        """
        Check storage quota consumption, when add or remove vm with disk
        """
        logger.info("Get quota %s id", conf.QUOTA_NAME)
        q_id = ll_datacenters.get_quota_id_by_name(
            dc_name=conf.DC_NAME_0, quota_name=conf.QUOTA_NAME
        )
        cpu_profile_id = ll_clusters.get_cpu_profile_id_by_name(
            conf.CLUSTER_NAME[0], conf.CLUSTER_NAME[0]
        )
        logger.info("Create new vm %s", conf.VM_NAME)
        assert ll_vms.createVm(
            positive=True, vmName=conf.TMP_VM_NAME,
            vmDescription=conf.VM_DESC,
            cluster=conf.CLUSTER_NAME[0],
            storageDomainName=conf.STORAGE_NAME[0],
            provisioned_size=conf.SIZE_10_GB, memory=conf.SIZE_512_MB,
            memory_guaranteed=conf.SIZE_512_MB,
            vm_quota=q_id, disk_quota=q_id,
            nic=conf.NIC_NAME[0], network=conf.MGMT_BRIDGE,
            cpu_profile_id=cpu_profile_id
        ), "Failed to create new vm %s" % conf.TMP_VM_NAME
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_STORAGE,
            usage_type=conf.STORAGE_USAGE,
            usage=conf.FULL_DISK_USAGE
        )
        logger.info("Remove vm %s", conf.TMP_VM_NAME)
        assert ll_vms.removeVm(
            positive=True, vm=conf.TMP_VM_NAME
        ), "Failed to remove vm %s" % conf.TMP_VM_NAME
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_STORAGE,
            usage_type=conf.STORAGE_USAGE,
            usage=conf.DEFAULT_DISK_USAGE
        )

    @classmethod
    def teardown_class(cls):
        """
        Check if vm exist and remove it
        """
        logger.info("Check if vm %s exist", conf.TMP_VM_NAME)
        if ll_vms.does_vm_exist(vm_name=conf.TMP_VM_NAME):
            logger.info("Remove vm %s", conf.TMP_VM_NAME)
            if not ll_vms.removeVm(positive=True, vm=conf.TMP_VM_NAME):
                logger.error("Failed to remove vm %s", conf.TMP_VM_NAME)
        super(TestQuotaConsumptionVmWithDisk, cls).teardown_class()


class TestQuotaConsumptionBasicVmActions(QuotaTestMode):
    """
    Run basic vm actions and check quota consumption
    """
    __test__ = True
    quota_mode = conf.QUOTA_AUDIT_MODE
    quota_cluster_limit = {
        None: {
            conf.VCPU_LIMIT: conf.DEFAULT_CPU_LIMIT,
            conf.MEMORY_LIMIT: conf.DEFAULT_MEMORY_LIMIT
        }
    }

    @polarion("RHEVM3-9395")
    def test_run_basic_vm_actions(self):
        """
        Run basic vm actions and check quota consumption
        """
        logger.info("Start vm %s", conf.VM_NAME)
        assert ll_vms.startVm(
            positive=True, vm=conf.VM_NAME
        ), "Failed to start vm %s" % conf.VM_NAME
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.MEMORY_USAGE,
            usage=conf.DEFAULT_MEMORY_USAGE
        )
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.VCPU_USAGE,
            usage=conf.DEFAULT_CPU_USAGE
        )
        logger.info(
            "Wait until vm %s state will not equal to %s",
            conf.VM_NAME, conf.VM_UP
        )
        assert ll_vms.waitForVmsStates(
            positive=True, names=conf.VM_NAME
        ), "Vm %s still not have state %s" % (conf.VM_NAME, conf.VM_UP)
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.MEMORY_USAGE,
            usage=conf.DEFAULT_MEMORY_USAGE
        )
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.VCPU_USAGE,
            usage=conf.DEFAULT_CPU_USAGE
        )
        logger.info("Suspend vm %s", conf.VM_NAME)
        assert ll_vms.suspendVm(
            positive=True, vm=conf.VM_NAME
        ), "Failed to suspend vm %s" % conf.VM_NAME
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.MEMORY_USAGE,
            usage=conf.ZERO_USAGE
        )
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.VCPU_USAGE,
            usage=conf.ZERO_USAGE
        )
        logger.info("Start vm %s", conf.VM_NAME)
        assert ll_vms.startVm(
            positive=True, vm=conf.VM_NAME
        ), "Failed to start vm %s" % conf.VM_NAME
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.MEMORY_USAGE,
            usage=conf.DEFAULT_MEMORY_USAGE
        )
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.VCPU_USAGE,
            usage=conf.DEFAULT_CPU_USAGE
        )
        logger.info("Stop vm %s", conf.VM_NAME)
        assert ll_vms.stopVm(
            positive=True, vm=conf.VM_NAME
        ), "Failed to stop vm %s" % conf.VM_NAME
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.MEMORY_USAGE,
            usage=conf.ZERO_USAGE
        )
        self.check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.VCPU_USAGE,
            usage=conf.ZERO_USAGE
        )
