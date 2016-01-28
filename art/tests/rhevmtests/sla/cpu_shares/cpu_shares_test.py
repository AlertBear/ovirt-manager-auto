"""
CPU SHARE TEST
test cpu share low, medium, high and custom and their combinations
"""
from art.unittest_lib import SlaTest as TestCase
from art.core_api import apis_utils
from art.core_api import apis_exceptions
from art.test_handler.tools import polarion  # pylint: disable=E0611
from nose.plugins.attrib import attr
from rhevmtests.sla import config
from rhevmtests import helpers
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.test_handler.exceptions as errors
import shlex
logger = config.logging.getLogger(__name__)


@attr(tier=1)
class BaseCpuShares(TestCase):
    """
    Base class for CPU shares
    The parameters: cpu_share_status and vm_list,
    have to be defined in the child class as a class member.
    """

    @classmethod
    def load_vm_cpu(cls, vm_list):
        """
        Load cpu on all VMs in the list
        :param vm_list: list of vm names
        :type vm_list: list
        """
        for vm_name in vm_list:
            ll_vms.wait_for_vm_states(vm_name)
            vm_resource = helpers.get_host_resource(
                hl_vms.get_vm_ip(vm_name), config.VMS_LINUX_PW
            )
            logger.info("Run cpu load on VM %s", vm_name)
            rc, out, err = vm_resource.run_command(
                ["dd", "if=/dev/zero", "of=/dev/null", "&"]
            )
            if rc:
                return False

    @classmethod
    def get_vms_cpu_consumption_on_host(cls, vm_list):
        """
        Get a list of VMs and return a dict with the VMs names as
        keys and the their cpu consumption on host as values
        :param vm_list: list of vm_names
        :type vm_list: list of string
        :return: dictionary with vm name and vm cpu consumption number
        :rtype: dict
        """
        current_dict = {}
        for vm_name in vm_list:
            vm_pid = config.VDS_HOSTS[0].get_vm_process_pid(vm_name)
            command = "top -b -n 1 -c -p %s | awk FNR==8" % vm_pid
            rc, out, _ = config.VDS_HOSTS[0].run_command(
                shlex.split(command)
            )
            if rc:
                return False
            current_dict[vm_name] = int(float(out.split()[8]))
        logger.info(
            "Current dict of VM's names and their cpu consumption :%s",
            current_dict
        )
        return current_dict

    @classmethod
    def check_ratio(cls, current_dict, expected_dict):
        """
        Check if the current_dict match the expected_ratio_dict
        (with deviation of 5%)
        :param current_dict:dict with vm names as keys and there current CPU
        consumption an the host as values
        :type current_dict: dict
        :param expected_dict:dict with vm names as keys and there
        expected CPU consumption aon the host as value
        :type expected_dict: dict
        :return: True if current_dict match the expected_ratio_dict
         (with deviation of 5%)
        :rtype: bool
        """
        for key, value in current_dict.iteritems():
            target = expected_dict[key]
            if not (target - 5 <= value <= target + 5):
                logger.warning(
                    "current CPU usage of %s should be around %s", key, target
                )
                return False
        return True

    @classmethod
    def check_cpu_share(cls):
        """
        Run the test -
        Get the vms CPU consumption and check if that is the expected ratio
        :raise APITimeout
        :return: true if the vms CPU consumption is in the expected ratio,
        False otherwise
        :rtype: bool
        """
        sampler = apis_utils.TimeoutingSampler(
            300, 20, cls.get_vms_cpu_consumption_on_host,
            cls.vm_list
        )
        try:
            for sample in sampler:
                if cls.check_ratio(sample, cls.expected_dict):
                    return True
        except apis_exceptions.APITimeout:
            logger.error("Timeout when waiting for CPU shares expected ratio")
        return False

    @classmethod
    def setup_class(cls):
        """
        Update the Vms CPU share, Start the Vms and run CPU load.
        """
        for vm_name, cpu_share in zip(
            cls.vm_list, cls.cpu_share_status
        ):
            logger.info("Update VM %s CPU shares to %s", vm_name, cpu_share)
            if not ll_vms.updateVm(True, vm_name, cpu_shares=cpu_share):
                raise errors.VMException(
                    "Failed to update VM %s CPU share to %d" %
                    (vm_name, cpu_share)
                )
        logger.info("Start vms: %s", cls.vm_list)
        if not ll_vms.startVms(cls.vm_list):
            raise errors.VMException("Failed to start VMs")
        cls.load_vm_cpu(cls.vm_list)

    @classmethod
    def teardown_class(cls):
        """
        Stop Vms in the list
        """
        ll_vms.stop_vms_safely(cls.vm_list)


