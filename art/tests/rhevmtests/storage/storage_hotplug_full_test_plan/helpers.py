"""
Hotplug test helpers functions
"""

import logging
import os
from art.unittest_lib import StorageTest as TestCase
import tempfile
from concurrent.futures import ThreadPoolExecutor
from art.rhevm_api.utils import test_utils

from utilities import machine
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level import storagedomains

import config

LOGGER = logging.getLogger(__name__)

ENUMS = config.ENUMS

FILE_WITH_RESULTS = "/tmp/hook.txt"

HOOKFILENAME = tempfile.mkstemp()[1]
HOOKWITHSLEEPFILENAME = tempfile.mkstemp()[1]
HOOKPRINTFILENAME = tempfile.mkstemp()[1]
HOOKJPEG = tempfile.mkstemp(suffix=".jpeg")[1]

DISKS_TO_PLUG = ["disk_to_plug_%s" % x for x in range(10)]
UNATTACHED_DISK = "unattached_disk"
TEXT = 'Hello World!'
VM_NAME = config.VM_NAME[0]

MAIN_HOOK_DIR = "/usr/libexec/vdsm/hooks/"
ALL_AVAILABLE_HOOKS = [
    'before_disk_hotplug', 'after_disk_hotplug', 'before_disk_hotunplug',
    'after_disk_hotunplug']

STORAGE_DOMAIN_API = test_utils.get_api('storage_domain', 'storagedomains')


ONE_PIXEL_FILE = (
    """\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H"""
    """\x00\x00\xff\xfe\x00\x13Created with GIMP\xff\xdb\x00C\x00\x01\x01"""
    """\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"""
    """\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"""
    """\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"""
    """\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xdb\x00C\x01\x01\x01"""
    """\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"""
    """\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"""
    """\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"""
    """\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xc2\x00\x11\x08\x00"""
    """\x01\x00\x01\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14"""
    """\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"""
    """\t\xff\xc4\x00\x14\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"""
    """\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x10\x03\x10"""
    """\x00\x00\x01\x7f\x0f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00"""
    """\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00"""
    """\x01\x05\x02\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00"""
    """\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01"""
    """?\x01\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"""
    """\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x01\x7f"""
    """\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"""
    """\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x06?\x02\x7f\xff\xc4"""
    """\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"""
    """\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?!\x7f\xff\xda\x00\x0c"""
    """\x03\x01\x00\x02\x00\x03\x00\x00\x00\x10\x1f\xff\xc4\x00\x14\x11\x01"""
    """\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff"""
    """\xda\x00\x08\x01\x03\x01\x01?\x10\x7f\xff\xc4\x00\x14\x11\x01\x00\x00"""
    """\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00"""
    """\x08\x01\x02\x01\x01?\x10\x7f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00"""
    """\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01"""
    """\x01\x00\x01?\x10\x7f\xff\xd9""")


def create_vm_with_disks():
    """ creates a VM and installs system on it; then creates 10 disks and
        attaches them to the VM
    """
    storage_domain_name = (storagedomains.getDCStorages(
        config.DATA_CENTER_NAME, False)[0]).name
    vms.createVm(
        True, VM_NAME, VM_NAME, cluster=config.CLUSTER_NAME,
        nic=config.HOST_NICS[0], storageDomainName=storage_domain_name,
        size=config.DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=True, volumeFormat=ENUMS['format_cow'], memory=config.GB,
        diskInterface=config.INTERFACE_VIRTIO,
        cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
        user=config.VMS_LINUX_USER, password=config.VMS_LINUX_PW,
        type=config.VM_TYPE_DESKTOP, installation=True, slim=True,
        image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
        useAgent=config.USE_AGENT)

    for disk_name in DISKS_TO_PLUG + [UNATTACHED_DISK]:
        disks.addDisk(
            True, alias=disk_name, size=config.GB,
            storagedomain=storage_domain_name,
            format=ENUMS['format_cow'], interface=config.INTERFACE_VIRTIO)

    disks.waitForDisksState(",".join(DISKS_TO_PLUG + [UNATTACHED_DISK]))
    for disk_name in DISKS_TO_PLUG:
        disks.attachDisk(True, disk_name, VM_NAME, False)


def create_local_files_with_hooks():
    """ creates all the hook files locally, so in the tests we can only copy
        them to the final location
    """
    # the easiest hook
    with open(HOOKFILENAME, "w+") as handle:
        handle.write("#!/bin/bash\nuuidgen>> %s\n" % FILE_WITH_RESULTS)

    # easy hook with sleep
    with open(HOOKWITHSLEEPFILENAME, "w+") as handle:
        handle.write(
            "#!/bin/bash\nsleep 30s\nuuidgen>> %s\n" % FILE_WITH_RESULTS)

    # hook with print 'Hello World!'
    with open(HOOKPRINTFILENAME, "w+") as handle:
        handle.write("#!/bin/bash\necho %s>> %s\n" % (TEXT, FILE_WITH_RESULTS))

    # jpeg file
    with open(HOOKJPEG, "w+") as handle:
        handle.write(ONE_PIXEL_FILE)


