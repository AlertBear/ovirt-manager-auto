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

    def execute_on_remote(self, executor, command_list, name):
        with executor.session() as ss:
            for cmd, erc in command_list:
                ss.logger.info('Executing on:%s cmd: %s', name, cmd)
                rc, _, err = ss.run_cmd(cmd)
                if not erc(rc):
                    raise Exception(
                        'Command: %s, exited unexpectly %s ERR: %s' % (
                            cmd, rc, err,
                        )
                    )

    def update_repos_and_vdsm(self, host_ip):
        executor = resources.VDS(host_ip, self._passwd).executor()
        command_list = (
            (['rpm', '-qa', '\'(rhev|ovirt)-release-*\'', '|',
                'xargs', 'rpm', '-e'], lambda x: True),
            (['rm', '-f', '/etc/yum.repos.d/rhev*.repo'], lambda x: True),
            (['puppet', 'agent', '--enable'], lambda x: x == 0),
            (['puppet', 'agent', '-t'], lambda x: x in (0, 2)),
            (['puppet', 'agent', '--disable'], lambda x: x == 0),
            (['yum', 'update', '-y'], lambda x: True),
        )
        self.execute_on_remote(executor, command_list, host_ip)

    def update_engine(self, executor):
        command_list = (
            (['engine-setup', '--config-append=' + config.ANSWER_FILE],
                lambda x: x == 0),
        )
        self.execute_on_remote(executor, command_list, 'engine')

    def update_engine_repositories(self, executor):
        command_list = (
            (['test', '-f', config.ANSWER_FILE], lambda x: x == 0),
            (['rpm', '-qa', '\'(rhev|ovirt)-release-*\'', '|',
                'xargs', 'rpm', '-e'], lambda x: True),
            (['rm', '-f', '/etc/yum.repos.d/rhev*.repo'], lambda x: True),
            (['puppet', 'agent', '--enable'], lambda x: x == 0),
            (['puppet', 'agent', '-t'], lambda x: x in (0, 2)),
            (['puppet', 'agent', '--disable'], lambda x: x == 0),
        )
        self.execute_on_remote(executor, command_list, 'engine')

    def update_engine_packages(self, executor):
        packages = [
            'ovirt-engine-setup',
            'ovirt-engine-sdk-java',
            'java-ovirt-engine-sdk4',
            'python-ovirt-engine-sdk4',
            'rubygem-ovirt-engine-sdk4',
            'ovirt-log-collector',
            'ovirt-engine-extension-aaa-ldap',
            'ovirt-engine-extension-aaa-misc',
            'ovirt-engine-extension-aaa-ldap-setup',
            'ovirt-engine-dwh-setup',
        ]
        command_list = tuple(
            (['yum', 'update', '-y', p], lambda x: x == 0) for p in packages
        )
        self.execute_on_remote(executor, command_list, 'engine')

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

        # update rhel hosts if any
        for host_ip in self.rhel_hosts_ip:
            self.update_repos_and_vdsm(host_ip)

        # update engine
        executor = config.ENGINE_HOST.executor()
        self.update_engine_repositories(executor)
        self.update_engine_packages(executor)
        self.update_engine(executor)

        # wait for engine to start
        self.wait_for_engine()

        # activate all hosts
        for host_name in host_name_list:
            hl_hosts.activate_host_if_not_up(host_name)
