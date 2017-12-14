"""
Quota Test
Check different cases for quota limitations in None, Audit and Enforce mode
Include CRUD tests, different limitations of storage, memory and vcpu tests
"""
import pytest
from rhevmtests.compute.sla.fixtures import (
    create_vms,
    make_template_from_vm,
    run_once_vms,
    start_vms,
    update_datacenter,
)

import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.disks as ll_disks
import art.rhevm_api.tests_lib.low_level.events as ll_events
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import helpers
from art.test_handler.tools import polarion, bz
from art.unittest_lib import testflow, SlaTest
from art.unittest_lib import (
    tier1,
    tier2,
)
from fixtures import (
    create_quota_limits,
    create_vm_snapshot,
    update_quota_cluster_hard_limit,
    stop_and_update_vm_cpus_and_memory,
    remove_additional_disk
)


@pytest.fixture(scope="module", autouse=True)
def init_quota_test(request):
    """
    1) Clean all events
    2) Create datacenter quota
    3) Create the VM
    """
    def fin():
        """
        1) Remove the VM
        2) Delete the quota
        """
        testflow.teardown("Remove the VM %s", conf.VM_NAME)
        ll_vms.safely_remove_vms(vms=[conf.VM_NAME])
        testflow.teardown("Delete the quota %s", conf.QUOTA_NAME)
        ll_datacenters.delete_dc_quota(
            dc_name=conf.DC_NAME[0], quota_name=conf.QUOTA_NAME
        )
    request.addfinalizer(fin)

    testflow.setup("Remove all events from the engine")
    sql = "DELETE FROM audit_log"
    conf.ENGINE.db.psql(sql)
    testflow.setup(
        "Create quota %s on datacenter %s",
        conf.DC_NAME[0], conf.QUOTA_NAME
    )
    assert ll_datacenters.create_dc_quota(
        dc_name=conf.DC_NAME[0],
        quota_name=conf.QUOTA_NAME
    )
    quota_id = ll_datacenters.get_quota_id_by_name(
        dc_name=conf.DC_NAME[0],
        quota_name=conf.QUOTA_NAME
    )
    testflow.setup("Create the VM %s", conf.VM_NAME)
    assert ll_vms.createVm(
        positive=True,
        vmName=conf.VM_NAME,
        cluster=conf.CLUSTER_NAME[0],
        nic=conf.NIC_NAME[0],
        provisioned_size=conf.SIZE_10_GB,
        storageDomainName=conf.STORAGE_NAME[0],
        memory=conf.SIZE_512_MB,
        memory_guaranteed=conf.SIZE_512_MB,
        network=conf.MGMT_BRIDGE,
        vm_quota=quota_id,
        disk_quota=quota_id
    )


class QuotaTestCRUD(SlaTest):
    """
    Quota CRUD test
    """

    @tier1
    @polarion("RHEVM3-9375")
    def test_a_create_quota(self):
        """
        Create Quota with the cluster and storage limits
        """
        quota_params = {"description": conf.QUOTA2_DESC}
        quota_cluster_limit = {
            None: {conf.VCPU_LIMIT: 1, conf.MEMORY_LIMIT: 1024}
        }
        quota_storage_limit = {None: {conf.STORAGE_LIMIT: 10}}
        testflow.step(
            "Create the quota %s on the datacenter %s",
            conf.QUOTA2_NAME, conf.DC_NAME[0]
        )
        assert ll_datacenters.create_dc_quota(
            dc_name=conf.DC_NAME[0],
            quota_name=conf.QUOTA2_NAME,
            **quota_params
        )
        testflow.step(
            "Create cluster %s and storage %s limits on the quota %s",
            quota_cluster_limit, quota_storage_limit, conf.QUOTA2_NAME
        )
        assert helpers.create_quota_limits(
            dc_name=conf.DC_NAME[0],
            quota_name=conf.QUOTA2_NAME,
            quota_cluster_limit=quota_cluster_limit,
            quota_storage_limit=quota_storage_limit
        )

    @tier1
    @polarion("RHEVM3-9390")
    def test_b_update_quota(self):
        """
        Update the quota
        """
        testflow.step(
            "Update the quota %s description", conf.QUOTA2_NAME
        )
        assert ll_datacenters.update_dc_quota(
            dc_name=conf.DC_NAME[0],
            quota_name=conf.QUOTA2_NAME,
            description=conf.QUOTA_DESC
        )

        testflow.step("Update the quota %s limits", conf.QUOTA2_NAME)
        assert helpers.create_quota_limits(
            dc_name=conf.DC_NAME[0],
            quota_name=conf.QUOTA2_NAME,
            quota_cluster_limit={
                None: {conf.VCPU_LIMIT: 2, conf.MEMORY_LIMIT: 2048}
            },
            quota_storage_limit={None: {conf.STORAGE_LIMIT: 20}}
        )

    @tier1
    @polarion("RHEVM3-9391")
    def test_c_delete_quota(self):
        """
        Delete the Quota
        """
        testflow.step(
            "Remove the quota %s from the datacenter %s",
            conf.QUOTA2_NAME, conf.DC_NAME[0]
        )
        assert ll_datacenters.delete_dc_quota(
            dc_name=conf.DC_NAME[0], quota_name=conf.QUOTA2_NAME
        )


