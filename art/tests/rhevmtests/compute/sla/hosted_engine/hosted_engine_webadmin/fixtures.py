"""
HE webadmin fixtures
"""
import time

import art.unittest_lib as test_libs
import config as conf
import helpers
import pytest
from art.rhevm_api.tests_lib.high_level import (
    host_network as hl_host_network,
    networks as hl_networks,
)
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
    vms as ll_vms
)


@pytest.fixture(scope="module")
def initialize_ge_constants():
    """
    Initialize HE constants
    """
    if not ll_hosts.is_hosted_engine_configured(conf.HOSTS[0]):
        pytest.skip("GE does not configured as HE environment")

    conf.INIT_HE_VM_CPUS = ll_vms.get_vm_processing_units_number(
        vm_name=conf.HE_VM
    )
    conf.EXPECTED_CPUS = 2 * conf.INIT_HE_VM_CPUS


@pytest.fixture(scope="class")
def enable_global_maintenance(request):
    """
    Enable global maintenance
    """
    def fin():
        test_libs.testflow.teardown("Disable global maintenance")
        helpers.run_hosted_engine_cli_command(
            resource=conf.VDS_HOSTS[0],
            command=["--set-maintenance", "--mode=%s" % conf.MAINTENANCE_NONE]
        )
        helpers.wait_for_hosts_he_attributes(
            hosts_names=conf.HOSTS[:1],
            expected_values={
                conf.PARAMS_HE_GLOBAL_MAINTENANCE: False,
                conf.PARAMS_HE_SCORE: 3400
            },
            testflow_func=test_libs.testflow.teardown
        )
    request.addfinalizer(fin)

    test_libs.testflow.setup("Enable 'GlobalMaintenance'")
    helpers.run_hosted_engine_cli_command(
        resource=conf.VDS_HOSTS[0],
        command=["--set-maintenance", "--mode=%s" % conf.MAINTENANCE_GLOBAL]
    )
    assert helpers.wait_for_hosts_he_attributes(
        hosts_names=conf.HOSTS[:1],
        expected_values={
            conf.PARAMS_HE_GLOBAL_MAINTENANCE: True,
            conf.PARAMS_HE_SCORE: 3400
        },
        testflow_func=test_libs.testflow.setup
    )


@pytest.fixture(scope="class")
def update_he_vm(request):
    """
    1) Update the HE VM
    """
    he_params = request.node.cls.he_params

    test_libs.testflow.setup(
        "Update the VM %s with parameters %s", conf.HE_VM, he_params
    )
    assert ll_vms.updateVm(positive=True, vm=conf.HE_VM, **he_params)


@pytest.fixture(scope="class")
def restart_he_vm():
    """
    1) Wait for the OVF update and restart the HE VM
    """
    test_libs.testflow.setup(
        "Give %ss to make sure that the engine updates OVF",
        conf.SLEEP_OVF_UPDATE
    )
    time.sleep(conf.SLEEP_OVF_UPDATE)

    test_libs.testflow.setup("Apply new parameters on the HE VM")
    assert helpers.apply_new_parameters_on_he_vm()


@pytest.fixture(scope="class")
def update_he_vm_cpus():
    """
    Update the HE VM number of CPU's
    """
    test_libs.testflow.setup(
        "Update the HE VM CPU's to %s", conf.EXPECTED_CPUS
    )
    assert ll_vms.updateVm(
        positive=True,
        vm=conf.HE_VM,
        cpu_socket=conf.EXPECTED_CPUS,
        cpu_cores=1
    )
    test_libs.testflow.setup("Apply new parameters on the HE VM")
    assert helpers.apply_new_parameters_on_he_vm()


