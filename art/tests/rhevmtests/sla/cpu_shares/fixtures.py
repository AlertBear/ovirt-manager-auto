"""
CPU Share Fixtures
"""
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import pytest


@pytest.fixture(scope="class")
def update_vms_cpu_share(request):
    """
    1) Update VM's CPU share
    """
    vms_cpu_shares = request.node.cls.vms_cpu_shares
    for vm_name, cpu_shares in vms_cpu_shares.iteritems():
        assert ll_vms.updateVm(
            positive=True, vm=vm_name, cpu_shares=cpu_shares
        )