@pytest.mark.usefixtures(
    update_datacenter.__name__,
    update_quota_cluster_hard_limit.__name__,
    create_quota_limits.__name__
)
class QuotaTestMode(SlaTest):
    """
    This unittest class tests quota enforced/audit mode
    """
    __test__ = False
    dcs_to_update = None
    quota_cluster_hard_limit = None
    quota_limits = {
        conf.QUOTA_CLUSTER_LIMIT: {
            None: {conf.MEMORY_LIMIT: 1, conf.VCPU_LIMIT: 1}
        },
        conf.QUOTA_STORAGE_LIMIT: {None: {conf.STORAGE_LIMIT: 20}}
    }

    def _check_hotplug(self, vm_state, audit_msg_type, vm_sockets):
        """
        Check the VM CPU hotplug, under different quota modes

        Args:
            vm_state (str): Expected VM state
            audit_msg_type (str): Audit message type
            vm_sockets (str): VM sockets
        """
        max_id = ll_events.get_max_event_id()
        testflow.step("Start the VM %s", conf.VM_NAME)
        assert ll_vms.startVm(
            positive=True, vm=conf.VM_NAME, wait_for_status=vm_state
        )

        compare = (
            False if self.quota_mode == conf.QUOTA_ENFORCED_MODE else True
        )
        testflow.step(
            "Update VM %s number of CPU sockets to %s",
            conf.VM_NAME, vm_sockets
        )
        assert ll_vms.updateVm(
            positive=True,
            vm=conf.VM_NAME,
            cpu_socket=vm_sockets,
            compare=compare
        )

        testflow.step("Check the quota message under audit events")
        assert self._check_quota_message(max_id, audit_msg_type)

    def _check_quota_message(self, max_id, audit_msg_type):
        """
        Check quota event message

        Args:
            max_id (str): ID of the last event
            audit_msg_type (str): Audit message type

        Returns:
            bool: True, if the quota message with ID greater
                than max_id exists, otherwise False
        """
        message = conf.QUOTA_EVENTS[self.quota_mode][audit_msg_type]
        testflow.step(
            "Waiting for the quota message '%s' with ID greater then %s",
            message, max_id
        )
        return ll_events.wait_for_event(message, start_id=max_id)

    @staticmethod
    def __prepare_for_cluster_limits(positive=True, vm_params=None):
        """
        1) Update VM parameters
        2) Start the VM

        Args:
            positive (bool): Positive behaviour for the start VM action
            vm_params (dict): VM new parameters
        """
        if vm_params:
            testflow.step(
                "Update the VM %s with parameters: %s", conf.VM_NAME, vm_params
            )
            assert ll_vms.updateVm(
                positive=True, vm=conf.VM_NAME, **vm_params
            )
        testflow.step("Start the VM %s", conf.VM_NAME)
        assert ll_vms.startVm(positive=positive, vm=conf.VM_NAME)

    @staticmethod
    def __prepare_for_storage_limits(positive=True, provisioned_size=conf.GB):
        """
        1) Create new disk with the quota

        Args:
            positive (bool): Positive behaviour for the add disk action
            provisioned_size (int): Disk size
        """
        testflow.step("Get the quota %s ID", conf.QUOTA_NAME)
        q_id = ll_datacenters.get_quota_id_by_name(
            dc_name=conf.DC_NAME[0], quota_name=conf.QUOTA_NAME
        )
        testflow.step(
            "Add the new disk %s with the size %s",
            conf.DISK_NAME, provisioned_size
        )
        assert ll_disks.addDisk(
            positive=positive,
            alias=conf.DISK_NAME,
            provisioned_size=provisioned_size,
            interface=conf.DISK_INTERFACE,
            format=conf.DISK_FORMAT_COW,
            storagedomain=conf.STORAGE_NAME[0],
            quota=q_id
        )

    def _check_limits(self, limit_type, audit_msg_type=None, **kwargs):
        """
        Check quota cluster or storage limits and
        check if quota message appears under audit events

        Args:
            limit_type (str): Quota limit type
            audit_msg_type (str): Audit message type

        Keyword Args:
            vm_params (dict): VM new parameters
            provisioned_size (int): Disk size
        """
        last_event_id = None
        if audit_msg_type:
            testflow.step("Get the ID of the last event")
            last_event_id = ll_events.get_max_event_id()
            assert last_event_id
        positive = True
        if (
            audit_msg_type and
            audit_msg_type == conf.EXCEED_TYPE and
            self.quota_mode == conf.QUOTA_ENFORCED_MODE
        ):
            positive = False
        if limit_type == conf.QUOTA_CLUSTER_LIMIT:
            self.__prepare_for_cluster_limits(positive=positive, **kwargs)
        elif limit_type == conf.QUOTA_STORAGE_LIMIT:
            self.__prepare_for_storage_limits(positive=positive, **kwargs)
        if audit_msg_type:
            testflow.step(
                "Check that quota message appears under audit events"
            )
            assert self._check_quota_message(
                max_id=last_event_id, audit_msg_type=audit_msg_type
            )

    @staticmethod
    def _check_limit_usage(limit_type, usage_type, usage):
        """
        Check if quota limit has correct value

        Args:
            limit_type (str): Limit type(cluster or storage)
            usage_type (str): Usage type
                storage: usage; cluster: vcpu_usage, memory_usage
            usage (float): Expected quota limit usage
        """
        quota_limit_usage = ll_datacenters.get_quota_limit_usage(
            dc_name=conf.DC_NAME[0],
            quota_name=conf.QUOTA_NAME,
            limit_type=limit_type,
            usage=usage_type
        )
        testflow.step(
            "Check if the expected %s: %s equal to the quota limit %s: %s",
            usage_type, usage, usage_type, quota_limit_usage
        )
        assert usage == quota_limit_usage

    def _check_vcpu_and_memory_limit_usage(self, usages):
        """
        Check quota VCPU and memory limits usage

        Args:
            usages (dict): VCPU and memory usage
        """
        self._check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.MEMORY_USAGE,
            usage=usages[conf.MEMORY_USAGE]
        )
        self._check_limit_usage(
            limit_type=conf.LIMIT_TYPE_CLUSTER,
            usage_type=conf.VCPU_USAGE,
            usage=usages[conf.VCPU_USAGE]
        )


