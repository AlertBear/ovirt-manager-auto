import copy
import json
import logging

from art.rhevm_api.tests_lib.low_level import events as ll_events
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
from art.unittest_lib import testflow
from utilities.ansible_runner import run_ansible_playbook

import config

logger = logging.getLogger(__name__)


class AnsibleRunner():
    """
    AnsibleRunner is wrapper for running specific playbook
    with predefined default variables and with additional custom variables.
    """
    def __init__(self, role):
        self.role = role
        self.extra_vars = copy.deepcopy(config.ANSIBLE_DEFAULT_EXTRA_VARS)

    def set_var(self, var_name, var_value):
        self.extra_vars[var_name] = var_value

    def get_vars(self):
        """
        Get all ansible variables
        Returns:
            dictionary of variables
        """
        return self.extra_vars

    def get_var(self, var_name):
        """
        get specific variable from ansible extra vars by name
        Args:
            var_name: name of ansible variable
        Returns:
            if variable exists, return value
            if variable doesn't exists, return None

        """
        if var_name in self.extra_vars:
            return self.extra_vars[var_name]
        else:
            return None

    def run(self):
        """
        run a playbook with defined variables
        """
        rc, out, err = run_ansible_playbook(
            '{ansible_path}/{tested_role}'.format(
                ansible_path=config.OVIRT_ANSIBLE_ROLES_PATH,
                tested_role=self.role
            ),
            "-e '{variables}'".format(
                variables=json.dumps(self.extra_vars)
            )
        )

        log_msg = 'Failed to exec ansible! RC: %s,\n out: %s,\n ERR: %s\n' % (
            rc, out, err
        )

        assert rc == 0, log_msg


class Checker():
    """
    EventChecker is class mainly for investigating events.
    Some tasks can't be checked directly after playbook run
    (amount of memory, number of CPU). It must be done via events.
    """
    def __init__(self):
        # save all host with available update
        self._update_available = [
            host for host in config.ENGINE_HOSTS
            if ll_hosts.is_upgrade_available(host)
        ]

        # save last event ID as mark for searching events
        self.start_event_id = ll_events.get_max_event_id()

    def _check_for_update(self):
        """
        Function for checking which hosts perform check for upgrade
        Returns:
            list of hosts which were checked
            list of hosts with available update
        """
        checked = []
        available_update = []

        for host in config.ENGINE_HOSTS:
            if ll_events.wait_for_event(
                config.HOST_CHECK_START.format(host=host),
                start_id=self.start_event_id
            ):
                checked.append(host)
            else:
                continue

            if ll_events.wait_for_event(
                config.HOST_CHECK_FINISH_AVAILABLE_UPDATE.format(host=host),
                start_id=self.start_event_id
            ):
                available_update.append(host)

        return checked, available_update

    def _check_upgrade(self):
        """
        Function to get lists of hosts which were upgraded,
        failed and not upgraded
        Returns:
            upgraded_hosts: list of upgraded hosts
            not_upgraded_hosts: list of not upgraded hosts
            failed_hosts: list of failed hosts
        """
        upgraded_hosts = []
        not_upgraded_hosts = []
        failed_hosts = []

        for host in config.ENGINE_HOSTS:
            if not ll_events.wait_for_event(
                    config.HOST_STARTED_UPGRADE.format(host=host),
                    start_id=self.start_event_id
            ):
                not_upgraded_hosts.append(host)
                continue

            if not ll_events.wait_for_event(
                config.HOST_FINISHED_UPGRADE.format(host=host),
                start_id=self.start_event_id
            ):
                failed_hosts.append(host)
                continue

            upgraded_hosts.append(host)

        if upgraded_hosts:
            # number of cluster update events
            # in case of upgrading, there should be two events
            # (normal -> maintenance, maintenance -> normal)

            status = ll_events.search_for_recent_event_from_event_id(
                positive=True,
                win_start_event_id=self.start_event_id,
                query=config.CLUSTER_UPDATED_MSG.format(
                    cluster=config.ANSIBLE_ENGINE_CLUSTER_NAME
                ),
                expected_count=2
            )

            assert not status, 'Cluster is still in maintenance state'

            testflow.step(
                "Hosts: {hosts} were upgraded".format(
                    hosts=upgraded_hosts
                )
            )

        else:
            testflow.step("None upgraded hosts")

        testflow.step(
            "Not updated hosts: {hosts}".format(
                hosts=not_upgraded_hosts
            )
        )

        return upgraded_hosts, not_upgraded_hosts, failed_hosts

    def upgrade(self, ansible_runner):
        """
        Method for checking upgrade of hosts from events
        Args:
            ansible_runner: object with variables from ansible run

        Returns:
            None

        """
        hosts_to_be_upgraded = ansible_runner.get_var("host_names")
        if not hosts_to_be_upgraded:
            hosts_to_be_upgraded = config.ENGINE_HOSTS

        hosts_to_be_left = [
            host for host in config.ENGINE_HOSTS
            if host not in hosts_to_be_upgraded
        ]

        logger.info('Hosts: %s are proceed to upgrade', hosts_to_be_upgraded)
        logger.info('Hosts: %s shouldn\'t be upgraded', hosts_to_be_left)

        update_available = []

        hosts_upgraded = []
        hosts_left = []

        checked, update_available = self._check_for_update()

        if ansible_runner.get_var("check_upgrade"):
            err_msg = (
                "Different hosts checked for update and to be upgraded, "
                "checked: {hosts_checked} x"
                "upgraded: {hosts_to_be_upgraded}"
            ).format(
                hosts_checked=checked,
                hosts_to_be_upgraded=hosts_to_be_upgraded
            )

            assert hosts_to_be_upgraded == checked, err_msg
        else:
            err_msg = (
                "A host was checked: {hosts_checked}"
            ).format(
                hosts_checked=checked
            )

            assert not checked, err_msg

            update_available = [
                host for host in self._update_available
                if host in hosts_to_be_upgraded
            ]

        hosts_upgraded, hosts_left, hosts_failed = self._check_upgrade()

        logger.info('Hosts: %s with available update', update_available)
        logger.info('Hosts: %s were upgraded', hosts_upgraded)
        logger.info('Hosts: %s left untouched', hosts_left)
        logger.info('Hosts: %s failed', hosts_failed)

        # none host installation should fail
        # in case of failure, ansible should fail

        err_msg = (
            "Failed installation of hosts: {hosts_failed}"
        ).format(
            hosts_failed=hosts_failed
        )

        assert not hosts_failed, err_msg

        # host with available update should be upgraded

        err_msg = (
            "Different hosts, available update: {hosts_with_update} x"
            "upgraded: {hosts_upgraded}"
        ).format(
            hosts_with_update=update_available,
            hosts_upgraded=hosts_upgraded
        )

        assert hosts_upgraded == update_available, err_msg

        err_msg = (
            "Only specified hosts should be upgraded, "
            "hosts should be left: {hosts_to_be_left} x"
            "upgraded hosts: {hosts_to_be_left}"
        ).format(
            hosts_to_be_left=hosts_to_be_left,
            hosts_upgraded=hosts_upgraded
        )

        # testing empty intersection of two lists
        assert not set(hosts_to_be_left) & set(hosts_upgraded), err_msg
