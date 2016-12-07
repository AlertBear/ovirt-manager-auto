"""
Helpers function for spm_priority_sanity
"""
from rhevmtests.storage import config
from art.rhevm_api.tests_lib.high_level import (
    hosts as hl_hosts,
)
from art.unittest_lib import testflow


def deactivate_and_verify_hosts(hosts=config.HOSTS):
    """
    Deactivate given hosts and verify they reach to 'maintenance' state

    Args:
        hosts (list): List of hosts to deactivate

    Raises:
        HostException: If deactivate host fail
    """
    testflow.step("Put hosts '%s' into maintenance mode", hosts)
    assert hl_hosts.deactivate_hosts_if_up(hosts), (
        "Unable to deactivate hosts: %s " % hosts
    )
