"""
Common tests for upgrade.

Fixtures:
    We need to run our ansible for playbook after some preparation of
    resources. For this purpose you can use session scope fixtures (take a look
    at doc in upgrade_fixtures.py)

Ordering markers:
    To make sure that first test which will be executed is
    test_upgrade_engine (which executes ansible with engine-setup) we use
    pytest ordering plugin. If you have some tests which should be executed
    before or after this test, you can use the following decorators imported
    from art.unittest_lib to change their order:
        - @order_before_upgrade - run before ansible
        - @order_upgrade - run ansible
        - @order_before_upgrade_hosts - run after ansible, before hosts upgrade
        - @order_upgrade_hosts - for hosts upgrade
        - @order_after_upgrade_hosts - run after hosts upgrade
        - @order_upgrade_cluster - for cluster upgrade
        - @order_after_upgrade_cluster -run after cluster upgrade
        - @order_upgrade_dc - for data center upgrade
        - @order_after_upgrade - run after data center upgrade

    You have to use order markers to run tests only once in proper order!!!
    If you don't use them, your test will be executed twice (befor and after
    upgrade as the last tests). Create some base class for your team and use
    default marker @order_after_upgrade

Tiers and Teams:
    All the tests should be marked with proper team and tier.
    For tier use marker @attr(tier="upgrade"). For team use same as you used to
    use in rhevmtests.

Skipping tests after or before upgrade:
    Because we have the same tests for example in branch 4.0 and master, we
    don't want to collect and execute these tests which should be executed only
    once before or after upgrade depend on state in which the engine is. This
    is done by marks plugin in pytest_customization.
"""

import logging

from utilities.ansible_runner import (
    run_ansible_playbook,
    prepare_env_group_vars
)
from art.unittest_lib import testflow, UpgradeTest, order_upgrade

import config

logger = logging.getLogger(__name__)


class TestUpgradeCommon(UpgradeTest):
    __test__ = True

    @order_upgrade
    def test_upgrade_engine(self):
        """
        This test runs ansible which upgrades only the engine. This test won't
        be collected when upgrade_version == version so it won't be executed
        after upgrade.
        """

        testflow.step("Copy group_vars for environment upgrade engine.")
        assert prepare_env_group_vars(
            config.product, config.upgrade_version
        ), "Failed when copy groupvars!"
        testflow.step("Running ansible for upgrade engine.")
        rc, out, err = run_ansible_playbook(
            "ansible-playbooks/playbooks/ovirt-upgrade",
            "-e '{ovirt_upgrade_skip_hosts: True, "
            "ovirt_upgrade_packages_repos_update_all: True}'"
        )
        logger.info("Output of ansible commands: %s", out)
        log_msg = "Failed to exec ansible! RC: %s, out: %s, ERR: %s" % (
            rc, out, err
        )
        assert not rc, log_msg