@pytest.mark.usefixtures(update_datacenter.__name__)
class TestDeleteQuotaInUseAudit(SlaTest):
    """
    Negative: Delete quota in use under audit quota
    """
    quota_mode = conf.QUOTA_AUDIT_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_AUDIT_MODE]
        }
    }

    @tier1
    @polarion("RHEVM3-9406")
    @bz({"1517492": {}})
    def test_delete_quota_in_use(self):
        """
        Delete quota in use
        """
        testflow.step("Delete the quota %s", conf.QUOTA_NAME)
        assert not ll_datacenters.delete_dc_quota(
            dc_name=conf.DC_NAME[0], quota_name=conf.QUOTA_NAME
        )


@pytest.mark.usefixtures(update_datacenter.__name__)
class TestDeleteQuotaInUseEnforced(SlaTest):
    """
    Negative: Delete quota in use under enforced quota
    """
    quota_mode = conf.QUOTA_ENFORCED_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_ENFORCED_MODE]
        }
    }

    @tier1
    @bz({"1517492": {}})
    @polarion("RHEVM3-9447")
    def test_delete_quota_in_use(self):
        """
        Delete quota in use
        """
        testflow.step("Delete the quota %s", conf.QUOTA_NAME)
        assert not ll_datacenters.delete_dc_quota(
            dc_name=conf.DC_NAME[0], quota_name=conf.QUOTA_NAME
        )


