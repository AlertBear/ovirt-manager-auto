"""
Testing vdsm hooks and vm hooks: before_vm_start, after_vm_pause,
before_vdsm_start, after_vdsm_stop
"""

import logging

import pytest
from os import path

from art.rhevm_api.tests_lib.low_level import hooks, vms, hosts
from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.test_handler.tools import polarion
from art.unittest_lib import CoreSystemTest as TestCase, testflow
from art.unittest_lib import attr

from hooks import config

HOOK_VALUE = "1234"
CUSTOM_HOOK = "auto_custom_hook={0}".format(HOOK_VALUE)
REMOVE_HOOKS = "rm -f /var/tmp/*.hook"
HOOK_DIR = "/usr/libexec/vdsm/hooks"
TMP = "/var/tmp"

__test__ = True

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    testflow.setup("Setting up module %s.", __name__)

    testflow.step("Creating a VM with name %s", config.HOOKS_VM_NAME)
    assert vms.createVm(
        positive=True,
        vmName=config.HOOKS_VM_NAME,
        cluster=config.clusters_names[0],
        display_type=config.display_type_vnc,
        template=config.templates_names[0],
        custom_properties=CUSTOM_HOOK
    )

    def finalize():
        testflow.teardown("Tearing down module %s.", __name__)

        testflow.step("Removing all hooks from %s host.", config.hosts_ips[0])
        assert runMachineCommand(
            positive=True,
            ip=config.hosts_ips[0],
            user=config.hosts_user,
            password=config.hosts_password,
            cmd=REMOVE_HOOKS
        )[0]

        testflow.step("Removing a VM with name %s.", config.HOOKS_VM_NAME)
        assert vms.removeVm(
            positive=True,
            vm=config.HOOKS_VM_NAME,
            stopVM='true'
        )

    request.addfinalizer(finalize)


def check_vdsmd():
    if not test_utils.isVdsmdRunning(
            config.hosts_ips[0],
            config.hosts_user,
            config.hosts_password
    ):
        hosts.start_vdsm(
            config.hosts[0],
            config.hosts_password,
            config.dcs_names[0]
        )


def check_vm():
    if not vms.checkVmState(
            positive=True,
            vmName=config.HOOKS_VM_NAME,
            state=config.vm_state_up
    ):
        vms.restartVm(
            vm=config.HOOKS_VM_NAME,
            wait_for_ip=True,
            placement_host=config.hosts[0],
        )


class TestCaseVm(TestCase):
    """ vm hooks """
    __test__ = False
    CUSTOM_HOOK = "auto_custom_hook"
    PY = "py"

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        """ create shell script """
        testflow.setup("Setting up %s class", cls.__name__)

        testflow.step(
            "Checking for %s VM state",
            config.HOOKS_VM_NAME
        )
        check_vm()

        testflow.step(
            "Creating a Python script with name %s "
            "on host %s to verify %s hook",
            cls._hook_name(ext=cls.PY),
            config.hosts_ips[0],
            cls.CUSTOM_HOOK
        )
        hooks.create_python_script_to_verify_custom_hook(
            ip=config.hosts_ips[0],
            password=config.hosts_password,
            script_name=cls._hook_name(ext=cls.PY),
            custom_hook=cls.CUSTOM_HOOK,
            target=path.join(HOOK_DIR, cls.NAME),
            output_file=path.join(TMP, cls._hook_name()),
        )

        def finalize():
            """ remove created script """
            testflow.teardown("Tearing down %s class", cls.__name__)

            testflow.step("Setting python script name...")
            hook_name = path.join(cls.NAME, cls._hook_name(ext=cls.PY))
            testflow.step("\tPython script name now equals %s.", hook_name)

            testflow.step(
                "Removing python script %s from host %s.",
                hook_name,
                config.hosts_ips[0]
            )
            test_utils.removeFileOnHost(
                positive=True,
                ip=config.hosts_ips[0],
                password=config.hosts_password,
                filename=path.join(HOOK_DIR, hook_name)
            )
            testflow.step("Checking %s VM's state", config.HOOKS_VM_NAME)
            check_vm()

        request.addfinalizer(finalize)

    @classmethod
    def check_for_file(cls, positive):
        """ Check for file created by vdsm_stop hook """
        logger.info("Checking for existence of file %s/%s.", TMP, cls.NAME)
        return hooks.check_for_file_existence_and_content(
            positive,
            ip=config.hosts_ips[0],
            password=config.hosts_password,
            filename=path.join(TMP, cls._hook_name()),
            content=HOOK_VALUE
        )

    @classmethod
    def _hook_name(cls, ext="hook"):
        return "{0}.{1}".format(cls.NAME, ext)


