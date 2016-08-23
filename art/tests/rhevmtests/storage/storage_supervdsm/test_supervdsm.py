"""
Test supervdsm
Make sure to run this test with "remove_packages"  plugin to test the
installation of supervdsm when adding the host to the Data Center
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Storage/3_3_Storage_SuperVdsm
"""
import logging
import time
import pytest
from art.unittest_lib import (
    tier2,
    tier4,
    storages,
)
import config
from art.unittest_lib import StorageTest as TestCase
from rhevmtests.storage.fixtures import (
    init_host_resource, init_host_or_engine_executor
)
from art.rhevm_api.tests_lib.low_level import (
    hosts as ll_hosts
)
from fixtures import (
    check_host_up,
    restore_supervdsm_files
)
from art.test_handler.tools import polarion

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures(
    check_host_up.__name__,
    init_host_resource.__name__,
    init_host_or_engine_executor.__name__
)
class BaseTestCase(TestCase):
    """
    Base test case with common setup and teardown
    """


@storages((config.NOT_APPLICABLE,))
class TestCase6269(BaseTestCase):
    """
    supervdsm test case, sanity
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_SuperVdsm
    """
    __test__ = True

    @polarion("RHEVM3-6269")
    @tier2
    @storages(('iscsi',))
    def test_supervdsm_sanity(self):
        """
        Test basic functionality is running after host is installed
        """
        logger.info(
            "Make sure services are running after host is added to rhevm in "
            "the setup Class"
        )
        assert self.host_resource.service(name=config.VDSMD).status(), (
            "VDSM is not running"
        )
        assert self.host_resource.service(
            name=config.SUPERVDSMD
        ).status(), "superVDSM is not running"

        rc, out, err = self.executor.run_cmd(config.HW_INFO_COMMAND)
        assert not rc, config.ERROR_HW_OUTPUT % err

        logger.info("Make sure log files exists")
        assert self.host_resource.fs.exists(path=config.SUPERVDSM_LOG), (
            config.FILE_DOES_NOT_EXIST % config.SUPERVDSM_LOG
        )
        assert self.host_resource.fs.exists(path=config.VDSM_LOG), (
            config.FILE_DOES_NOT_EXIST % config.VDSM_LOG
        )


class TestCase6270(BaseTestCase):
    """
    supervdsm test case, command options
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_SuperVdsm
    """
    __test__ = True

    @polarion("RHEVM3-6270")
    @tier4
    def test_command_options_test(self):
        """
        Test command options
        """
        def run_system_init_supervdsmd(cmd):
            command = [config.SERVICE_CMD, cmd, config.SUPERVDSMD]
            try:
                rc, out, err = self.executor.run_cmd(command)
                if rc:
                    logger.error(
                        "Executed %s, output: %s, error: %s" % (
                            command, out, err
                        )
                    )
                    return False
                return True
            except IndexError:
                self.fail("Couldn't find supervdsm PID")

        logger.info("Stopping supervdsm")
        assert self.host_resource.service(config.SUPERVDSMD).stop(), (
            config.ERROR_EXEC_SERVICE_ACTION % ("stop", "supervdsm")
        )
        time.sleep(config.SLEEP_SERVICE)
        logger.info("Starting supervdsm")
        assert self.host_resource.service(config.SUPERVDSMD).start(), (
            config.ERROR_EXEC_SERVICE_ACTION % ("start", "supervdsm")
        )
        time.sleep(config.SLEEP_SERVICE)
        # for supporting rhel versions that stopping supervdsm stopps vdsm
        # (rhel7 and up)
        logger.info("Starting vdsmd")
        self.host_resource.service(config.VDSMD).start()
        time.sleep(config.SLEEP_SERVICE)
        restart_commands = [
            'restart', 'condrestart', 'force-reload', 'try-restart'
        ]
        for command in restart_commands:
            logger.info("Restarting supervdsm")
            assert run_system_init_supervdsmd(
                command
            ), config.ERROR_EXEC_SERVICE_ACTION % (command, "supervdsmd")


