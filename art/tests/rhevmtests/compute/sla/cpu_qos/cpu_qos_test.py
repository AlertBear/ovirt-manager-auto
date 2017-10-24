"""
CPU QoS test
"""
import pytest
import rhevmtests.compute.sla.helpers as sla_helpers

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
from art.test_handler.tools import polarion, bz
from art.unittest_lib import testflow, tier1, tier2, SlaTest
from fixtures import (
    create_cpu_profile,
    create_cpu_qoss,
    create_template_for_cpu_qos_test,
    create_vm_from_template_for_cpu_qos_test
)
from rhevmtests.compute.sla.fixtures import (
    create_vm_without_disk,
    migrate_he_vm,
    start_vms,
    stop_guest_agent_service,
    update_vms,
    update_vms_cpus_to_hosts_cpus
)

he_src_host = 0


@pytest.fixture(scope="module", autouse=True)
def init_constants():
    """
    Setup:
    1. Set the default CPU profile ID for each cluster
    """
    conf.DEFAULT_CPU_PROFILE_ID_CLUSTER_0 = (
        ll_clusters.get_cpu_profile_id_by_name(
            cpu_profile_name=conf.CLUSTER_NAME[0],
            cluster_name=conf.CLUSTER_NAME[0]
        )
    )
    conf.DEFAULT_CPU_PROFILE_ID_CLUSTER_1 = (
        ll_clusters.get_cpu_profile_id_by_name(
            cpu_profile_name=conf.CLUSTER_NAME[1],
            cluster_name=conf.CLUSTER_NAME[1]
        )
    )


class TestQoSAndCpuProfileCRUD(SlaTest):
    """
    1. test_a_add_qos
    2. test_b_negative_add_qos
    3. test_c_add_cpu_profile
    4. test_d_attach_cpu_profile_to_vm
    5. test_e_remove_cpu_profile_and_qos
    """

    @tier1
    @polarion("RHEVM-14931")
    def test_a_add_qos(self):
        """
        Add 4 QoS with: 10%, 25%, 50% and 75%
        """
        for qos_name, qos_value in conf.QOSS.iteritems():
            testflow.step(
                "Create CPU QoS %s on datacenter %s with value: %s",
                qos_name, conf.DC_NAME[0], qos_value
            )
            assert ll_datacenters.add_qos_to_datacenter(
                datacenter=conf.DC_NAME[0],
                qos_name=qos_name,
                qos_type=conf.QOS_TYPE_CPU,
                cpu_limit=qos_value
            )

    @tier1
    @polarion("RHEVM3-14700")
    def test_b_negative_add_qos(self):
        """
        1. Try to set a string in Qos
        2. Try to set a value in QoS that is bigger then 100
        3. Try to set a value in QoS that is smaller then 0
        """
        qoss = {"qos_120": 120, "qos_-5": -5}
        for qos_name, qos_value in qoss.iteritems():
            testflow.step(
                "Create CPU QoS %s on datacenter %s with parameters: %s",
                qos_name, conf.DC_NAME[0], qos_value
            )
            assert not ll_datacenters.add_qos_to_datacenter(
                datacenter=conf.DC_NAME[0],
                qos_name=qos_name,
                qos_type=conf.QOS_TYPE_CPU,
                cpu_limit=qos_value
            )

    @tier1
    @polarion("RHEVM3-14711")
    def test_c_add_cpu_profile(self):
        """
        Add 4 cpu profile that match the QOSS that were already created
        """
        for cpu_profile_name, qos_name in conf.CPU_PROFILES.iteritems():
            cpu_qos_obj = ll_datacenters.get_qos_from_datacenter(
                datacenter=conf.DC_NAME[0],
                qos_name=qos_name
            )
            testflow.step(
                "Create CPU profile %s on cluster %s with QoS %s",
                cpu_profile_name, conf.CLUSTER_NAME[0], qos_name
            )
            assert ll_clusters.add_cpu_profile(
                cluster_name=conf.CLUSTER_NAME[0],
                name=cpu_profile_name,
                qos=cpu_qos_obj
            )

    @tier1
    @polarion("RHEVM-14932")
    def test_d_attach_cpu_profile_to_vm(self):
        """
        Attach all cpu profiles to VM's
        """
        for vm_name, cpu_profile_name in conf.VMS_CPU_PROFILES.iteritems():
            cpu_profile_id = ll_clusters.get_cpu_profile_id_by_name(
                cluster_name=conf.CLUSTER_NAME[0],
                cpu_profile_name=cpu_profile_name
            )
            testflow.step(
                "Attach CPU profile %s to VM %s", cpu_profile_name, vm_name
            )
            assert ll_vms.updateVm(
                positive=True,
                vm=vm_name,
                cpu_profile_id=cpu_profile_id
            )

    @tier1
    @polarion("RHEVM3-14710")
    def test_e_remove_cpu_profile_and_qos(self):
        """
        1. Detach CPU profiles from VM's
        2. Delete a CPU profile that does not attached to a VM
        3. Delete a Qos that does not attached to a VM
        """
        for vm_name in conf.VMS_CPU_PROFILES.iterkeys():
            testflow.step(
                "Attach default CPU profile to VM %s", vm_name
            )
            assert ll_vms.updateVm(
                positive=True,
                vm=vm_name,
                cpu_profile_id=conf.DEFAULT_CPU_PROFILE_ID_CLUSTER_0
            )
        for cpu_profile_name, qos_name in conf.CPU_PROFILES.iteritems():
            testflow.step(
                "Remove CPU profile %s from cluster %s",
                cpu_profile_name, conf.CLUSTER_NAME[0]
            )
            assert ll_clusters.remove_cpu_profile(
                cluster_name=conf.CLUSTER_NAME[0],
                cpu_prof_name=cpu_profile_name
            )
            testflow.step(
                "Remove CPU QoS %s from datacenter %s",
                qos_name, conf.DC_NAME[0]
            )
            assert ll_datacenters.delete_qos_from_datacenter(
                datacenter=conf.DC_NAME[0],
                qos_name=qos_name
            )