class TestCaseVdsm(TestCase):
    """ vdsm hooks """
    __test__ = False

    SHELL = "sh"

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        """ create shell script """
        testflow.setup("Setting up %s class.", cls.__name__)

        testflow.step("Checking if vdsmd is running.")
        check_vdsmd()

        testflow.step("Setting script name.")
        script_name = cls._hook_name(ext=cls.SHELL)
        testflow.step("\tScript name now equals %s.", script_name)

        testflow.step(
            "Creating shell script %s on %s host.",
            script_name,
            config.hosts_ips[0]
        )
        hooks.create_one_line_shell_script(
            ip=config.hosts_ips[0],
            password=config.hosts_password,
            script_name=script_name,
            command='touch',
            arguments=path.join(TMP, cls._hook_name()),
            target=path.join(HOOK_DIR, cls.NAME)
        )

        def finalize():
            """ remove created script """
            testflow.teardown("Tearing down class %s.", cls.__name__)

            testflow.step("Setting shell script's name.")
            hook_name = path.join(cls.NAME, cls._hook_name(ext=cls.SHELL))
            testflow.step("\tShell script name now equals %s.", hook_name)

            testflow.step(
                "Removing shell script %s from host %s.",
                hook_name,
                config.hosts_ips[0]
            )
            test_utils.removeFileOnHost(
                positive=True,
                ip=config.hosts_ips[0],
                password=config.hosts_password,
                filename=path.join(HOOK_DIR, hook_name)
            )

            testflow.step(
                "Removing hook %s from host %s.",
                cls._hook_name(),
                config.hosts_ips[0]
            )
            test_utils.removeFileOnHost(
                positive=True,
                ip=config.hosts_ips[0],
                password=config.hosts_password,
                filename=path.join(TMP, cls._hook_name())
            )
            testflow.step("Checking if vdsmd is running.")
            check_vdsmd()

        request.addfinalizer(finalize)

    @classmethod
    def check_for_file(cls, positive):
        """ Check for file created by vdsm_stop hook """
        logger.info("Checking for existence of file %s/%s", TMP, cls.NAME)
        return hooks.check_for_file_existence_and_content(
            positive=positive,
            ip=config.hosts_ips[0],
            password=config.hosts_password,
            filename=path.join(TMP, cls._hook_name())
        )

    @classmethod
    def _hook_name(cls, ext="hook"):
        return "{0}.{1}".format(cls.NAME, ext)


@attr(tier=3)
class TestCaseAfterVdsmStop(TestCaseVdsm):
    """ after_vdsm_stop hook """
    __test__ = True

    NAME = 'after_vdsm_stop'

    @polarion("RHEVM3-8482")
    def test_after_vdsm_stop(self):
        """ test_after_vdsm_stop """
        testflow.step("Stopping vdsm on %s.", config.hosts_ips[0])
        hosts.stop_vdsm(config.hosts[0], config.hosts_password)

        testflow.step(
            "Checking for presence of %s on %s.",
            self._hook_name(),
            config.hosts_ips[0]
        )
        assert self.check_for_file(positive=True)


@attr(tier=3)
class TestCaseBeforeVdsmStart(TestCaseVdsm):
    """ before_vdsm_start hook """
    __test__ = True

    NAME = "before_vdsm_start"

    @polarion("RHEVM3-8483")
    def test_before_vdsm_start(self):
        """ test_before_vdsm_start """
        testflow.step("Stopping vdsm on %s.", config.hosts_ips[0])
        hosts.stop_vdsm(config.hosts[0], config.hosts_password)

        testflow.step(
            "Checking the %s is not at %s.",
            self._hook_name(),
            config.hosts_ips[0]
        )
        assert not self.check_for_file(positive=False)

        testflow.step("Starting vdsm on %s.", config.hosts_ips[0])
        hosts.start_vdsm(
            config.hosts[0],
            config.hosts_password,
            config.dcs_names[0]
        )

        testflow.step(
            "Checking for presence of %s on %s.",
            self._hook_name(),
            config.hosts_ips[0]
        )
        assert self.check_for_file(positive=True)


@attr(tier=3)
class TestCaseBeforeVmStart(TestCaseVm):
    """ before_vm_start hook """
    __test__ = True

    NAME = "before_vm_start"

    @polarion("RHEVM3-8484")
    def test_before_vm_start(self):
        """ Check for file created by before_vm_start hook """
        testflow.step("Stopping VM %s.", config.HOOKS_VM_NAME)
        assert vms.stopVm(True, vm=config.HOOKS_VM_NAME)

        testflow.step(
            "Checking the %s is not at %s.",
            self._hook_name(),
            config.hosts_ips[0]
        )
        assert not self.check_for_file(positive=False)

        testflow.step("Starting VM %s.", config.HOOKS_VM_NAME)
        assert vms.startVm(
            positive=True,
            vm=config.HOOKS_VM_NAME,
            wait_for_status=config.vm_state_up,
            wait_for_ip=True,
            placement_host=config.hosts[0],
        )

        testflow.step(
            "Checking for presence of %s on %s.",
            self._hook_name(),
            config.hosts_ips[0]
        )
        assert self.check_for_file(positive=True)


@attr(tier=3)
class TestCaseAfterVmPause(TestCaseVm):
    """ after_vm_pause hook """
    __test__ = True
    NAME = "after_vm_pause"

    @polarion("RHEVM3-8485")
    def test_after_vm_pause(self):
        """ Check for file created by after_vm_pause hook """
        testflow.step("Suspending VM %s.", config.HOOKS_VM_NAME)
        assert vms.suspendVm(True, vm=config.HOOKS_VM_NAME, wait=True)

        testflow.step(
            "Checking for presence of %s on %s.",
            self._hook_name(),
            config.hosts_ips[0]
        )
        assert self.check_for_file(positive=True)
