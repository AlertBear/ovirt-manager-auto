from art.rhevm_api.tests_lib.high_level import datacenters
from art.rhevm_api.tests_lib.low_level import storagedomains, vms, templates
from art.rhevm_api.utils import test_utils
from art.unittest_lib import testflow
from rhevmtests.system.hooks import config
from utilities.rhevm_tools.base import Setup
from utilities.rhevm_tools.config import ConfigUtility


def setup_package():
    testflow.setup("Setting up %s package.", __name__)

    if not config.GOLDEN_ENV:
        testflow.step("So, it's not the Gold environment.")
        testflow.step("Building datacenter.")
        datacenters.build_setup(
            config=config.PARAMETERS,
            storage=config.PARAMETERS,
            storage_type=config.STORAGE_TYPE,
            basename=config.TEST_NAME
        )

        testflow.step("Getting storage domain.")
        storage_domain = storagedomains.getDCStorages(
            config.DC_NAME[0],
            False
        )[0].get_name()

        testflow.step("Creating VM with name %s.", config.HOOKS_VM_NAME)
        assert vms.createVm(
            positive=True,
            vmName=config.HOOKS_VM_NAME,
            cluster=config.CLUSTER_NAME[0],
            nic="nic",
            storageDomainName=storage_domain,
            provisioned_size=config.DISK_SIZE,
            diskType=config.DISK_TYPE_SYSTEM,
            diskInterface=config.DISK_INTERFACE,
            memory=config.GB,
            cpu_socket=config.CPU_SOCKET,
            cpu_cores=config.CPU_CORES,
            nicType=config.NIC_TYPE_VIRTIO,
            display_type=config.DISPLAY_TYPE,
            os_type=config.OS_TYPE,
            user=config.VMS_LINUX_USER,
            password=config.VMS_LINUX_PW,
            installation=True,
            slim=True,
            useAgent=True,
            image=config.COBBLER_PROFILE,
            network=config.MGMT_BRIDGE
        )

        testflow.step("Getting IP of VM %s.", config.HOOKS_VM_NAME)
        ip = vms.waitForIP(config.HOOKS_VM_NAME)
        assert ip[0]
        assert test_utils.setPersistentNetwork(
            ip[1]["ip"],
            config.VMS_LINUX_PW
        )
        testflow.step(
            "Stopping VM %s and creating template %s.",
            config.HOOKS_VM_NAME,
            config.TEMPLATE_NAME[0]
        )
        assert vms.stopVm(True, vm=config.HOOKS_VM_NAME)
        assert templates.createTemplate(
            True,
            vm=config.HOOKS_VM_NAME,
            name=config.TEMPLATE_NAME[0],
            cluster=config.CLUSTER_NAME[0]
        )
        testflow.step("Removing VM so we need no one right now.")
        assert vms.removeVm(True, config.HOOKS_VM_NAME)

    testflow.step("Running Setup() for getting all configuration.")
    setup = Setup(
        config.VDC_HOST,
        config.VDC_ROOT_USER,
        config.VDC_ROOT_PASSWORD,
        conf=config.VARS
    )
    config_util = ConfigUtility(setup)
    config_util(set=config.CUSTOM_PROPERTY, cver=config.VER)
    config_util(set=config.CUSTOM_PROPERTY_VNIC, cver=config.VER)
    test_utils.restart_engine(config.ENGINE, 5, 70)


def teardown_package():
    testflow.teardown("Tearing down package %s.", __name__)
    if not config.GOLDEN_ENV:
        testflow.step("As it's not gold env:")
        testflow.step("\t removing template %s.", config.TEMPLATE_NAME[0])
        assert templates.removeTemplate(True, config.TEMPLATE_NAME[0])

        testflow.step("Cleaning %s datacenter.", config.DC_NAME[0])
        datacenters.clean_datacenter(
            positive=True,
            datacenter=config.DC_NAME[0],
            vdc=config.VDC_HOST,
            vdc_password=config.VDC_ROOT_PASSWORD
        )