@pytest.mark.usefixtures(
    migrate_he_vm.__name__,
    create_cpu_qoss.__name__,
    create_cpu_profile.__name__,
    update_vms.__name__
)
class BaseCpuQoSAndCpuProfile(SlaTest):
    """
    Apply common fixtures on all child classes
    """

    @staticmethod
    def calculate_expected_values(load_dict):
        """
        Calculate expected values for test

        Args:
            load_dict (dict): Load to VM dictionary

        Returns:
            dict: Keys - VM names, Values - Expected CPU load percentage
        """
        expected_values = {}
        for vm_name, load_value in load_dict.iteritems():
            host = ll_vms.get_vm_host(vm_name=vm_name)
            host_cpu = ll_hosts.get_host_processing_units_number(
                host_name=host
            )
            vm_cpu = ll_vms.get_vm_processing_units_number(vm_name=vm_name)
            expected_value = (
                float(host_cpu) / float(vm_cpu) * float(load_value)
            )
            expected_value = 100 if expected_value > 100 else expected_value
            expected_values[vm_name] = expected_value
        return expected_values


@pytest.mark.usefixtures(start_vms.__name__)
class TestCpuQoSLimitationSanity(BaseCpuQoSAndCpuProfile):
    """
    Check that VM limited to specific CPU load by CPU QoS
    """

    cpu_qoss = {conf.CPU_QOS_10: conf.QOSS[conf.CPU_QOS_10]}
    cpu_profiles = {conf.CPU_PROFILE_10: conf.CPU_QOS_10}
    vms_to_params = {
        conf.QOS_VMS[0]: {conf.VM_CPU_PROFILE: conf.CPU_PROFILE_10}
    }
    vms_to_start = conf.QOS_VMS[:1]
    load_dict = {conf.QOS_VMS[0]: conf.QOSS[conf.CPU_QOS_10]}

    @tier1
    @bz({'1454633': {}})
    @polarion("RHEVM3-14688")
    def test_vm_cpu_limitation(self):
        """
        1. Load VM CPU to 100%
        2. Check that the VM CPU is the right amount CPU,
           that is taken from the host.
        """
        expected_dict = self.calculate_expected_values(
            load_dict=self.load_dict
        )
        assert sla_helpers.load_vm_and_check_the_load(
            load_dict=self.load_dict,
            expected_values=expected_dict
        )


