"""
Scheduler sanity test fixtures
"""
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import pytest


@pytest.fixture(scope="class")
def update_vms_nics(request):
    """
    1) Update VM's NIC's
    """
    vms_nics_to_params = request.node.cls.vms_nics_to_params

    def fin():
        for vm_name in vms_nics_to_params.iterkeys():
            for vm_nic in vms_nics_to_params[vm_name].iterkeys():
                u_libs.testflow.teardown(
                    "Update the VM %s to use the network %s",
                    vm_name, conf.MGMT_BRIDGE
                )
                ll_vms.updateNic(
                    positive=True,
                    vm=vm_name,
                    nic=vm_nic,
                    network=conf.MGMT_BRIDGE
                )
    request.addfinalizer(fin)

    for vm_name in vms_nics_to_params.iterkeys():
        for vm_nic, nic_params in vms_nics_to_params[vm_name].iteritems():
            u_libs.testflow.setup(
                "Update the VM %s NIC %s with parameters %s",
                vm_name, vm_nic, nic_params
            )
            ll_vms.updateNic(
                positive=True, vm=vm_name, nic=vm_nic, **nic_params
            )


@pytest.fixture(scope="class")
def create_network(request):
    """
    1) Create and attach network to the cluster
    """
    network_name = request.node.cls.network_name

    def fin():
        """
        1) Remove the network
        """
        u_libs.testflow.teardown(
            "Remove the network %s from the datacenter %s",
            network_name, conf.DC_NAME[0]
        )
        hl_networks.remove_net_from_setup(
            host=[],
            network=[network_name],
            data_center=conf.DC_NAME[0]
        )
    request.addfinalizer(fin)

    assert hl_networks.create_and_attach_networks(
        data_center=conf.DC_NAME[0],
        clusters=[conf.CLUSTER_NAME[0]],
        networks={network_name: {}}
    )