class TestCase6271(BaseTestCase):
    """
    supervdsm test case, communication between supervdsm and vdsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_SuperVdsm
    """
    __test__ = True

    @polarion("RHEVM3-6271")
    @tier4
    def test_communication(self):
        """
        Test that both services work when one is stopped
        """
        logger.info("Stopping vdsmd")
        assert self.host_resource.service(config.VDSMD).stop(), (
            "vdsm didn't stop"
        )
        time.sleep(config.SLEEP_SERVICE)
        assert self.host_resource.service(config.SUPERVDSMD).status(),  (
            config.ERROR_SERVICE_NOT_UP % (
                config.SUPERVDSMD
            )
        )
        logger.info("Starting supervdsmd")
        self.host_resource.service(config.SUPERVDSMD).start()
        logger.info("Starting vdsmd")
        assert self.host_resource.service(config.VDSMD).start(), (
            "vdsm didn't start"
        )
        # After restart vdsm wait for host to be up
        assert ll_hosts.wait_for_hosts_states(
            True, config.HOSTS[0], states=config.HOST_UP, timeout=60
        ), "Host never activated after vdsm restarted."
        time.sleep(config.SLEEP_SERVICE)
        rc, out, err = self.executor.run_cmd(config.HW_INFO_COMMAND)
        assert not rc, config.ERROR_HW_OUTPUT % err

        logger.info("Stopping supervdsmd")
        assert self.host_resource.service(config.SUPERVDSMD).stop(), (
            "Supervdsm didn't stop"
        )
        time.sleep(config.SLEEP_SERVICE)
        logger.info("Starting supervdsmd")
        assert self.host_resource.service(config.SUPERVDSMD).start(), (
            "Supervdsm didn't start"
        )
        # for supporting rhel versions that stopping supervdsm stopps vdsm
        # (rhel7 and up)
        logger.info("Starting vdsmd")
        self.host_resource.service(config.VDSMD).start()
        # After restart vdsm wait for host to be up
        assert ll_hosts.wait_for_hosts_states(
            True, config.HOSTS[0], states=config.HOST_UP, timeout=60
        ), "Host never activated after vdsm restarted."
        time.sleep(config.SLEEP_SERVICE)
        rc, out, err = self.executor.run_cmd(config.HW_INFO_COMMAND)
        assert not rc, config.ERROR_HW_OUTPUT % err


class TestCase6272(BaseTestCase):
    """
    supervdsm test case, supervdsm stress test
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_SuperVdsm
    """
    __test__ = True

    @polarion("RHEVM3-6272")
    @tier4
    def test_supervdsm_stress_test(self):
        """
        supervdsm stress tests
        """
        N = 100
        # is much faster run it with one ssh session
        cmd = (
            "for i in `seq 0 %(iter)d`; do vdsm-client Host getHardwareInfo"
            " >& /dev/null; if [ $? -ne 0 ]; then exit -1; fi; done;" %
            {'iter': N}
        )

        logger.info("Executing vdsClient get HW Info for %d times" % N)
        # ~ 2 sec per execution for vdsm-client , vds-client was 0.3 sec
        rc, out, err = self.executor.run_cmd(cmd.split(' '), io_timeout=N * 10)
        assert not rc, (
            "Couldn't execute %(iter)d times the command. %(output)s:" %
            {
                "iter": N,
                "output": out,
            }
        )


@pytest.mark.usefixtures(
    restore_supervdsm_files.__name__,
)
class TestCase6273(BaseTestCase):
    """
    deleting supervdsm log and changing log file permissions
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_SuperVdsm
    """
    __test__ = True

    @polarion("RHEVM3-6273")
    @tier4
    def test_change_supervdsm_log(self):
        """
        change permissions and delete supervdsm log
        """
        logger.info("Removing supervdsm log file to test recovery")
        assert self.host_resource.fs.remove(
            config.SUPERVDSM_LOG
        ), "Error removing %s file" % config.SUPERVDSM_LOG
        assert self.host_resource.service(config.SUPERVDSMD).status(), (
            config.ERROR_SERVICE_NOT_UP % config.SUPERVDSMD
        )
        rc, out, err = self.executor.run_cmd(config.HW_INFO_COMMAND)
        assert not rc, (
            "Supervdsm didn't recover from removing log file, out=%s" % out
        )
        assert self.host_resource.fs.exists(
            config.SUPERVDSM_LOG
        ), "%s should be created" % config.SUPERVDSM_LOG

        logger.info("Changing supervdsm log file permissions to test recovery")
        rc, out, err = self.executor.run_cmd(
            ["chmod", "0000", config.SUPERVDSM_LOG]
        )
        assert not rc, "Error changing %s permissions %s" % (
            config.SUPERVDSM_LOG, out
        )
        assert self.host_resource.service(config.SUPERVDSMD).status(), (
            config.ERROR_SERVICE_NOT_UP % config.SUPERVDSMD
        )
        rc, out, err = self.executor.run_cmd(config.HW_INFO_COMMAND)
        assert not rc, (
            "Supervdsm didn't recover from changing log file's permissions"
        )