class TestRemoveAttachedCpuProfile(BaseCpuQoSAndCpuProfile):
    """
    Negative: remove CPU profile that attached to VM
    """
    cpu_qoss = {conf.CPU_QOS_10: conf.QOSS[conf.CPU_QOS_10]}
    cpu_profiles = {conf.CPU_PROFILE_10: conf.CPU_QOS_10}
    vms_to_params = {
        conf.QOS_VMS[0]: {conf.VM_CPU_PROFILE: conf.CPU_PROFILE_10}
    }

    @tier2
    @bz({'1454633': {}})
    @polarion("RHEVM-14708")
    def test_remove_cpu_profile(self):
        """
        Try to delete a CPU profile that is attached to a VM
        """
        testflow.step("Remove CPU profile %s", conf.CPU_PROFILE_10)
        assert not ll_clusters.remove_cpu_profile(
            cluster_name=conf.CLUSTER_NAME[0],
            cpu_prof_name=conf.CPU_PROFILE_10
        )


@pytest.mark.usefixtures(
    create_vm_without_disk.__name__,
    create_cpu_qoss.__name__,
    create_cpu_profile.__name__,
    update_vms.__name__,
    create_template_for_cpu_qos_test.__name__,
    create_vm_from_template_for_cpu_qos_test.__name__
)
class TestCreateQoSVmFromTemplate(SlaTest):
    """
    Create VM from template that has specific CPU profile
    """
    cpu_qoss = {conf.CPU_QOS_10: conf.QOSS[conf.CPU_QOS_10]}
    cpu_profiles = {conf.CPU_PROFILE_10: conf.CPU_QOS_10}
    vms_to_params = {
        conf.VM_WITHOUT_DISK: {conf.VM_CPU_PROFILE: conf.CPU_PROFILE_10}
    }

    @tier2
    @bz({'1454633': {}})
    @polarion("RHEVM3-14939")
    def test_template_cpu_profile(self):
        """
        1. Create a template on first cluster with a CPU profile
        2. Create a VM from the template on second cluster
        3. Check that created and gets the default CPU profile
        """
        vm_cpu_profile_id = ll_vms.get_cpu_profile_id(
            vm_name=conf.QOS_VM_FROM_TEMPLATE
        )
        testflow.step(
            "Check if VM created from template has default CPU profile %s",
            conf.CLUSTER_NAME[1]
        )
        assert vm_cpu_profile_id == conf.DEFAULT_CPU_PROFILE_ID_CLUSTER_1


@pytest.mark.usefixtures(start_vms.__name__)
class TestCpuLimitationAfterVmMigration(BaseCpuQoSAndCpuProfile):
    """
    Check VM CPU limitation after migration
    """
    cpu_qoss = {conf.CPU_QOS_10: conf.QOSS[conf.CPU_QOS_10]}
    cpu_profiles = {conf.CPU_PROFILE_10: conf.CPU_QOS_10}
    vms_to_params = {
        conf.QOS_VMS[0]: {conf.VM_CPU_PROFILE: conf.CPU_PROFILE_10}
    }
    vms_to_start = conf.QOS_VMS[:1]
    load_dict = {conf.QOS_VMS[0]: conf.QOSS[conf.CPU_QOS_10]}

    @tier1
    @bz({'1454633': {}})
    @polarion("RHEVM3-14697")
    def test_vm_cpu_limitation(self):
        """
        1. Migrate VM to a different host
        2. Load vm CPU to 100%
        3. Check that the VM CPU is the right amount CPU,
           that is taken from the host.
        """
        testflow.step("Migrate VM %s", conf.QOS_VMS[0])
        assert ll_vms.migrateVm(positive=True, vm=conf.QOS_VMS[0])
        expected_dict = self.calculate_expected_values(
            load_dict=self.load_dict
        )
        assert sla_helpers.load_vm_and_check_the_load(
            load_dict=self.load_dict, expected_values=expected_dict
        )


