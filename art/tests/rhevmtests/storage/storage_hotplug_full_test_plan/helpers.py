"""
Hotplug test helpers functions
"""

import logging
import os
from art.unittest_lib import StorageTest as TestCase
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from art.rhevm_api.utils import test_utils

from utilities import machine
from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import disks
from art.rhevm_api.tests_lib.low_level.hosts import getHostIP
from rhevmtests.storage.helpers import create_vm_or_clone

import config

LOGGER = logging.getLogger(__name__)

FILE_WITH_RESULTS = "/tmp/hook.txt"

HOOKFILENAME = tempfile.mkstemp()[1]
HOOKWITHSLEEPFILENAME = tempfile.mkstemp()[1]
HOOKPRINTFILENAME = tempfile.mkstemp()[1]
HOOKJPEG = tempfile.mkstemp(suffix=".jpeg")[1]

DISKS_TO_PLUG = dict()
UNATTACHED_DISKS_PER_STORAGE_TYPE = dict()
TEXT = 'Hello World!'
DISKS_WAIT_TIMEOUT = 300


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


def create_vm_with_disks(storage_domain, storage_type):
    """ creates a VM and installs system on it; then creates 10 disks and
        attaches them to the VM
        Parameters:
            * storage_domain: name of the storage domain
            * storage_type: storage type of the domain where the disks will be
                created
        Returns:
            name of the vm created
    """
    vm_name = config.VM_NAME % storage_type
    unattached_disk = 'unattached_disk_%s' % storage_type

    create_vm_or_clone(
        True, vm_name, vm_name, cluster=config.CLUSTER_NAME,
        nic=config.NIC_NAME[0], storageDomainName=storage_domain,
        size=config.VM_DISK_SIZE, diskType=config.DISK_TYPE_SYSTEM,
        volumeType=True, volumeFormat=config.DISK_FORMAT_COW,
        memory=config.GB, diskInterface=config.INTERFACE_VIRTIO,
        cpu_cores=config.CPU_CORES, nicType=config.NIC_TYPE_VIRTIO,
        display_type=config.DISPLAY_TYPE, os_type=config.OS_TYPE,
        user=config.VMS_LINUX_USER, password=config.VMS_LINUX_PW,
        type=config.VM_TYPE_DESKTOP, installation=True, slim=True,
        image=config.COBBLER_PROFILE, network=config.MGMT_BRIDGE,
        useAgent=config.USE_AGENT)

    DISKS_TO_PLUG.update({storage_type: []})
    for index in xrange(10):
        DISKS_TO_PLUG[storage_type].append(
            (
                "disk_to_plug_%s_%s" % (storage_type, str(index))
            )
        )

    UNATTACHED_DISKS_PER_STORAGE_TYPE.update({storage_type: []})
    UNATTACHED_DISKS_PER_STORAGE_TYPE[storage_type].append(unattached_disk)

    all_disks_to_add = (
        DISKS_TO_PLUG[storage_type] +
        UNATTACHED_DISKS_PER_STORAGE_TYPE[storage_type]
    )
    for disk_name in all_disks_to_add:
        disks.addDisk(
            True, alias=disk_name, size=config.GB,
            storagedomain=storage_domain,
            format=config.DISK_FORMAT_COW, interface=config.INTERFACE_VIRTIO)

    disks.wait_for_disks_status(
        all_disks_to_add,
        timeout=DISKS_WAIT_TIMEOUT,
    )
    for disk_name in DISKS_TO_PLUG[storage_type]:
        disks.attachDisk(True, disk_name, vm_name, False)

    return vm_name


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
            disk = disks.getVmDisk(self.vm_name, disk_name)
            LOGGER.info("Disk active: %s" % disk.active)
            if disk.get_active() and not self.active_disk:
                assert vms.deactivateVmDisk(True, self.vm_name, disk_name)
            elif not disk.get_active() and self.active_disk:
                assert vms.activateVmDisk(True, self.vm_name, disk_name)

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
        self.use_disks = DISKS_TO_PLUG[self.storage]
        self.vm_name = config.VM_NAME % self.storage
        assert vms.waitForVMState(self.vm_name)
        self.host_name = vms.getVmHost(self.vm_name)[1]['vmHoster']
        self.host_address = getHostIP(self.host_name)
        LOGGER.info("Host: %s" % self.host_address)

        LOGGER.info("Looking for username and password")
        self.user = config.HOSTS_USER
        self.password = config.HOSTS_PW

        LOGGER.info("Creating 'machine' object")
        self.machine = machine.LinuxMachine(
            self.host_address, self.user, self.password, False)

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
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            future_to_results = dict(
                (executor.submit(
                    self.action[0], True, self.vm_name, disk_name,
                ), disk_name) for disk_name in self.use_disks
            )
        for future in as_completed(future_to_results):
            disk_name = future_to_results[future]
            self.assertTrue(
                future.result(), "Failed to perform action %s on %s" % (
                    self.action[0].__name__, disk_name),
            )

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
