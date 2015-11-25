from art.rhevm_api.tests_lib.low_level import vms

from rhevmtests.system.guest_tools.linux_guest_agent import config


def teardown_package():
    for image in sorted(config.TEST_IMAGES):
        vms.removeVm(True, image, stopVM='true')
