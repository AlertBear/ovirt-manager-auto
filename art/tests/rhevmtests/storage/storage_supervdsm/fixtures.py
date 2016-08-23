"""
Fixtures for supervdsm module
"""
import pytest
import config
import logging
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts
)

logger = logging.getLogger(__name__)


@pytest.fixture()
def check_host_up(request, storage):
    """
    Check the host is in status UP and get the host ip
    """
    self = request.node.cls

    # Wait a few seconds for host to be up
    ll_hosts.wait_for_hosts_states(
        True, config.HOSTS[0], states=config.HOST_UP, timeout=30
    )
    # If there's a problem with vdsm the host switches between
    # non_operational - non_responsive status
    if not ll_hosts.is_host_up(True, config.HOSTS[0]):
        logger.error(
            "Host %s was down unexpectedly. Starting it up" %
            config.HOSTS[0]
        )
        assert ll_hosts.activate_host(
            True, config.HOSTS[0]
        ), "Host %s was not activated" % config.HOSTS[0]
    self.host_ip = ll_hosts.get_host_ip(config.HOSTS[0])


@pytest.fixture()
def restore_supervdsm_files(request, storage):
    """
    Make sure to restore supervdsm log file
    """
    self = request.node.cls

    def finalizer():
        self.host_resource.service(config.VDSMD).stop()
        self.executor.run_cmd(["touch", config.SUPERVDSM_LOG])
        self.executor.run_cmd(["chmod", "0644", config.SUPERVDSM_LOG])
        self.executor.run_cmd(["chown", "vdsm:kvm", config.SUPERVDSM_LOG])
        self.host_resource.service(config.SUPERVDSMD).start()
        # for supporting rhel versions that stopping supervdsm stopps vdsm
        # (rhel7 and up)
        self.host_resource.service(config.VDSMD).start()
        # After start vdsm wait for host to be up
        ll_hosts.wait_for_hosts_states(
            True, config.HOSTS[0], states=config.HOST_UP, timeout=60
        )

        # after restarting supervdsm, run vdsm command that requires
        # supervdsm in order to trigger reconnection between supervdsm and vdsm
        self.executor.run_cmd(config.HW_INFO_COMMAND)
    request.addfinalizer(finalizer)
