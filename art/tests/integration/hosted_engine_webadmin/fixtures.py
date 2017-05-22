"""
HE webadmin fixtures
"""
import pytest

import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_sds
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as test_libs
import config as conf
import helpers
from art.rhevm_api import resources


@pytest.fixture(scope="module")
def initialize_ge_constants():
    """
    Initialize hosts constants
    """
    if conf.GE:
        golden_env = conf.ART_CONFIG["prepared_env"]
        dc = golden_env["dcs"][0]
        conf.DC_NAME = dc["name"]
        clusters = dc["clusters"]
        conf.CLUSTER_NAME = clusters[0]["name"]
        for cluster in clusters:
            for host in cluster["hosts"]:
                conf.HOSTS.append(host["name"])
        host_objs = ll_hosts.HOST_API.get(abs_link=False)
        conf.HOSTS_IP = [host_obj.get_address() for host_obj in host_objs]
        if not ll_hosts.is_hosted_engine_configured(conf.HOSTS[0]):
            pytest.skip("GE does not configured as HE environment")
    conf.VDS_HOSTS = [resources.VDS(h, conf.HOSTS_PW) for h in conf.HOSTS_IP]
    conf.INIT_HE_VM_CPUS = ll_vms.get_vm_processing_units_number(
        vm_name=conf.HE_VM_NAME
    )
    conf.EXPECTED_CPUS = 2 * conf.INIT_HE_VM_CPUS


@pytest.fixture(scope="module")
def init_he_webadmin(request):
    """
    1) Wait for the engine to be up
    2) Enable global maintenance
    3) Change the OVF update interval to one minute
    4) Add storage domain to the engine to start auto-import
    5) Wait until HE VM will appear under engine
    6) Wait for up state of HE VM
    """
    def fin():
        test_libs.testflow.teardown(
            "Set engine-config parameter %s to %s",
            conf.OVF_UPDATE_INTERVAL, conf.DEFAULT_OVF_UPDATE_INTERVAL_VALUE
        )
        helpers.change_engine_config_ovf_update_interval()
        test_libs.testflow.teardown("Disable global maintenance")
        helpers.run_hosted_engine_cli_command(
            resource=conf.VDS_HOSTS[0],
            command=["--set-maintenance", "--mode=%s" % conf.MAINTENANCE_NONE]
        )
    request.addfinalizer(fin)

    test_libs.testflow.setup("Wait until the engine will be UP")
    assert conf.ENGINE.wait_for_engine_status_up(timeout=conf.SAMPLER_TIMEOUT)
    if not conf.GE:
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
    he_vm_host = ll_vms.get_vm_host(vm_name=conf.HE_VM_NAME)
    if he_vm_host != conf.HOSTS[0]:
        test_libs.testflow.setup(
            "Migrate the VM %s to the host %s", conf.HE_VM_NAME, conf.HOSTS[0]
        )
        assert ll_vms.migrateVm(
            positive=True, vm=conf.HE_VM_NAME, host=conf.HOSTS[0], force=True
        )
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
    test_libs.testflow.setup("Wait for the OVF generation and restart HE VM")
    helpers.apply_new_parameters_on_he_vm()


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
            "Update the HE VM CPU's to %s", conf.INIT_HE_VM_CPUS
        )
        ll_vms.updateVm(
            positive=True,
            vm=conf.HE_VM_NAME,
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
            conf.TEST_NETWORK, conf.DC_NAME
        )
        hl_networks.remove_net_from_setup(
            host=[conf.HOSTS[0]],
            network=[conf.TEST_NETWORK],
            data_center=conf.DC_NAME
        )
    request.addfinalizer(fin)

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
            vm=conf.HE_VM_NAME,
            nic=conf.ADDITIONAL_HE_VM_NIC_NAME,
            plugged=False
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


@pytest.fixture(scope="class")
def not_enough_cpus_skip_test():
    """
    Skip the test if the host where runs HE VM does not have enough CPU's
    """
    he_vm_host = ll_vms.get_vm_host(vm_name=conf.HE_VM_NAME)
    he_vm_host_cpus = (
        ll_hosts.get_host_sockets(host_name=he_vm_host) *
        ll_hosts.get_host_cores(host_name=he_vm_host)
    )
    if he_vm_host_cpus < conf.EXPECTED_CPUS:
        pytest.skip("Host %s does not have enough CPU's" % he_vm_host)
