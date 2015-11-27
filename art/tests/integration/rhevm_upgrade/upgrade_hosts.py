'''
Sanity tests for upgrading hosts
'''
import logging
import os.path

from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api import resources
from art.rhevm_api.tests_lib.low_level import hosts, clusters, datacenters
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr
from art.unittest_lib import CoreSystemTest as TestCase

from rhevm_upgrade import config

logger = logging.getLogger(__name__)


@attr(tier=2)
class UpgradeHosts(TestCase):
    """ Perform the upgrade of hosts """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.engine_hosts = hosts.get_host_list()
        assert len(cls.engine_hosts) > 0, 'There are no hosts to be upgraded'

    def _add_repo_to_host(self, host, name, repo):
        with host.executor().session() as ss:
            with ss.open_file(
                '%s.repo' % os.path.join(config.YUM_DIR, name),
                'w'
            ) as repo_file:
                repo_file.write((
                    '[{repo_name}]\n'
                    'name={repo_name}\n'
                    'baseurl={baseurl}\n'
                    'enabled=1\n'
                    'gpgcheck=0\n'
                ).format(
                    repo_name=name,
                    baseurl=repo,
                ))

    def _check_for_upgrade(self, host):
        """
        FIXME: rewrite this method once there is support to forcibly check
               available upgrade of host
        """
        self.assertTrue(
            test_utils.set_engine_properties(
                config.ENGINE,
                ['HostPackagesUpdateTimeInHours=0.01'],
            ),
            'Failed to change HostPackagesUpdateTimeInHours config'
        )
        # Wait until upgrade is available to engine
        for available in TimeoutingSampler(
            timeout=120,
            sleep=10,
            func=hosts.is_upgrade_available,
            host_name=host.ip,
        ):
            if available:
                break

    def _upgrade(self, host):
        logger.info("Upgrading host '%s'", host.ip)
        self.assertTrue(
            hosts.upgrade_host(host.ip),
            "Upgrade of host '%s' failed" % host.ip
        )

    def _upgrade_rhel_host(self, host):
        logger.info("Adding new repos to host '%s' ", host.ip)
        for name, repo in config.UPGRADE_REPOS:
            self._add_repo_to_host(host, name, repo)

        self._check_for_upgrade(host)
        self._upgrade(host)

    @polarion('RHEVM3-14102')
    def test_upgrade_rhel_hosts(self):
        """ Perform upgrade of rhel hosts in setup """
        for host in [
            host for host in self.engine_hosts if host.get_type() == 'rhel'
        ]:
            self._upgrade_rhel_host(
                resources.VDS(host.get_name(), config.HOSTS_PW)
            )

    # This case have to be last, after hosts are upgraded
    def test_zz_upgrade_cluster_dc_version(self):
        """ Change cluster/dc compatibility version to current """
        self.assertTrue(
            clusters.updateCluster(
                True,
                config.CLUSTER_NAME,
                version=config.TO_VERSION,
            ),
            "Failed to upgrade compatibility version of cluster"
        )
        self.assertTrue(
            datacenters.updateDataCenter(
                True,
                config.DC_NAME,
                version=config.TO_VERSION
            ),
            "Failed to upgrade compatibility version of datacenter"
        )
