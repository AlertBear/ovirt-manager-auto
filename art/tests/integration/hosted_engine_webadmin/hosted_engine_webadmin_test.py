"""
Test HE behaviour via the engine
"""
import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import helpers
from art.test_handler.tools import polarion
from fixtures import (
    add_nic_to_he_vm,
    create_network,
    initialize_ge_constants,
    init_he_webadmin,
    update_he_vm,
    update_he_vm_cpus_back,
    wait_for_ovf_and_restart_he_vm
)


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    init_he_webadmin.__name__,
    update_he_vm.__name__,
    wait_for_ovf_and_restart_he_vm.__name__
)
class TestUpdateHeVmMemory(u_libs.SlaTest):
    """
    Update HE VM memory and check that HE VM has
    expected memory value via engine and via guest OS
    """
    __test__ = True
    he_params = {
        "memory": conf.EXPECTED_MEMORY,
        conf.MAX_MEMORY: conf.HE_VM_MAX_MEMORY
    }

    @polarion("RHEVM-15025")
    def test_he_vm_memory(self):
        """
        1) Check HE VM memory via the engine
        2) Check HE VM memory via guest OS
        """
        assert helpers.check_he_vm_memory_via_engine(
            expected_value=conf.EXPECTED_MEMORY
        )
        assert helpers.check_he_vm_memory_via_guest_os(
            expected_value=conf.EXPECTED_MEMORY
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    init_he_webadmin.__name__,
    update_he_vm.__name__,
    update_he_vm_cpus_back.__name__
)
@pytest.mark.incremental
class TestHotPlugAndUnplugCpus(u_libs.SlaTest):
    """
    Hotplug CPU's on HE VM and check that HE VM has
    expected amount of CPU's via engine and via guest OS
    """
    __test__ = True
    he_params = {
        conf.MAX_MEMORY: conf.HE_VM_MAX_MEMORY
    }

    @staticmethod
    def update_and_check_cpus(sockets):
        """
        1) Update HE VM sockets number
        2) Check that HE VM has the expected number of sockets

        Args:
            sockets (int): Number of sockets
        """
        u_libs.testflow.step("Update HE VM sockets number to %s", sockets)
        assert ll_vms.updateVm(
            positive=True, vm=conf.HE_VM_NAME, cpu_socket=sockets
        )
        assert helpers.check_he_vm_cpu_via_engine(expected_value=sockets)
        assert helpers.check_he_vm_cpu_via_guest_os(expected_value=sockets)

    @polarion("RHEVM-15027")
    def test_plug_cpu(self):
        """
        1) Check CPU hot plug
        """
        self.update_and_check_cpus(sockets=conf.EXPECTED_CPUS)

    @polarion("RHEVM-19141")
    def test_unplug_cpu(self):
        """
        1) Check CPU hot unplug
        """
        self.update_and_check_cpus(sockets=conf.DEFAULT_CPUS_VALUE)


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    init_he_webadmin.__name__,
    update_he_vm.__name__,
    wait_for_ovf_and_restart_he_vm.__name__,
    update_he_vm_cpus_back.__name__
)
class TestUpdateHeVmCpus(u_libs.SlaTest):
    """
    Update HE VM amount of CPU's and check that HE VM has
    expected amount of CPU's via engine and via guest OS
    """
    __test__ = True
    he_params = {
        "cpu_cores": 2,
        conf.MAX_MEMORY: conf.HE_VM_MAX_MEMORY
    }

    @polarion("RHEVM-15023")
    def test_he_vm_cpus(self):
        """
        1) Check HE VM CPU's via the engine
        2) Check HE VM CPU's via guest OS
        """
        assert helpers.check_he_vm_cpu_via_engine(
            expected_value=conf.EXPECTED_CPUS
        )
        assert helpers.check_he_vm_cpu_via_guest_os(
            expected_value=conf.EXPECTED_CPUS
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    init_he_webadmin.__name__
)
class TestAddNicToHeVmWithManagementNetwork(u_libs.SlaTest):
    """
    Add with management network NIC to HE VM
    """
    __test__ = True

    @polarion("RHEVM-17141")
    def test_add_nic(self):
        """
        Add NIC
        """
        u_libs.testflow.step(
            "Add NIC with the management network to the HE VM"
        )
        assert not ll_vms.addNic(
            positive=True,
            vm=conf.HE_VM_NAME,
            network=conf.MGMT_BRIDGE,
            name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    init_he_webadmin.__name__,
    wait_for_ovf_and_restart_he_vm.__name__,
    create_network.__name__,
    add_nic_to_he_vm.__name__
)
class TestAddNicToHeVmWithoutManagementNetwork(u_libs.SlaTest):
    """
    Add NIC to HE VM without management network and
    check if NIC appear under HE VM
    """
    __test__ = True

    @polarion("RHEVM-15026")
    def test_he_vm_nic(self):
        """
        Check NIC via engine and via guest OS, before and after HE VM restart
        """
        assert helpers.check_he_vm_nic_via_engine(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        assert helpers.check_he_vm_nic_via_guest_os(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        u_libs.testflow.step("Wait for the OVF update and restart HE VM")
        assert helpers.apply_new_parameters_on_he_vm()
        assert helpers.check_he_vm_nic_via_engine(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        assert helpers.check_he_vm_nic_via_guest_os(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )


@u_libs.attr(tier=3)
@pytest.mark.usefixtures(
    initialize_ge_constants.__name__,
    init_he_webadmin.__name__
)
@pytest.mark.incremental
class TestAddHostAndDeployHostedEngine(u_libs.SlaTest):
    """
    1) Add the host with HE deployment
    2) Undeploy the host
    3) Deploy the host
    """
    __test__ = True

    @staticmethod
    def _deploy_hosted_engine(deploy):
        """
        Deploy and undeploy helper method

        Args:
            deploy (bool): Deploy or undeploy the host
        """
        u_libs.testflow.step("Deactivate the host %s", conf.HOSTS[1])
        assert ll_hosts.deactivate_host(positive=True, host=conf.HOSTS[1])

        deploy_msg = "Deploy" if deploy else "Undeploy"
        deploy_param = {"deploy_hosted_engine": True} if deploy else {
            "undeploy_hosted_engine": True
        }
        u_libs.testflow.step("%s the host %s", deploy_msg, conf.HOSTS[1])
        assert ll_hosts.install_host(
            host=conf.HOSTS[1],
            root_password=conf.HOSTS_PW,
            **deploy_param
        )

        u_libs.testflow.step("Activate the host %s", conf.HOSTS[1])
        assert ll_hosts.activate_host(positive=True, host=conf.HOSTS[1])

        u_libs.testflow.step(
            "Wait until the engine will %s the host %s",
            deploy_msg.lower(), conf.HOSTS[1]
        )
        assert helpers.wait_until_host_will_deploy_he(
            host_name=conf.HOSTS[1], negative=not deploy
        )

    @polarion("RHEVM-17142")
    def test_add_host(self):
        """
        Add the host and deploy HE on it
        """
        if conf.GE:
            self._deploy_hosted_engine(deploy=False)

            u_libs.testflow.step(
                "Remove the host %s from the engine", conf.HOSTS[1]
            )
            assert ll_hosts.removeHost(
                positive=True, host=conf.HOSTS[1], deactivate=True
            )
        u_libs.testflow.step("Add the host %s to the engine", conf.HOSTS[1])
        assert ll_hosts.add_host(
            name=conf.HOSTS[1],
            address=conf.VDS_HOSTS[1].fqdn,
            root_password=conf.HOSTS_PW,
            cluster=conf.CLUSTER_NAME,
            deploy_hosted_engine=True
        )

        u_libs.testflow.step(
            "Wait until the host %s will HE configured", conf.HOSTS[1]
        )
        assert helpers.wait_until_host_will_deploy_he(host_name=conf.HOSTS[1])
        self._deploy_hosted_engine(deploy=False)
        self._deploy_hosted_engine(deploy=True)
