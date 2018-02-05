import copy
import json
import logging

from art.rhevm_api.tests_lib.low_level import events as ll_events
from art.rhevm_api.tests_lib.low_level import hosts as ll_hosts
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
        return self.extra_vars

    def get_var(self, var_name):
        return self.extra_vars.get(var_name, None)

    def run(self):
        """
        run a playbook with defined variables
        """

        logger.info('oVirt Ansible role vars: %s', self.extra_vars)

        logger.info('Running ansible playbook.')

        rc, out, err = run_ansible_playbook(
            '{ansible_path}/{tested_role}'.format(
                ansible_path=config.OVIRT_ANSIBLE_ROLES_PATH,
                tested_role=self.role
            ),
            "-e '{variables}'".format(
                variables=json.dumps(self.extra_vars)
            )
        )

        logger.info('Running ansible playbook\n Output:\n%s.', out)

        log_msg = 'Failed to exec ansible! RC: %s,\n ERR: %s\n' % (
            rc, err
        )

        assert rc == 0, log_msg


class Checker():
    """
    EventChecker is class mainly for investigating events.
    Some tasks can't be checked directly after playbook run
    (amount of memory, number of CPU). It must be done via events.
    """
    def __init__(self):
        logger.info('Getting information about update.')
        self._update_available = [
            host for host in config.ENGINE_HOSTS
            if ll_hosts.is_upgrade_available(host)
        ]

        logger.info('Get max event ID.')
        self.start_event_id = ll_events.get_max_event_id()

    def _check_for_update(self):
        """
        Function for checking which hosts perform check for upgrade
        Returns:
            {
                'checked': [list of hosts which were checked]
                'update_available': [list of hosts with available update]
            }
        """
        logger.info('Checking check for update.')

        checked = []
        update_available = []

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
                update_available.append(host)

        ret = {}
        ret['checked'] = checked
        ret['update_available'] = update_available

        return ret

    def _check_upgrade(self):
        """
        Function to get lists of hosts which were upgraded,
        failed and not upgraded
        Returns:
            {
                'upgraded_hosts': [list of upgraded hosts]
                'not_upgraded_hosts': [list of not upgraded hosts]
                'failed_hosts': [list of failed hosts]
            }
        """
        logger.info('Checking upgrade events.')

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
                win_start_event_id=self.start_event_id,
                query=config.CLUSTER_UPDATED_MSG.format(
                    cluster=config.ANSIBLE_ENGINE_CLUSTER_NAME
                ),
                expected_count=config.HOST_TO_MAINTENANCE_COUNT
            )

            assert not status, 'Cluster is still in maintenance state'

            logger.info('Hosts: %s were upgraded', upgraded_hosts)

        else:
            logger.info('None upgraded hosts')

        logger.info('Not updated hosts: %s', not_upgraded_hosts)

        ret = {}
        ret['upgraded'] = upgraded_hosts
        ret['not_upgraded'] = not_upgraded_hosts
        ret['failed'] = failed_hosts

        return ret

    def upgrade(self, ansible_runner):
        """
        Method for checking upgrade of hosts from events
        Args:
            ansible_runner: object with variables from ansible run
        """
        logger.info('Check upgrade from events started')

        hosts_to_be_upgraded = ansible_runner.get_var('host_names')
        if not hosts_to_be_upgraded:
            hosts_to_be_upgraded = config.ENGINE_HOSTS

        hosts_to_be_left = [
            host for host in config.ENGINE_HOSTS
            if host not in hosts_to_be_upgraded
        ]

        logger.info('Hosts: %s are marked for upgrade', hosts_to_be_upgraded)
        logger.info('Hosts: %s shouldn\'t be upgraded', hosts_to_be_left)

        check = self._check_for_update()

        if ansible_runner.get_var('check_upgrade'):
            err_msg = (
                'Different hosts checked for update and to be upgraded, '
                'with_update {hosts_with_update} + '
                'checked: {hosts_checked} x '
                'upgraded: {hosts_to_be_upgraded}'
            ).format(
                hosts_with_update=self._update_available,
                hosts_checked=check['checked'],
                hosts_to_be_upgraded=hosts_to_be_upgraded
            )

            condition = (
                set(hosts_to_be_upgraded) == (
                    set(check['checked'] + self._update_available)
                )
            )
            assert condition, err_msg

        else:
            err_msg = (
                'A host was checked: {hosts_checked}'
            ).format(
                hosts_checked=check['checked']
            )

            assert not check['checked'], err_msg

            check['update_available'] = [
                host for host in self._update_available
                if host in hosts_to_be_upgraded
            ]

        upgrade = self._check_upgrade()

        logger.info(
            'Hosts: %s with available update',
            check['update_available']
        )
        logger.info('Hosts: %s were upgraded', upgrade['upgraded'])
        logger.info('Hosts: %s left untouched', upgrade['not_upgraded'])
        logger.info('Hosts: %s failed', upgrade['failed'])

        # none host installation should fail
        # in case of failure, ansible should fail

        err_msg = (
            'Failed installation of hosts: {hosts_failed}'
        ).format(
            hosts_failed=upgrade['failed']
        )

        assert not upgrade['failed'], err_msg

        # host with available update should be upgraded

        err_msg = (
            'Different hosts, available update: {hosts_with_update} x'
            'upgraded: {hosts_upgraded}'
        ).format(
            hosts_with_update=check['update_available'],
            hosts_upgraded=upgrade['upgraded']
        )

        assert upgrade['upgraded'] == check['update_available'], err_msg

        err_msg = (
            'Only specified hosts should be upgraded, '
            'hosts should be left: {hosts_to_be_left} x'
            'upgraded hosts: {hosts_upgraded}'
        ).format(
            hosts_to_be_left=hosts_to_be_left,
            hosts_upgraded=upgrade['upgraded']
        )

        cond = set(hosts_to_be_left).intersection(set(upgrade['upgraded']))
        assert not cond, err_msg