@pytest.mark.usefixtures(stop_and_update_vm_cpus_and_memory.__name__)
class TestQuotaCluster(QuotaTestMode):
    """
    Parent class for quota cluster limits tests
    """
    limit_type = conf.QUOTA_CLUSTER_LIMIT


class TestQuotaAuditModeMemory(TestQuotaCluster):
    """
    Check cluster memory limit under audit quota
    """
    quota_mode = conf.QUOTA_AUDIT_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_AUDIT_MODE]
        }
    }
    quota_cluster_hard_limit = 50
    quota_limits = {
        conf.QUOTA_CLUSTER_LIMIT: {
            None: {conf.MEMORY_LIMIT: 1, conf.VCPU_LIMIT: -1}
        }
    }

    @tier2
    @polarion("RHEVM3-9428")
    def test_a_quota_memory_limit(self):
        """
        Check under grace memory limit
        """
        self._check_limits(limit_type=self.limit_type)

    @tier2
    @polarion("RHEVM3-9430")
    def test_b_quota_memory_limit_in_grace(self):
        """
        Check in grace memory limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.GRACE_TYPE,
            vm_params={conf.VM_MEMORY: conf.SIZE_1280_MB}
        )

    @tier2
    @polarion("RHEVM3-9433")
    def test_c_quota_memory_limit_over_grace(self):
        """
        Check over grace memory limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.EXCEED_TYPE,
            vm_params={conf.VM_MEMORY: conf.SIZE_2_GB}
        )


class TestQuotaEnforcedModeMemory(TestQuotaCluster):
    """
    Check cluster memory limit under enforced quota
    """
    quota_mode = conf.QUOTA_ENFORCED_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_ENFORCED_MODE]
        }
    }
    quota_cluster_hard_limit = 50
    quota_limits = {
        conf.QUOTA_CLUSTER_LIMIT: {
            None: {conf.MEMORY_LIMIT: 1, conf.VCPU_LIMIT: -1}
        }
    }

    @tier2
    @polarion("RHEVM3-9418")
    def test_a_quota_memory_limit(self):
        """
        Check under grace memory limit
        """
        self._check_limits(limit_type=self.limit_type)

    @tier2
    @polarion("RHEVM3-9419")
    def test_b_quota_memory_limit_in_grace(self):
        """
        Check in grace memory limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.GRACE_TYPE,
            vm_params={conf.VM_MEMORY: conf.SIZE_1280_MB}
        )

    @tier2
    @polarion("RHEVM3-9409")
    def test_c_quota_memory_limit_over_grace(self):
        """
        Check over grace memory limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.EXCEED_TYPE,
            vm_params={conf.VM_MEMORY: conf.SIZE_2_GB}
        )


class TestQuotaAuditModeCPU(TestQuotaCluster):
    """
    Check cluster vcpu limit under audit quota
    """
    quota_mode = conf.QUOTA_AUDIT_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_AUDIT_MODE]
        }
    }
    quota_cluster_hard_limit = 100
    quota_limits = {
        conf.QUOTA_CLUSTER_LIMIT: {
            None: {
                conf.VCPU_LIMIT: conf.MINIMAL_CPU_LIMIT,
                conf.MEMORY_LIMIT: conf.DEFAULT_MEMORY_LIMIT
            }
        }
    }

    @tier2
    @polarion("RHEVM3-9434")
    def test_a_quota_vcpu_limit(self):
        """
        Check under grace vcpu limit
        """
        self._check_limits(limit_type=self.limit_type)

    @tier2
    @polarion("RHEVM3-9437")
    def test_b_quota_vcpu_limit_in_grace(self):
        """
        Check in grace vcpu limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.GRACE_TYPE,
            vm_params={conf.VM_CPU_CORES: conf.NUM_OF_CPUS[conf.GRACE_TYPE]}
        )

    @tier2
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-9438")
    def test_c_quota_vcpu_limit_over_grace(self):
        """
        Check over grace vcpu limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.EXCEED_TYPE,
            vm_params={conf.VM_CPU_CORES: conf.NUM_OF_CPUS[conf.EXCEED_TYPE]}
        )

    @tier2
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12366")
    def test_d_quota_vcpu_hotplug_in_grace_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(
            vm_state=conf.VM_UP,
            audit_msg_type=conf.GRACE_TYPE,
            vm_sockets=conf.NUM_OF_CPUS[conf.GRACE_TYPE]
        )

    @tier2
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12367")
    def test_e_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            vm_state=conf.VM_UP,
            audit_msg_type=conf.EXCEED_TYPE,
            vm_sockets=conf.NUM_OF_CPUS[conf.EXCEED_TYPE]
        )