def remove_hook_files():
    """ removes all the local copies of the hook files
    """
    os.remove(HOOKFILENAME)
    os.remove(HOOKWITHSLEEPFILENAME)
    os.remove(HOOKPRINTFILENAME)
    os.remove(HOOKJPEG)


class HotplugHookTest(TestCase):
    """ basic class for disk hotplug hooks
        all tests work like follows:
            * prepare/clear env
            * install hooks
            * perform an action (attach/activate/deactivate a disk)
            * check if correct hooks were called
    """
    hook_dir = None
    vm_name = None
    __test__ = False
    active_disk = None
    hooks = {}
    use_disks = []
    action = [lambda a, b, c, wait: True]

    def run_cmd(self, cmd):
        rc, out = self.machine.runCmd(cmd)
        self.assertTrue(rc, "Command %s failed: %s" % (cmd, out))
        return out

    def create_hook_file(self, local_hook, remote_hook):
        """ copies a local hook file to a remote location
        """
        LOGGER.info("Hook file: %s" % remote_hook)
        assert self.machine.copyTo(local_hook, remote_hook)
        LOGGER.info("Changing permissions")
        self.run_cmd(["chmod", "775", remote_hook])
        self.run_cmd(["chown", "36:36", remote_hook])

    def put_disks_in_correct_state(self):
        """ activate/deactivate disks we will use in the test
        """
        for disk_name in self.use_disks:
            disk = disks.getVmDisk(VM_NAME, disk_name)
            LOGGER.info("Disk active: %s" % disk.active)
            if disk.get_active() and not self.active_disk:
                assert vms.deactivateVmDisk(True, VM_NAME, disk_name)
            elif not disk.get_active() and self.active_disk:
                assert vms.activateVmDisk(True, VM_NAME, disk_name)

    def clear_hooks(self):
        """ clear all vdsm hot(un)plug hook directories
        """
        for hook_dir in ALL_AVAILABLE_HOOKS:
            remote_hooks = os.path.join(MAIN_HOOK_DIR, hook_dir, '*')
            self.run_cmd(['rm', '-f', remote_hooks])

    def clear_file_for_hook_resuls(self):
        """ removes old hook result file, creates an empty result file
        """
        LOGGER.info("Removing old results")
        self.run_cmd(['rm', '-f', FILE_WITH_RESULTS])
        LOGGER.info("Touching result file")
        self.run_cmd(['touch', FILE_WITH_RESULTS])
        LOGGER.info("Changing permissions of results")
        self.run_cmd(['chown', 'vdsm:kvm', FILE_WITH_RESULTS])

    def install_required_hooks(self):
        """ install all the hooks required in the test
        """
        for hook_dir, hooks in self.hooks.iteritems():
            for hook in hooks:
                remote_hook = os.path.join(
                    MAIN_HOOK_DIR, hook_dir, os.path.basename(hook))
                self.create_hook_file(hook, remote_hook)

    def setUp(self):
        """ performed actions:
            * clear all hooks
            * clear hook result file
            * put disks in correct state
            * install new hook(s)
        """
        self.address = vms.getVmHost(VM_NAME)[1]['vmHoster']
        LOGGER.info("Host: %s" % self.address)

        LOGGER.info("Looking for username and password")
        self.user = config.HOSTS_USER
        self.password = config.HOSTS_PW

        LOGGER.info("Creating 'machine' object")
        self.machine = machine.LinuxMachine(
            self.address, self.user, self.password, False)

        LOGGER.info("Clearing old hooks")
        self.clear_hooks()

        LOGGER.info("Clearing old hooks results")
        self.clear_file_for_hook_resuls()

        LOGGER.info("Putting disks in correct state")
        self.put_disks_in_correct_state()

        LOGGER.info("Installing hooks")
        self.install_required_hooks()

    def get_hooks_result_file(self):
        """ reads hook result file
        """
        _, tmpfile = tempfile.mkstemp()
        LOGGER.info("temp: %s" % tmpfile)
        try:
            self.machine.copyFrom(FILE_WITH_RESULTS, tmpfile)
            with open(tmpfile) as handle:
                result = handle.readlines()
            LOGGER.debug("Hook result: %s", "".join(result))
            return result
        finally:
            os.remove(tmpfile)

    def verify_hook_called(self):
        """ verify if the correct hooks were called
            this version only checks if the hook result file is not empty,
            it is redefined in many subclasses
        """
        assert self.get_hooks_result_file()

    def perform_action(self):
        """ perform defined action (plug/unplug disk) on given disks and checks
            it succeeded
        """
        results = []
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            for disk_name in self.use_disks:
                LOGGER.info("Calling %s on %s" % (self.action[0].__name__,
                                                  disk_name))
                results.append(executor.submit(
                    self.action[0], True, VM_NAME, disk_name))
        for result in results:
            self.assertTrue(
                result.result(),
                "Something went wrong: %s" % [i.result() for i in results])

    def perform_action_and_verify_hook_called(self):
        """ calls defined action (activate/deactivate disk) and checks if hooks
            were called
        """
        self.perform_action()
        self.verify_hook_called()

    def tearDown(self):
        """ clear hooks and removes hook results
        """
        self.run_cmd(['rm', '-f', FILE_WITH_RESULTS])
        self.clear_hooks()
