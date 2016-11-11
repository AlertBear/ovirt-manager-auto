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
from art.unittest_lib import StorageTest as TestCase
from art.unittest_lib import attr

from art.rhevm_api.tests_lib.low_level import hosts

from art.test_handler.tools import polarion

from rhevmtests.storage import config
from utilities.machine import LINUX, Machine

logger = logging.getLogger(__name__)

SUPERVDSM_LOG = "/var/log/vdsm/supervdsm.log"
VDSM_LOG = "/var/log/vdsm/vdsm.log"
SVDSM_LOCK = "/var/run/vdsm/svdsm.sock"
SUPERVDSMD = "supervdsmd"
VDSMD = "vdsmd"
SERVICE_CMD = "/sbin/service"

HW_INFO_COMMAND = ["vdsClient", "-s", "0", "getVdsHardwareInfo"]
SLEEP_SERVICE = 10

# Error messages
ERROR_EXEC_SERVICE_ACTION = "Failed to execute %s on service %s"
ERROR_SERVICE_NOT_UP = "Service %s is not running"
ERROR_SERVICE_UP = "Service %s is running"
ERROR_HW_OUTPUT = "Cannot get HW Info, output:\n%s"
FILE_DOES_NOT_EXIST = "File %s does not exist"


def getSupervdsmPid(machine):
    return machine.getPidByName("supervdsmServer")[1][0]["ProcessId"]


def getVdsmPid(machine):
    return machine.getPidByName("vdsm")[1][0]["ProcessId"]


def isVdsmRunning(machine):
    """
    Make sure is running checking the process and the System Init status
    """
    try:
        getVdsmPid(machine)
        return machine.isServiceRunning(VDSMD)
    except IndexError:
        return False


def isSupervdsmRunning(machine):
    """
    Make sure is running checking the process and the System Init status
    """
    try:
        getSupervdsmPid(machine)
        return machine.isServiceRunning(SUPERVDSMD)
    except IndexError:
        return False


@pytest.fixture()
def check_host_up(request):
    """
    Check the host is in status UP and get the host ip
    """
    self = request.node.cls

    # Wait a few seconds for host to be up
    hosts.waitForHostsStates(
        True, config.HOSTS[0], states=config.HOST_UP, timeout=30
    )
    # If there's a problem with vdsm the host switches between
    # non_operational - non_responsive status
    if not hosts.isHostUp(True, config.HOSTS[0]):
        logger.error(
            "Host %s was down unexpectedly. Starting it up" %
            config.HOSTS[0]
        )
        assert hosts.activate_host(
            True, config.HOSTS[0]
        ), "Host %s was not activated" % config.HOSTS[0]
    host_ip = hosts.getHostIP(config.HOSTS[0])
    self.machine = Machine(
        host_ip, config.HOSTS_USER,
        config.HOSTS_PW).util(LINUX)
    self.machine.enableServiceSupport()


@pytest.fixture()
def restore_supervdsm_files(request):
    """
    Make sure to restore supervdsm log file
    """
    self = request.node.cls

    def finalizer():
        self.machine.stopService(SUPERVDSMD)
        self.machine.runCmd(["touch", SUPERVDSM_LOG])
        self.machine.runCmd(["chmod", "0644", SUPERVDSM_LOG])
        self.machine.runCmd(["chown", "vdsm:kvm", SUPERVDSM_LOG])
        self.machine.startService(SUPERVDSMD)
        # for supporting rhel versions that stopping supervdsm stopps vdsm
        # (rhel7 and up)
        self.machine.startService(VDSMD)
        # After start vdsm wait for host to be up
        hosts.waitForHostsStates(True, config.HOSTS[0], states=config.HOST_UP,
                                 timeout=60)

        # after restarting supervdsm, run vdsm command that requires
        # supervdsm in order to trigger reconnection between supervdsm and vdsm
        self.machine.runCmd(HW_INFO_COMMAND)
    request.addfinalizer(finalizer)


@pytest.mark.usefixtures(
    check_host_up.__name__,
)
@attr(tier=2)
class TestCase6269(TestCase):
    """
    supervdsm test case, sanity
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_SuperVdsm
    """
    __test__ = True
    storages = config.NOT_APPLICABLE

    @polarion("RHEVM3-6269")
    def test_supervdsm_sanity(self):
        """
        Test basic functionality is running after host is installed
        """
        logger.info("Make sure services are running after host is added "
                    "to rhevm in the setup Class")
        assert isVdsmRunning(self.machine), "VDSM is not running"
        assert isSupervdsmRunning(self.machine), "VDSM is not running"

        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        assert success, ERROR_HW_OUTPUT % output

        logger.info("Make sure log files exists")
        assert self.machine.isFileExists(SUPERVDSM_LOG), (
            FILE_DOES_NOT_EXIST % SUPERVDSM_LOG
        )
        assert self.machine.isFileExists(VDSM_LOG), (
            FILE_DOES_NOT_EXIST % VDSM_LOG
        )