class TestQuotaEnforcedModeCPU(TestQuotaCluster):
    """
    Check cluster vcpu limit under enforced quota
    """
    quota_mode = conf.QUOTA_ENFORCED_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_ENFORCED_MODE]
        }
    }
    quota_cluster_hard_limit = 100
    quota_limits = {
        conf.QUOTA_CLUSTER_LIMIT: {
            None: {
                conf.VCPU_LIMIT: conf.MINIMAL_CPU_LIMIT,
                conf.MEMORY_LIMIT: conf.DEFAULT_MEMORY_LIMIT
            }
        }
    }

    @tier2
    @polarion("RHEVM3-9408")
    def test_a_quota_vcpu_limit(self):
        """
        Check under grace vcpu limit
        """
        self._check_limits(limit_type=self.limit_type)

    @tier2
    @polarion("RHEVM3-9402")
    def test_b_quota_vcpu_limit_in_grace(self):
        """
        Check in grace vcpu limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.GRACE_TYPE,
            vm_params={conf.VM_CPU_CORES: conf.NUM_OF_CPUS[conf.GRACE_TYPE]}
        )

    @tier2
    @polarion("RHEVM3-9403")
    def test_c_quota_vcpu_limit_over_grace(self):
        """
        Check over grace vcpu limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.EXCEED_TYPE,
            vm_params={conf.VM_CPU_CORES: conf.NUM_OF_CPUS[conf.EXCEED_TYPE]}
        )

    @tier2
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12370")
    def test_d_quota_vcpu_hotplug_in_grace_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit in grace
        """
        self._check_hotplug(
            vm_state=conf.VM_UP,
            audit_msg_type=conf.GRACE_TYPE,
            vm_sockets=conf.NUM_OF_CPUS[conf.GRACE_TYPE]
        )

    @tier2
    @pytest.mark.skipif(conf.PPC_ARCH, reason=conf.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-12371")
    def test_e_quota_vcpu_hotplug_in_exceed_vm_up(self):
        """
        Hotplug additional vCPU, when vm is up,
        to put quota vCPU limit over grace
        """
        self._check_hotplug(
            vm_state=conf.VM_UP,
            audit_msg_type=conf.EXCEED_TYPE,
            vm_sockets=conf.NUM_OF_CPUS[conf.EXCEED_TYPE]
        )


@pytest.mark.usefixtures(remove_additional_disk.__name__)
class TestQuotaStorage(QuotaTestMode):
    """
    Base class to check quota storage limits
    """
    limit_type = conf.QUOTA_STORAGE_LIMIT


class TestQuotaAuditModeStorage(TestQuotaStorage):
    """
    Check storage limitation under audit quota
    """
    quota_mode = conf.QUOTA_AUDIT_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_AUDIT_MODE]
        }
    }

    @tier2
    @polarion("RHEVM3-9440")
    def test_a_quota_storage_limit(self):
        """
        Check under grace storage limit
        """
        self._check_limits(
            limit_type=self.limit_type, provisioned_size=conf.SIZE_10_GB
        )

    @tier2
    @polarion("RHEVM3-9443")
    def test_b_quota_storage_limit_in_grace(self):
        """
        Check in grace storage limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.GRACE_TYPE,
            provisioned_size=conf.SIZE_14_GB
        )

    @tier2
    @polarion("RHEVM3-9446")
    def test_c_quota_storage_limit_over_grace(self):
        """
        Check over grace storage limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.EXCEED_TYPE,
            provisioned_size=conf.SIZE_15_GB
        )


class TestQuotaEnforcedModeStorage(TestQuotaStorage):
    """
    Check storage limitation under audit quota
    """
    quota_mode = conf.QUOTA_ENFORCED_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_ENFORCED_MODE]
        }
    }

    @tier2
    @polarion("RHEVM3-9405")
    def test_a_quota_storage_limit(self):
        """
        Check under grace storage limit
        """
        self._check_limits(
            limit_type=self.limit_type, provisioned_size=conf.SIZE_10_GB
        )

    @tier2
    @polarion("RHEVM3-9407")
    def test_b_quota_storage_limit_in_grace(self):
        """
        Check in grace storage limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.GRACE_TYPE,
            provisioned_size=conf.SIZE_14_GB
        )

    @tier2
    @polarion("RHEVM3-9404")
    def test_c_quota_storage_limit_over_grace(self):
        """
        Check over grace storage limit
        """
        self._check_limits(
            limit_type=self.limit_type,
            audit_msg_type=conf.EXCEED_TYPE,
            provisioned_size=conf.SIZE_15_GB
        )


