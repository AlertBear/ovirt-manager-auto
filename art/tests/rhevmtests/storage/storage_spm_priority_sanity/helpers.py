"""
Helpers function for spm_priority_sanity
"""
from rhevmtests.storage import config
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts,
)
from art.rhevm_api.tests_lib.high_level import (
    hosts as hl_hosts,
)
from art.unittest_lib import testflow


def deactivate_and_verify_hosts(hosts=config.HOSTS):
    """
    Deactivate given hosts and verify they reach to 'maintenance' state

    :param hosts: List of hosts to deactivate
    :type hosts: list
    :raise: HostException
    """
    testflow.step("Put hosts '%s' into maintenance mode", hosts)
    assert hl_hosts.deactivate_hosts_if_up(hosts), (
        "Unable to deactivate hosts: %s " % hosts
    )
    assert ll_hosts.waitForHostsStates(
        True, hosts, config.HOST_MAINTENANCE
    ), 'Hosts failed to enter maintenance mode'