@pytest.fixture(scope="class")
def update_he_vm_cpus_back(request):
    """
    Update the HE VM CPU's to the default value
    """
    def fin():
        test_libs.testflow.teardown(
            "Update the HE VM CPU's to %s", conf.INIT_HE_VM_CPUS
        )
        ll_vms.updateVm(
            positive=True,
            vm=conf.HE_VM,
            cpu_socket=conf.INIT_HE_VM_CPUS,
            cpu_cores=1
        )
        test_libs.testflow.teardown("Apply new parameters on the HE VM")
        helpers.apply_new_parameters_on_he_vm()
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def create_network(request):
    """
    1) Create and attach network to the cluster
    2) Attach network to the host
    """
    def fin():
        """
        1) Remove network from the host and remove the network
        """
        test_libs.testflow.teardown(
            "Remove the network %s from the datacenter %s",
            conf.TEST_NETWORK, conf.DC_NAME[0]
        )
        hl_networks.remove_net_from_setup(
            host=[conf.HOSTS[0]],
            network=[conf.TEST_NETWORK],
            data_center=conf.DC_NAME[0]
        )
    request.addfinalizer(fin)

    assert hl_networks.create_and_attach_networks(
        data_center=conf.DC_NAME[0],
        clusters=[conf.CLUSTER_NAME[0]],
        networks={conf.TEST_NETWORK: {"required": False}}
    )
    sn_dict = {
        "add": {
            conf.TEST_NETWORK: {
                "datacenter": conf.DC_NAME[0],
                "network": conf.TEST_NETWORK,
                "nic": conf.VDS_HOSTS[0].nics[1]
            }
        }
    }
    assert hl_host_network.setup_networks(host_name=conf.HOSTS[0], **sn_dict)


@pytest.fixture(scope="class")
def add_nic_to_he_vm(request):
    """
    Add NIC to HE VM
    """
    def fin():
        test_libs.testflow.teardown(
            "Unplug NIC %s from the HE VM", conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        ll_vms.updateNic(
            positive=True,
            vm=conf.HE_VM,
            nic=conf.ADDITIONAL_HE_VM_NIC_NAME,
            plugged=False
        )
        test_libs.testflow.teardown(
            "Remove the NIC %s from the HE VM", conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        ll_vms.removeNic(
            positive=True,
            vm=conf.HE_VM,
            nic=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
    request.addfinalizer(fin)

    test_libs.testflow.setup(
        "Add NIC %s with network %s to HE VM",
        conf.ADDITIONAL_HE_VM_NIC_NAME, conf.TEST_NETWORK
    )
    assert ll_vms.addNic(
        positive=True,
        vm=conf.HE_VM,
        name=conf.ADDITIONAL_HE_VM_NIC_NAME,
        network=conf.TEST_NETWORK,
        plugged=True,
        linked=True
    )


@pytest.fixture(scope="class")
def not_enough_cpus_skip_test():
    """
    Skip the test if the host where runs HE VM does not have enough CPU's
    """
    he_vm_host = ll_vms.get_vm_host(vm_name=conf.HE_VM)
    he_vm_host_cpus = (
        ll_hosts.get_host_sockets(host_name=he_vm_host) *
        ll_hosts.get_host_cores(host_name=he_vm_host)
    )
    if he_vm_host_cpus < conf.EXPECTED_CPUS:
        pytest.skip("Host %s does not have enough CPU's" % he_vm_host)


@pytest.fixture(scope="class")
def undeploy_he_host(request):
    """
    Undeploy hosted engine from the host
    """
    def fin():
        """
        Deploy host as hosted engine host
        """
        if not ll_hosts.is_host_exist(host=conf.HOSTS[1]):
            assert ll_hosts.add_host(
                name=conf.HOSTS[1],
                address=conf.VDS_HOSTS[1].fqdn,
                root_password=conf.HOSTS_PW,
                cluster=conf.CLUSTER_NAME[0],
                deploy_hosted_engine=True
            )
    request.addfinalizer(fin)

    assert helpers.deploy_hosted_engine_on_host(deploy=False)

    test_libs.testflow.step(
        "Remove the host %s from the engine", conf.HOSTS[1]
    )
    assert ll_hosts.remove_host(
        positive=True, host=conf.HOSTS[1], deactivate=True
    )