@pytest.mark.usefixtures(run_once_vms.__name__)
class TestQuotaConsumptionRunOnceVM(QuotaTestMode):
    """
    Run vm once and check quota consumption
    """
    quota_mode = conf.QUOTA_AUDIT_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_AUDIT_MODE]
        }
    }
    quota_limits = {
        conf.QUOTA_CLUSTER_LIMIT: {
            None: {
                conf.VCPU_LIMIT: conf.DEFAULT_CPU_LIMIT,
                conf.MEMORY_LIMIT: conf.DEFAULT_MEMORY_LIMIT
            }
        }
    }
    vms_to_run = {conf.VM_NAME: {}}

    @tier2
    @polarion("RHEVM3-9396")
    def test_run_vm_once(self):
        """
        Run vm once and check quota consumption
        """
        self._check_vcpu_and_memory_limit_usage(usages=conf.DEFAULT_USAGES)


@pytest.mark.usefixtures(
    start_vms.__name__,
    create_vm_snapshot.__name__
)
class TestQuotaConsumptionSnapshot(QuotaTestMode):
    """
    Make snapshot and check quota consumption
    """
    quota_mode = conf.QUOTA_AUDIT_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_AUDIT_MODE]
        }
    }
    vms_to_start = [conf.VM_NAME]
    wait_for_vms_ip = False

    @tier2
    @polarion("RHEVM3-9397")
    def test_make_snapshot(self):
        """
        Make snapshot and check quota consumption
        """
        quota_limit_usage = ll_datacenters.get_quota_limit_usage(
            dc_name=conf.DC_NAME[0],
            quota_name=conf.QUOTA_NAME,
            limit_type=conf.LIMIT_TYPE_STORAGE,
            usage=conf.STORAGE_USAGE
        )
        testflow.step(
            "Check if the quota %s storage usage greater than %sGB",
            conf.QUOTA_NAME, conf.DEFAULT_DISK_USAGE
        )
        assert quota_limit_usage > conf.DEFAULT_DISK_USAGE


@pytest.mark.usefixtures(make_template_from_vm.__name__)
class TestQuotaConsumptionTemplate(QuotaTestMode):
    """
    Create template from vm, remove it and check quota consumption
    """
    quota_mode = conf.QUOTA_AUDIT_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_AUDIT_MODE]
        }
    }
    vm_for_template = conf.VM_NAME
    template_name = conf.TEMPLATE_NAME

    @tier2
    @polarion("RHEVM3-9394")
    def test_a_template_consumption(self):
        """
        1) Check quota limit usage
        2) Remove the template
        3) Check quota limit usage
        """
        self._check_limit_usage(
            limit_type=conf.LIMIT_TYPE_STORAGE,
            usage_type=conf.STORAGE_USAGE,
            usage=conf.FULL_DISK_USAGE
        )
        testflow.step("Remove the template %s", conf.TEMPLATE_NAME)
        assert ll_templates.remove_template(
            positive=True, template=conf.TEMPLATE_NAME
        )
        self._check_limit_usage(
            limit_type=conf.LIMIT_TYPE_STORAGE,
            usage_type=conf.STORAGE_USAGE,
            usage=conf.DEFAULT_DISK_USAGE
        )