@pytest.mark.usefixtures(
    check_host_up.__name__,
)
@attr(tier=4)
class TestCase6270(TestCase):
    """
    supervdsm test case, command options
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_SuperVdsm
    """
    __test__ = True

    @polarion("RHEVM3-6270")
    def test_command_options_test(self):
        """
        Test command options
        """
        def runSystemInitSupervdsmd(cmd):
            command = [SERVICE_CMD, SUPERVDSMD, cmd]
            try:
                success, output = self.machine.runCmd(command)
                if not success:
                    logger.error("Executed %s, output: %s" % (command, output))
                    return False
                return True
            except IndexError:
                self.fail("Couldn't find supervdsm PID")

        logger.info("Stopping supervdsm")
        assert self.machine.stopService(
            SUPERVDSMD
        ), ERROR_EXEC_SERVICE_ACTION % ("stop", "supervdsm")
        time.sleep(SLEEP_SERVICE)
        logger.info("Starting supervdsm")
        assert self.machine.startService(
            SUPERVDSMD
        ), ERROR_EXEC_SERVICE_ACTION % ("start", "supervdsm")
        time.sleep(SLEEP_SERVICE)
        # for supporting rhel versions that stopping supervdsm stopps vdsm
        # (rhel7 and up)
        logger.info("Starting vdsmd")
        self.machine.startService(VDSMD)
        time.sleep(SLEEP_SERVICE)
        restart_commands = ['restart', 'condrestart', 'force-reload',
                            'try-restart']
        for command in restart_commands:
            logger.info("Restarting supervdsm")
            assert runSystemInitSupervdsmd(
                command
            ), ERROR_EXEC_SERVICE_ACTION % (command, "supervdsm")


@pytest.mark.usefixtures(
    check_host_up.__name__,
)
@attr(tier=4)
class TestCase6271(TestCase):
    """
    supervdsm test case, communication between supervdsm and vdsm
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_SuperVdsm
    """
    __test__ = True

    @polarion("RHEVM3-6271")
    def test_communication(self):
        """
        Test that both services work when one is stopped
        """
        logger.info("Stopping vdsmd")
        assert self.machine.stopService(VDSMD), "vdsm didn't stop"
        time.sleep(SLEEP_SERVICE)
        assert isSupervdsmRunning(
            self.machine
        ), ERROR_SERVICE_NOT_UP % "supervdsm"
        logger.info("Starting supervdsmd")
        self.machine.startService(SUPERVDSMD)
        logger.info("Starting vdsmd")
        assert self.machine.startService(VDSMD), "vdsm didn't start"
        # After restart vdsm wait for host to be up
        assert hosts.waitForHostsStates(
            True, config.HOSTS[0], states=config.HOST_UP, timeout=60
        ), "Host never activated after vdsm restarted."
        time.sleep(SLEEP_SERVICE)
        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        assert success, ERROR_HW_OUTPUT % output

        logger.info("Stopping supervdsmd")
        assert self.machine.stopService(SUPERVDSMD), "Supervdsm didn't stop"
        time.sleep(SLEEP_SERVICE)
        logger.info("Starting supervdsmd")
        assert self.machine.startService(SUPERVDSMD), "Supervdsm didn't start"
        # for supporting rhel versions that stopping supervdsm stopps vdsm
        # (rhel7 and up)
        logger.info("Starting vdsmd")
        self.machine.startService(VDSMD)
        # After restart vdsm wait for host to be up
        assert hosts.waitForHostsStates(
            True, config.HOSTS[0], states=config.HOST_UP, timeout=60
        ), "Host never activated after vdsm restarted."
        time.sleep(SLEEP_SERVICE)
        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        assert success, ERROR_HW_OUTPUT % output


@pytest.mark.usefixtures(
    check_host_up.__name__,
)
@attr(tier=4)
class TestCase6272(TestCase):
    """
    supervdsm test case, supervdsm stress test
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_SuperVdsm
    """
    __test__ = True

    @polarion("RHEVM3-6272")
    def test_supervdsm_stress_test(self):
        """
        supervdsm stress tests
        """
        N = 1000
        # is much faster run it with one ssh session
        cmd = (
            "for i in `seq 0 %(iter)d`; do vdsClient -s 0 getVdsHardwareInfo"
            " >& /dev/null; if [ $? -ne 0 ]; then exit -1; fi; done;" %
            {'iter': N}
        )

        logger.info("Executing vdsClient get HW Info for %d times" % N)
        # ~ 0.3 sec per execution
        success, output = self.machine.runCmd(cmd.split(' '), timeout=N * 0.3)
        assert success, (
            "Couldn't execute %(iter)d times the command. %(output)s:" %
            {
                "iter": N,
                "output": output,
            }
        )


@pytest.mark.usefixtures(
    check_host_up.__name__,
    restore_supervdsm_files.__name__,
)
@attr(tier=4)
class TestCase6273(TestCase):
    """
    deleting supervdsm log and changing log file permissions
    https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
    Storage/3_3_Storage_SuperVdsm
    """
    __test__ = True

    @polarion("RHEVM3-6273")
    def test_change_supervdsm_log(self):
        """
        change permissions and delete supervdsm log
        """
        logger.info("Removing supervdsm log file to test recovery")
        assert self.machine.removeFile(
            SUPERVDSM_LOG
        ), "Error removing %s file" % SUPERVDSM_LOG
        assert isSupervdsmRunning(
            self.machine
        ), ERROR_SERVICE_NOT_UP % "supervdsm"
        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        assert success, (
            "Supervdsm didn't recover from removing log file, out=%s" % output
        )
        assert self.machine.isFileExists(
            SUPERVDSM_LOG
        ), "%s should be created" % SUPERVDSM_LOG

        logger.info("Changing supervdsm log file permissions to test recovery")
        success, output = self.machine.runCmd(["chmod", "0000", SUPERVDSM_LOG])
        assert success, "Error changing %s permissions %s" % (
            SUPERVDSM_LOG, output
        )
        assert isSupervdsmRunning(
            self.machine
        ), ERROR_SERVICE_NOT_UP % "supervdsm"
        success, output = self.machine.runCmd(HW_INFO_COMMAND)
        assert success, (
            "Supervdsm didn't recover from changing log file's permissions"
        )
