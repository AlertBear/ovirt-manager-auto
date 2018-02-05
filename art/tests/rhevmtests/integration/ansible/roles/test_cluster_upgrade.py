"""
Testing oVirt Ansible role - oVirt Cluster Upgrade
"""
from art.test_handler.tools import polarion
from art.unittest_lib import CoreSystemTest as TestCase
from art.unittest_lib import testflow
from art.unittest_lib import tier2

import common


@tier2
class TestAnsibleRoleClusterUpgrade(TestCase):
    """ Sanity testing of Ansible Role oVirt Cluster Upgrade """

    @polarion('RHEVM-21914')
    def test_cluster_upgrade_sanity(self):
        """
        Cluster Upgrade Sanity
        Update only host where update is available
        """
        cluster_upgrade = common.AnsibleRunner('cluster-upgrade')

        testflow.setup('Saving information about state of engine')
        checker = common.Checker()

        testflow.setup(
            'oVirt Ansible roles variables {ansible_vars}'.format(
                ansible_vars=cluster_upgrade.get_vars()
            )
        )

        testflow.step('Running oVirt ansible role')
        cluster_upgrade.run()

        testflow.step('Check result')
        checker.upgrade(cluster_upgrade)

    @polarion('RHEVM-25132')
    def test_cluster_upgrade_check_updates_sanity(self):
        """
        Cluster Upgrade Sanity
        Run check for update in playbook
        Update only host where update is available
        """
        cluster_upgrade = common.AnsibleRunner('cluster-upgrade')

        testflow.setup('Saving information about state of engine')
        checker = common.Checker()

        cluster_upgrade.set_var('check_upgrade', True)

        testflow.setup(
            'oVirt Ansible roles variables {ansible_vars}'.format(
                ansible_vars=cluster_upgrade.get_vars()
            )
        )

        testflow.step('Running oVirt ansible role')
        cluster_upgrade.run()

        testflow.step('Check result')
        checker.upgrade(cluster_upgrade)
