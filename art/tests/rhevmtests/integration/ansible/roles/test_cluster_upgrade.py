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

    @polarion("RHEVM-21914")
    def test_cluster_upgrade_sanity(self):
        """
        Cluster Upgrade Sanity
        Update only host where update is available
        """
        ansible = common.AnsibleRunner("cluster-upgrade")

        testflow.setup(
            "oVirt Ansible roles variables {ansible_vars}".format(
                ansible_vars=ansible.get_vars()
            )
        )

        testflow.step('Saving information about state of engine')
        checker = common.Checker()

        testflow.step('Running ansible playbook.')
        ansible.run()

        testflow.step("Checking upgrade from events")
        checker.upgrade(ansible)

    @polarion("RHEVM-25132")
    def test_cluster_upgrade_check_updates_sanity(self):
        """
        Cluster Upgrade Sanity
        Run check for update in playbook
        Update only host where update is available
        """
        ansible = common.AnsibleRunner("cluster-upgrade")
        ansible.set_var("check_upgrade", True)

        testflow.setup(
            "oVirt Ansible roles variables {ansible_vars}".format(
                ansible_vars=ansible.get_vars()
            )
        )

        testflow.step('Saving information about state of engine')
        checker = common.Checker()

        testflow.step('Running ansible playbook.')
        ansible.run()

        testflow.step("Checking upgrade from events")
        checker.upgrade(ansible)
