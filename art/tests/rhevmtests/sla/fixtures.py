"""
SLA fixtures
"""
import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import config as sla_config


@pytest.fixture(scope="class")
def stop_vms(request):
    vms_to_stop = getattr(request.node.cls, "vms_to_stop", None)

    def fin():
        """
        1) Stop VM
        """
        ll_vms.stop_vms_safely(vms_list=vms_to_stop)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def update_vms(request):
    """
    1) Pin VM to list of hosts
    """
    vms_to_params = request.node.cls.vms_to_params

    def fin():
        """
        1) Unpin VM
        """
        for vm_name in vms_to_params.iterkeys():
            ll_vms.updateVm(
                positive=True, vm=vm_name, **sla_config.DEFAULT_VM_PARAMETERS
            )
    request.addfinalizer(fin)

    for vm_name, vm_params in vms_to_params.iteritems():
        if sla_config.VM_PLACEMENT_HOSTS in vm_params:
            hosts = []
            for host_index in vm_params[sla_config.VM_PLACEMENT_HOSTS]:
                hosts.append(sla_config.HOSTS[host_index])
                vm_params[sla_config.VM_PLACEMENT_HOSTS] = hosts
        if sla_config.VM_PLACEMENT_HOST in vm_params:
            vm_params[sla_config.VM_PLACEMENT_HOST] = sla_config.HOSTS[
                vm_params[sla_config.VM_PLACEMENT_HOST]
            ]
        assert ll_vms.updateVm(
            positive=True, vm=vm_name, **vm_params
        )


@pytest.fixture(scope="class")
def activate_hosts(request):
    hosts_to_activate_indexes = request.node.cls.hosts_to_activate

    def fin():
        """
        1) Activate all hosts
        """
        hosts_to_activate = [
            sla_config.HOSTS[i] for i in hosts_to_activate_indexes
        ]
        for host_to_activate in hosts_to_activate:
            hl_hosts.activate_host_if_not_up(host=host_to_activate)
    request.addfinalizer(fin)
