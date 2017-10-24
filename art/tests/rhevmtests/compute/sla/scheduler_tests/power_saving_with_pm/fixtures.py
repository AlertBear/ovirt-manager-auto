"""
Power saving with power management test fixtures
"""
import time

import pytest

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.unittest_lib as u_lib
import rhevmtests.compute.sla.config as conf


@pytest.fixture(scope="class")
def power_on_host(request):
    """
    Power on the host via power management
    """
    host_down = getattr(request.node.cls, "host_down")

    if not host_down:
        return

    host_down = conf.HOSTS[host_down]

    def fin():
        if ll_hosts.get_host_status(host=host_down) == conf.HOST_DOWN:
            u_lib.testflow.teardown(
                "Wait %s seconds between fence operations",
                conf.FENCE_TIMEOUT
            )
            time.sleep(conf.FENCE_TIMEOUT)
            u_lib.testflow.teardown("Start the host %s", host_down)
            status = ll_hosts.fence_host(
                host=host_down, fence_type="start"
            )
            if (
                not status and
                ll_hosts.get_host_status(
                    host=host_down
                ) == conf.HOST_NONRESPONSIVE
            ):
                u_lib.testflow.teardown(
                    "Host %s non-responsive trying to restart it",
                    host_down
                )
                ll_hosts.fence_host(host=host_down, fence_type="restart")
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def disable_host_policy_control_flag(request):
    """
    Disable host policy_control_flag
    """
    def fin():
        """
        Enable host policy_control_flag
        """
        u_lib.testflow.teardown(
            "Enable the host %s policy control flag", conf.HOSTS[1]
        )
        assert ll_hosts.update_host(
            positive=True,
            host=conf.HOSTS[2],
            pm=True,
            pm_automatic=True
        )
    request.addfinalizer(fin)

    u_lib.testflow.setup(
        "Disable the host %s policy control flag", conf.HOSTS[1]
    )
    assert ll_hosts.update_host(
        positive=True,
        host=conf.HOSTS[2],
        pm=True,
        pm_automatic=False
    )
