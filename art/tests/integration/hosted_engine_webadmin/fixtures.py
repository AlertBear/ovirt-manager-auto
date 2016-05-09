"""
HE webadmin fixtures
"""
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as test_libs
import config as conf
import helpers
import pytest


@pytest.fixture(scope="class")
def update_he_vm(request):
    """
    1) Update the HE VM
    """
    he_params = request.node.cls.he_params

    test_libs.testflow.setup(
        "Update the VM %s with parameters %s", conf.HE_VM_NAME, he_params
    )
    assert ll_vms.updateVm(positive=True, vm=conf.HE_VM_NAME, **he_params)


@pytest.fixture(scope="class")
def wait_for_ovf_and_restart_he_vm():
    """
    1) Wait for the OVF update and restart the HE VM
    """
    test_libs.testflow.setup("Apply new parameters on the HE VM")
    assert helpers.apply_new_parameters_on_he_vm()


@pytest.fixture(scope="class")
def update_he_vm_cpus_back(request):
    """
    Update the HE VM CPU's to the default value
    """
    def fin():
        test_libs.testflow.teardown(
            "Update the HE VM CPU's to %s", conf.DEFAULT_CPUS_VALUE
        )
        ll_vms.updateVm(
            positive=True,
            vm=conf.HE_VM_NAME,
            cpu_socket=conf.DEFAULT_CPUS_VALUE,
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
            conf.TEST_NETWORK, conf.DC_NAME
        )
        hl_networks.remove_net_from_setup(
            host=[conf.HOSTS[0]],
            network=[conf.TEST_NETWORK],
            data_center=conf.DC_NAME
        )
    request.addfinalizer(fin)

    test_libs.testflow.setup(
        "Create new network %s and attach it to the cluster %s",
        conf.TEST_NETWORK, conf.CLUSTER_NAME
    )
    assert hl_networks.create_and_attach_networks(
        data_center=conf.DC_NAME,
        cluster=conf.CLUSTER_NAME,
        network_dict={conf.TEST_NETWORK: {"required": False}}
    )
    sn_dict = {
        "add": {
            conf.TEST_NETWORK: {
                "datacenter": conf.DC_NAME,
                "network": conf.TEST_NETWORK,
                "nic": conf.VDS_HOSTS[0].nics[1]
            }
        }
    }
    test_libs.testflow.setup(
        "Create %s via setup_network on host %s", sn_dict, conf.HOSTS[0]
    )
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
        ll_vms.hotUnplugNic(
            positive=True,
            vm=conf.HE_VM_NAME,
            nic=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        test_libs.testflow.teardown(
            "Remove the NIC %s from the HE VM", conf.ADDITIONAL_HE_VM_NIC_NAME
        )
        ll_vms.removeNic(
            positive=True,
            vm=conf.HE_VM_NAME,
            nic=conf.ADDITIONAL_HE_VM_NIC_NAME
        )
    request.addfinalizer(fin)

    test_libs.testflow.setup(
        "Add NIC %s with network %s to HE VM",
        conf.ADDITIONAL_HE_VM_NIC_NAME, conf.TEST_NETWORK
    )
    assert ll_vms.addNic(
        positive=True,
        vm=conf.HE_VM_NAME,
        name=conf.ADDITIONAL_HE_VM_NIC_NAME,
        network=conf.TEST_NETWORK,
        plugged=True,
        linked=True
    )
