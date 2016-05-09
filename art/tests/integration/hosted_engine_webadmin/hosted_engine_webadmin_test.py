"""
Test HE behaviour via the engine
"""
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_sds
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as test_libs
import config as conf
import helpers
import pytest
from art.test_handler.tools import polarion
from fixtures import (
    add_nic_to_he_vm,
    create_network,
    update_he_vm,
    update_he_vm_cpus_back,
    wait_for_ovf_and_restart_he_vm
)


@pytest.fixture(scope="module", autouse=True)
def init_he_webadmin():
    """
    1) Wait for the engine to be up
    2) Enable global maintenance
    3) Change the OVF update interval to one minute
    4) Add storage domain to the engine to start auto-import
    5) Wait until HE VM will appear under engine
    6) Wait for up state of HE VM
    """
    test_libs.testflow.setup("Wait until the engine will be UP")
    assert conf.ENGINE.wait_for_engine_status_up(timeout=conf.SAMPLER_TIMEOUT)
    test_libs.testflow.setup("Enable 'GlobalMaintenance'")
    helpers.run_hosted_engine_cli_command(
        resource=conf.VDS_HOSTS[0],
        command=["--set-maintenance", "--mode=%s" % conf.MAINTENANCE_GLOBAL]
    )
    test_libs.testflow.setup(
        "Set engine-config parameter %s to %s",
        conf.OVF_UPDATE_INTERVAL, conf.OVF_UPDATE_INTERVAL_VALUE
    )
    assert helpers.change_engine_config_ovf_update_interval()
    test_libs.testflow.setup(
        "Add master storage domain %s:%s",
        conf.PARAMETERS["data_domain_address"],
        conf.PARAMETERS["data_domain_path"]
    )
    assert hl_sds.create_storages(
        storage=conf.PARAMETERS,
        type_=conf.STORAGE_TYPE,
        host=conf.HOSTS[0],
        datacenter=conf.DC_NAME
    )
    test_libs.testflow.setup(
        "Wait until the HE VM will be appear under the engine"
    )
    assert helpers.wait_until_he_vm_will_appear_under_engine()
    test_libs.testflow.setup("Wait until the HE VM will have state UP")
    assert ll_vms.waitForVMState(vm=conf.HE_VM_NAME)
    test_libs.testflow.setup("Wait for the OVF generation and restart HE VM")
    helpers.apply_new_parameters_on_he_vm()


@pytest.mark.usefixtures(
    update_he_vm.__name__,
    wait_for_ovf_and_restart_he_vm.__name__
)
class TestUpdateHeVmMemory(test_libs.SlaTest):
    """
    Update HE VM memory and check that HE VM has
    expected memory value via engine and via guest OS
    """
    __test__ = True
    he_params = {"memory": conf.EXPECTED_MEMORY}

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


@pytest.mark.usefixtures(
    update_he_vm.__name__,
    update_he_vm_cpus_back.__name__
)
class TestHotplugHeVmCpus(test_libs.SlaTest):
    """
    Hotplug CPU's on HE VM and check that HE VM has
    expected amount of CPU's via engine and via guest OS
    """
    __test__ = True
    he_params = {"cpu_socket": conf.EXPECTED_CPUS}

    @polarion("RHEVM-15027")
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


@pytest.mark.usefixtures(
    update_he_vm.__name__,
    wait_for_ovf_and_restart_he_vm.__name__,
    update_he_vm_cpus_back.__name__
)
class TestUpdateHeVmCpus(test_libs.SlaTest):
    """
    Update HE VM amount of CPU's and check that HE VM has
    expected amount of CPU's via engine and via guest OS
    """
    __test__ = True
    he_params = {"cpu_cores": 2}

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


class TestAddNicToHeVmWithManagementNetwork(test_libs.SlaTest):
    """
    Add with management network NIC to HE VM
    """
    __test__ = True

    @polarion("RHEVM-17141")
    def test_add_nic(self):
        """
        Add NIC
        """
        test_libs.testflow.step(
            "Add NIC with the management network to the HE VM"
        )
        assert not ll_vms.addNic(
            positive=True,
            vm=conf.HE_VM_NAME,
            network=conf.MGMT_BRIDGE,
            name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )


@pytest.mark.usefixtures(
    wait_for_ovf_and_restart_he_vm.__name__,
    create_network.__name__,
    add_nic_to_he_vm.__name__
)
class TestAddNicToHeVmWithoutManagementNetwork(test_libs.SlaTest):
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
        helpers.check_he_vm_nic_via_engine(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        helpers.check_he_vm_nic_via_guest_os(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        test_libs.testflow.step("Wait for the OVF update and restart HE VM")
        helpers.apply_new_parameters_on_he_vm()
        helpers.check_he_vm_nic_via_engine(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        helpers.check_he_vm_nic_via_guest_os(
            nic_name=conf.ADDITIONAL_HE_VM_NIC_NAME
        )


@pytest.mark.incremental
class TestAddHostAndDeployHostedEngine(test_libs.SlaTest):
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
        test_libs.testflow.step("Deactivate the host %s", conf.HOSTS[1])
        assert ll_hosts.deactivate_host(positive=True, host=conf.HOSTS[1])

        deploy_msg = "Deploy" if deploy else "Undeploy"
        deploy_param = {"deploy_hosted_engine": True} if deploy else {
            "undeploy_hosted_engine": True
        }
        test_libs.testflow.step("%s the host %s", deploy_msg, conf.HOSTS[1])
        assert ll_hosts.install_host(
            host=conf.HOSTS[1],
            root_password=conf.HOSTS_PW,
            **deploy_param
        )

        test_libs.testflow.step("Activate the host %s", conf.HOSTS[1])
        assert ll_hosts.activate_host(positive=True, host=conf.HOSTS[1])

        test_libs.testflow.step(
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
        self._deploy_hosted_engine(deploy=False)
        test_libs.testflow.step("Remove the host %s", conf.HOSTS[1])
        assert ll_hosts.removeHost(
            positive=True, host=conf.HOSTS[1], deactivate=True
        )

        test_libs.testflow.step("Add the host %s to the engine", conf.HOSTS[1])
        assert ll_hosts.add_host(
            name=conf.HOSTS[1],
            address=conf.VDS_HOSTS[1].fqdn,
            root_password=conf.HOSTS_PW,
            deploy_hosted_engine=True
        )

        test_libs.testflow.step(
            "Wait until the host %s will HE configured", conf.HOSTS[1]
        )
        assert helpers.wait_until_host_will_deploy_he(host_name=conf.HOSTS[1])
        self._deploy_hosted_engine(deploy=False)
        self._deploy_hosted_engine(deploy=True)
