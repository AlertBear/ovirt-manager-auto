import logging
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.high_level.hosts as hl_hosts
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import golden_env.config as config
from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api import resources
from art.unittest_lib import BaseTestCase as TestCase
logger = logging.getLogger(__name__)


class TestUpgrade(TestCase):
    __test__ = True

    def get_rhel_hosts_ip(self, host_list):
        hosts = []
        for host in host_list:
            host_type = host.get_type()
            host_ip = host.get_address()
            logger.info('Host %s is type: %s', host_ip, host_type)
            if host_type == 'rhel':
                hosts.append(host_ip)
        return hosts

    def stop_all_vms(self):
        all_vms = ll_vms.get_all_vms()
        vms_list = [vm.get_name() for vm in all_vms]
        return ll_vms.stop_vms_safely(vms_list)

    def update_repos_and_vdsm(self, host_ip):
        command_list = (
            (['puppet', 'agent', '--enable'], lambda x: x == 0),
            (['puppet', 'agent', '-t'], lambda x: True),
            (['yum', 'update', '-y'], lambda x: True),
        )
        host = resources.VDS(host_ip, self._passwd)
        with host.executor().session() as ss:
            for cmd, erc in command_list:
                ss.logger.info('Executing on host:%s cmd: %s', host_ip, cmd)
                rc, _, err = ss.run_cmd(cmd)
                if not erc(rc):
                    raise Exception(
                        'Command: %s, exited unexpectly %s ERR: %s' % (
                            cmd, rc, err,
                        )
                    )

    def update_engine(self):
        command_list = (
            (['test', '-f', config.ANSWER_FILE], lambda x: x == 0),
            (['puppet', 'agent', '--enable'], lambda x: x == 0),
            (['rpm', '-qa', '\'(rhev|ovirt)-release-*\'', '|',
                'xargs', 'rpm', '-e'], lambda x: True),
            (['puppet', 'agent', '-t'], lambda x: True),
            (['yum', 'update', 'rhevm-setup', '-y'], lambda x: x == 0),
            (['engine-setup', '--config-append=' + config.ANSWER_FILE],
                lambda x: x == 0),
            (['yum', 'update', '-y', 'java_sdk',
                'ovirt-engine-extension-aaa-ldap',
                'ovirt-engine-extension-aaa-misc',
                'ovirt-engine-extension-aaa-ldap-setup'],
                lambda x: True),
            (['yum', 'update', '-y', 'rhevm-sdk-java',
                'rhevm-log-collector'], lambda x: True),
            (['yum', 'update', '-y', 'ovirt-sdk-java',
                'ovirt-log-collector'], lambda x: True),
        )
        with config.ENGINE_HOST.executor().session() as ss:
            for cmd, erc in command_list:
                ss.logger.info('Executing on engine, cmd: %s', cmd)
                rc, _, err = ss.run_cmd(cmd)
                if not erc(rc):
                    raise Exception(
                        'Command: %s, exited unexpectly %s ERR: %s' % (
                            cmd, rc, err,
                        )
                    )

    def wait_for_engine(self):
        engine = resources.Engine(
            config.ENGINE_HOST,
            resources.ADUser(
                'admin',
                config.VDC_PASSWORD,
                resources.Domain('internal'),
            )
        )
        for status in TimeoutingSampler(
            300, 20, lambda: engine.health_page_status
        ):
            if status:
                break

    def test_upgrade(self):
        assert config.ANSWER_FILE, 'Answer file for Otopi is not specified.'
        host_list = ll_hosts.get_host_list()
        host_name_list = [
            host.get_name() for host in host_list
        ]
        self._passwd = config.PASSWORDS[0]

        # stop all vms
        assert self.stop_all_vms()

        # put all hosts to maintenance
        hl_hosts.deactivate_hosts_if_up(host_name_list)

        # Get not RHEV-H
        self.rhel_hosts_ip = self.get_rhel_hosts_ip(host_list)
        assert self.rhel_hosts_ip, 'No hosts found'

        # update hosts
        for host_ip in self.rhel_hosts_ip:
            self.update_repos_and_vdsm(host_ip)

        # update engine
        self.update_engine()

        # wait for engine to start
        self.wait_for_engine()

        # activate all hosts
        for host_name in host_name_list:
            hl_hosts.activate_host_if_not_up(host_name)