@pytest.mark.usefixtures(start_vms.__name__)
class TestVmCpuLimitationAfterHotplug(BaseCpuQoSAndCpuProfile):
    """
    Check VM CPU limitation after CPU hotplug
    """
    cpu_qoss = {conf.CPU_QOS_10: conf.QOSS[conf.CPU_QOS_10]}
    cpu_profiles = {conf.CPU_PROFILE_10: conf.CPU_QOS_10}
    vms_to_params = {
        conf.QOS_VMS[0]: {conf.VM_CPU_PROFILE: conf.CPU_PROFILE_10}
    }
    vms_to_start = conf.QOS_VMS[:1]
    load_dict = {conf.QOS_VMS[0]: conf.QOSS[conf.CPU_QOS_10]}

    @tier2
    @bz({'1454633': {}})
    @polarion("RHEVM3-14696")
    def test_vm_cpu_limitation_after_cpu_hot_plug(self):
        """
        1. Preform hot-plug to maximum host processing units
        2. Check if now CPU load increased, as additional CPUs were added
        """
        host = ll_vms.get_vm_host(vm_name=conf.QOS_VMS[0])
        host_cpu = ll_hosts.get_host_processing_units_number(host_name=host)
        testflow.step("Hotplug CPU to VM %s", conf.QOS_VMS[0])
        vm_cpu_sockets = min(8, host_cpu)
        assert ll_vms.updateVm(
            positive=True, vm=conf.QOS_VMS[0], cpu_socket=vm_cpu_sockets
        )
        expected_dict = self.calculate_expected_values(
            load_dict=self.load_dict
        )
        assert sla_helpers.load_vm_and_check_the_load(
            load_dict=self.load_dict, expected_values=expected_dict
        )


@pytest.mark.usefixtures(
    update_vms_cpus_to_hosts_cpus.__name__,
    start_vms.__name__
)
class TestVmCpuLimitationWithDifferentValues(BaseCpuQoSAndCpuProfile):
    """
    Check VM CPU limitation with different values
    """
    cpu_qoss = conf.QOSS
    cpu_profiles = conf.CPU_PROFILES
    vms_to_params = dict(
        (
            vm_name, {conf.VM_CPU_PROFILE: cpu_profile}
        ) for vm_name, cpu_profile in conf.VMS_CPU_PROFILES.iteritems()
    )
    vms_to_hosts_cpus = dict((vm_name, 0) for vm_name in conf.QOS_VMS)
    vms_to_start = conf.QOS_VMS
    load_dict = dict(zip(conf.QOS_VMS, sorted(conf.QOSS.values())))

    @tier2
    @bz({'1454633': {}})
    @polarion("RHEVM3-14727")
    def test_cpu_limitation(self):
        """
        1. Load the 4 vms with different cpu profiles values CPU to 100%
        2. See that every VM take CPU resources exactly as set in cpu profile
        """
        expected_dict = self.calculate_expected_values(
            load_dict=self.load_dict
        )
        assert sla_helpers.load_vm_and_check_the_load(
            load_dict=self.load_dict, expected_values=expected_dict
        )


@pytest.mark.usefixtures(
    start_vms.__name__,
    stop_guest_agent_service.__name__
)
class TestVmCpuLimitationWithoutGuestAgent(BaseCpuQoSAndCpuProfile):
    """
    Check VM CPU limitation when VM does not have guest agent
    """
    cpu_qoss = {conf.CPU_QOS_10: conf.QOSS[conf.CPU_QOS_10]}
    cpu_profiles = {conf.CPU_PROFILE_10: conf.CPU_QOS_10}
    vms_to_params = {
        conf.QOS_VMS[0]: {conf.VM_CPU_PROFILE: conf.CPU_PROFILE_10}
    }
    vms_to_start = conf.QOS_VMS[:1]
    load_dict = {conf.QOS_VMS[0]: conf.QOSS[conf.CPU_QOS_10]}
    stop_guest_agent_vm = conf.QOS_VMS[0]

    @tier2
    @bz({'1454633': {}})
    @polarion("RHEVM3-14729")
    def test_cpu_limitation_without_guest_agent(self):
        """
        1. Remove guest agent and puppet if exits
        2. Load VM CPU to 100%
        3. Check that VM take CPU resources exactly as set in cpu profile
        """
        expected_dict = self.calculate_expected_values(
            load_dict=self.load_dict
        )
        assert sla_helpers.load_vm_and_check_the_load(
            load_dict=self.load_dict, expected_values=expected_dict
        )