@pytest.mark.usefixtures(create_vms.__name__)
class TestQuotaConsumptionVmWithDisk(QuotaTestMode):
    """
    Create and remove vm with disk and check quota consumption
    """
    quota_mode = conf.QUOTA_AUDIT_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_AUDIT_MODE]
        }
    }
    vms_create_params = {
        conf.TMP_VM_NAME: {
            conf.VM_CLUSTER: conf.CLUSTER_NAME[0],
            conf.VM_STORAGE_DOMAIN: conf.STORAGE_NAME[0],
            conf.VM_DISK_SIZE: conf.SIZE_10_GB,
            conf.VM_MEMORY: conf.SIZE_512_MB,
            conf.VM_MEMORY_GUARANTEED: conf.SIZE_512_MB,
            conf.VM_QUOTA: conf.QUOTA_NAME,
            conf.VM_DISK_QUOTA: conf.QUOTA_NAME,
            conf.VM_NIC: conf.NIC_NAME[0],
            conf.VM_NETWORK: conf.MGMT_BRIDGE
        }
    }

    @tier2
    @polarion("RHEVM3-9393")
    def test_vm_with_disk_consumption(self):
        """
        1) Check quota limit usage
        2) Remove the VM
        3) Check quota limit usage
        """
        self._check_limit_usage(
            limit_type=conf.LIMIT_TYPE_STORAGE,
            usage_type=conf.STORAGE_USAGE,
            usage=conf.FULL_DISK_USAGE
        )
        testflow.step("Remove the VM %s", conf.TMP_VM_NAME)
        assert ll_vms.removeVm(positive=True, vm=conf.TMP_VM_NAME)
        self._check_limit_usage(
            limit_type=conf.LIMIT_TYPE_STORAGE,
            usage_type=conf.STORAGE_USAGE,
            usage=conf.DEFAULT_DISK_USAGE
        )


class TestQuotaConsumptionBasicVmActions(QuotaTestMode):
    """
    Run basic vm actions and check quota consumption
    """
    quota_mode = conf.QUOTA_AUDIT_MODE
    dcs_to_update = {
        conf.DC_NAME[0]: {
            conf.DC_QUOTA_MODE: conf.QUOTA_MODES[conf.QUOTA_AUDIT_MODE]
        }
    }
    quota_limits = {
        conf.QUOTA_CLUSTER_LIMIT: {
            None: {
                conf.VCPU_LIMIT: conf.DEFAULT_CPU_LIMIT,
                conf.MEMORY_LIMIT: conf.DEFAULT_MEMORY_LIMIT
            }
        }
    }

    @tier2
    @polarion("RHEVM3-9395")
    def test_run_basic_vm_actions(self):
        """
        1) Start the VM
        2) Check quota limit VCPU and memory usage
        3) Wait for the VM up state
        4) Check quota limit VCPU and memory usage
        5) Suspend the VM
        6) Check quota limit VCPU and memory usage
        7) Start the VM
        8) Check quota limit VCPU and memory usage
        9) Stop the VM
        10) Check quota limit VCPU and memory usage
        """
        testflow.step("Start the VM %s", conf.VM_NAME)
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME)
        self._check_vcpu_and_memory_limit_usage(usages=conf.DEFAULT_USAGES)

        testflow.step(
            "Wait until the VM %s state will be equal to %s",
            conf.VM_NAME, conf.VM_UP
        )
        assert ll_vms.waitForVmsStates(positive=True, names=conf.VM_NAME)
        self._check_vcpu_and_memory_limit_usage(usages=conf.DEFAULT_USAGES)

        testflow.step("Suspend the VM %s", conf.VM_NAME)
        assert ll_vms.suspendVm(positive=True, vm=conf.VM_NAME)
        self._check_vcpu_and_memory_limit_usage(usages=conf.ZERO_USAGES)

        testflow.step("Start the VM %s", conf.VM_NAME)
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME)
        self._check_vcpu_and_memory_limit_usage(usages=conf.DEFAULT_USAGES)

        testflow.step("Stop the VM %s", conf.VM_NAME)
        assert ll_vms.stopVm(positive=True, vm=conf.VM_NAME)
        self._check_vcpu_and_memory_limit_usage(usages=conf.ZERO_USAGES)