class TestLowShare(BaseCpuShares):
    """
    Check that two vms that have the same low CPU share
    are competing evenly on the same core
    """
    __test__ = True
    cpu_share_status = [config.CPU_SHARE_LOW, config.CPU_SHARE_LOW]
    vm_list = config.VM_NAME[:2]
    expected_dict = dict((vm, 50) for vm in vm_list)

    @polarion("RHEVM3-4980")
    def test_low_share(self):
        """
        Test low share CPU
        """
        self.assertTrue(
            self.check_cpu_share(), "The vms aren't competing evenly on core"
        )


class TestMediumShare(BaseCpuShares):
    """
    Check that two vms that have the same medium CPU share
    are competing evenly on the same core
    """
    __test__ = True
    cpu_share_status = [config.CPU_SHARE_MEDIUM, config.CPU_SHARE_MEDIUM]
    vm_list = config.VM_NAME[:2]
    expected_dict = dict((vm, 50) for vm in vm_list)

    @polarion("RHEVM3-4981")
    def test_medium_share(self):
        """
        Test medium share CPU
        """
        self.assertTrue(
            self.check_cpu_share(), "The vms aren't competing evenly on core"
        )


class TestHighShare(BaseCpuShares):
    """
    Check that two vms that have the same high CPU share
    are competing evenly on the same core
    """
    __test__ = True
    cpu_share_status = [config.CPU_SHARE_HIGH, config.CPU_SHARE_HIGH]
    vm_list = config.VM_NAME[:2]
    expected_dict = dict((vm, 50) for vm in vm_list)

    @polarion("RHEVM3-4982")
    def test_high_share(self):
        """
        Test high share CPU
        """
        self.assertTrue(
            self.check_cpu_share(), "The vms aren't competing evenly on core"
        )


class TestCustomShare(BaseCpuShares):
    """
    Check that two vms that have the same custom CPU share
    are competing evenly on the same core
    """
    __test__ = True
    cpu_share_status = [300, 300]
    vm_list = config.VM_NAME[:2]
    expected_dict = dict((vm, 50) for vm in vm_list)

    @polarion("RHEVM3-4983")
    def test_custom_share(self):
        """
        Test custom share CPU
        """
        self.assertTrue(
            self.check_cpu_share(), "The vms aren't competing evenly on core"
        )


class TestPredefinedValues(BaseCpuShares):
    """
    Check that 4 vms that have the different CPU share values
    are taking a different percent of core
    """
    __test__ = True
    cpu_share_status = [
        config.CPU_SHARE_LOW, config.CPU_SHARE_LOW,
        config.CPU_SHARE_MEDIUM, config.CPU_SHARE_HIGH
    ]
    vm_list = config.VM_NAME[:4]
    expected_dict = dict(zip(vm_list, (13, 13, 25, 50)))

    @polarion("RHEVM3-4984")
    def test_predefined_values(self):
        """
        Test CPU share with Predefined Values
        """
        self.assertTrue(
            self.check_cpu_share(),
            "The vms aren't taking the expected CPU percents from the core"
        )


class TestCustomValuesOfShare(BaseCpuShares):
    """
    Check that 4 vms that have the different custom CPU share values
    are taking a different percent of core
    """
    __test__ = True
    cpu_share_status = [100, 100, 200, 400]
    vm_list = config.VM_NAME[:4]
    expected_dict = dict(zip(vm_list, (13, 13, 25, 50)))

    @polarion("RHEVM3-4985")
    def test_custom_values_of_share(self):
        """
        Test custom values of share
        """
        self.assertTrue(
            self.check_cpu_share(),
            "The vms aren't taking the expected CPU percents from the core"
        )
