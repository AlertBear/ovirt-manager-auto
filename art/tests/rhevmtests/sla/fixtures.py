"""
SLA fixtures
"""
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as sla_config
import pytest


@pytest.fixture(scope="class")
def start_vms(request):
    """
    1) Start VM's
    """
    vms_to_start = request.node.cls.vms_to_start

    def fin():
        """
        1) Stop VM's
        """
        ll_vms.stop_vms_safely(vms_list=vms_to_start)
    request.addfinalizer(fin)

    ll_vms.start_vms(vm_list=vms_to_start)


@pytest.fixture(scope="class")
def stop_vms(request):
    vms_to_stop = request.node.cls.vms_to_stop

    def fin():
        """
        1) Stop VM's
        """
        ll_vms.stop_vms_safely(vms_list=vms_to_stop)
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def run_once_vms(request):
    """
    Run once VM's
    """
    vms_to_run = request.node.cls.vms_to_run

    def fin():
        """
        1) Stop VM's
        """
        ll_vms.stop_vms_safely(vms_list=vms_to_run.keys())
    request.addfinalizer(fin)

    for vm_name, run_once_params in vms_to_run.iteritems():
        host = run_once_params.get(sla_config.VM_RUN_ONCE_HOST)
        if host is not None:
            run_once_params[
                sla_config.VM_RUN_ONCE_HOST
            ] = sla_config.HOSTS[host]
    ll_vms.run_vms_once(vms=vms_to_run.keys(), **vms_to_run)


@pytest.fixture(scope="class")
def update_vms(request):
    """
    1) Update VM's
    """
    vms_to_params = request.node.cls.vms_to_params

    def fin():
        """
        1) Update VM's to default parameters
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
    hosts_to_activate_indexes = request.node.cls.hosts_to_activate_indexes

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


@pytest.fixture(scope="class")
def update_vms_to_default_parameters(request):
    update_to_default_params = request.node.cls.update_to_default_params

    def fin():
        """
        1) Update VM's to default parameters
        """
        for vm_name in update_to_default_params:
            ll_vms.updateVm(
                positive=True, vm=vm_name, **sla_config.DEFAULT_VM_PARAMETERS
            )
    request.addfinalizer(fin)
