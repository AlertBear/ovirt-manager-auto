"""
Virt - Payloads Test
Check different cases for adding payloads to vm, via creation or update, also
check mount of different types of payloads, cdrom, floppy.
"""
import os
import logging
from nose.tools import istest
from art.unittest_lib import attr
from art.unittest_lib import ComputeTest as TestCase
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611
from art.test_handler.settings import opts
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.rhevm_api.tests_lib.high_level.vms as high_vms
from art.rhevm_api.tests_lib.low_level.hooks import \
    checkForFileExistenceAndContent
from art.rhevm_api.utils.resource_utils import runMachineCommand
from rhevmtests.virt import config


logger = logging.getLogger(__name__)

ENUMS = opts['elements_conf']['RHEVM Enums']
PAYLOADS_TYPE = [ENUMS['payload_type_cdrom'], ENUMS['payload_type_floppy']]
PAYLOADS_DEVICES = ['/dev/sr1', '/dev/fd0']
PAYLOADS_FILENAME = ['payload.cdrom', 'payload.floppy']
PAYLOADS_CONTENT = ['cdrom payload via create',
                    'cdrom payload via update',
                    'floppy payload via create',
                    'floppy payload via update',
                    'complex\npayload\nfor\nuse']
VM_DSC = 'payload test'
TMP_DIR = '/tmp'
TIMEOUT = 60
CONN_TIMEOUT = 30
TCMS_PLAN_ID = 7775


@attr(tier=0)
class Payloads(TestCase):
    """
    Base class for Payloads Test
    """
    __test__ = False
    payload_filename = None
    payload_content = None
    payload_type = None
    vm_name = "payloads_vm"

    @classmethod
    def teardown_class(cls):
        """
        Stop and remove vm after each test case
        """
        if vms.get_vm_state(cls.vm_name) not in (ENUMS['vm_state_down'],):
            logging.info("Stop vm %s", cls.vm_name)
            if not vms.stopVm(True, cls.vm_name):
                raise errors.VMException("Failed to stop vm %s" %
                                         cls.vm_name)
        logging.info("Remove vm %s", cls.vm_name)
        if not vms.removeVm(True, cls.vm_name):
            raise errors.VMException("Failed to remove vm %s" %
                                     cls.vm_name)
        logging.info("Clean files from engine machine after existence check")
        filename = os.path.join(TMP_DIR, cls.payload_filename)
        cmd = "rm -f %s" % filename
        logging.info("Remove file %s from engine machine" % filename)
        status, out = runMachineCommand(True, ip=config.VDC_HOST,
                                        user=config.VDC_ROOT_USER,
                                        password=config.VDC_ROOT_PASSWORD,
                                        cmd=cmd)
        if not status:
            raise errors.VMException("Failed to run command %s on engine %s" %
                                     (cmd, config.VDC_HOST))

    @classmethod
    def _create_vm_with_payloads(cls):
        """
        Create new vm with given payload
        """
        logging.info("Add new vm %s with payloads"
                     "(type=%s, filename=%s,"" content=%s)",
                     cls.vm_name, cls.payload_type,
                     cls.payload_filename, cls.payload_content)
        if not vms.addVm(True, name=cls.vm_name,
                         cluster=config.CLUSTER_NAME[0],
                         template=config.TEMPLATE_NAME[0],
                         payloads=[(cls.payload_type, cls.payload_filename,
                                    cls.payload_content)]):
            raise errors.VMException("Failed to add vm %s" %
                                     cls.vm_name)

    @classmethod
    def _update_vm_with_payloads(cls):
        """
        First create vm without payloads and after it update it with payloads
        """
        logging.info("Add new vm %s without payloads", cls.vm_name)
        if not vms.addVm(True, name=cls.vm_name,
                         cluster=config.CLUSTER_NAME[0],
                         template=config.TEMPLATE_NAME[0]):
            raise errors.VMException("Failed to add vm %s" %
                                     cls.vm_name)
        logging.info("Update vm %s with payloads"
                     "(type=%s, filename=%s,"" content=%s)",
                     cls.vm_name, cls.payload_type,
                     cls.payload_filename, cls.payload_content)
        if not vms.updateVm(True, cls.vm_name,
                            payloads=[(cls.payload_type,
                                       cls.payload_filename,
                                       cls.payload_content)]):
            raise errors.VMException("Failed to update vm %s with payloads" %
                                     cls.vm_name)

    @classmethod
    def _get_vm_ip(cls):
        """
        Start vm and return vm ip
        """
        return high_vms.get_vm_ip(cls.vm_name)

    @classmethod
    def _check_existence_of_payload(cls, payload_device):
        """
        Start vm, mount payload and check if payload content exist
        """
        payload_dir = os.path.join(TMP_DIR, cls.payload_type)
        ip = cls._get_vm_ip()
        logging.info("Create new directory %s on vm %s and modprobe device",
                     payload_dir, cls.vm_name)
        cmd = 'mkdir %s && modprobe %s' % (payload_dir, cls.payload_type)
        status, out = runMachineCommand(True, ip=ip,
                                        user=config.VMS_LINUX_USER,
                                        password=config.VMS_LINUX_PW, cmd=cmd)
        if not status:
            raise errors.VMException("Failed to run command %s on vm %s: %s" %
                                     (cmd, cls.vm_name, out))
        logging.info("Mount device %s to directory %s",
                     payload_device, payload_dir)
        cmd = 'mount %s %s' % (payload_device, payload_dir)
        status, out = runMachineCommand(True, ip=ip,
                                        user=config.VMS_LINUX_USER,
                                        password=config.VMS_LINUX_PW,
                                        cmd=cmd, timeout=TIMEOUT,
                                        conn_timeout=CONN_TIMEOUT)
        if not status:
            raise errors.VMException("Failed to run command %s on vm %s: %s" %
                                     (cmd, cls.vm_name, out))
        logging.info("Check if file content exist on vm %s",
                     cls.vm_name)
        filename = os.path.join(payload_dir, cls.payload_filename)
        if not checkForFileExistenceAndContent(True, ip=ip,
                                               user=config.VMS_LINUX_USER,
                                               password=config.VMS_LINUX_PW,
                                               filename=filename,
                                               content=cls.payload_content):
            logging.error("File %s does not exist on vm %s",
                          filename, cls.vm_name)
            return False
        return True


class PayloadViaCreate(Payloads):
    """
    Base class for payloads via create
    """
    __test__ = False
    payload_filename = None
    payload_content = None
    payload_type = None

    @classmethod
    def setup_class(cls):
        """
        Create new vm with payload
        """
        cls._create_vm_with_payloads()


class PayloadViaUpdate(Payloads):
    """
    Base class for payloads via update
    """
    __test__ = False
    payload_filename = None
    payload_content = None
    payload_type = None

    @classmethod
    def setup_class(cls):
        """
        Create new vm and update it with payload
        """
        cls._update_vm_with_payloads()


class CreateVmWithCdromPayload(PayloadViaCreate):
    """
    Create new vm with cdrom payload via create and check if payload exist,
    also check if payload object exist under vm
    """
    __test__ = True
    payload_filename = PAYLOADS_FILENAME[0]
    payload_content = PAYLOADS_CONTENT[0]
    payload_type = PAYLOADS_TYPE[0]

    @bz({'1158010': {'engine': None, 'version': None}})
    @tcms(TCMS_PLAN_ID, '222049')
    @istest
    def check_existence_of_payload(self):
        """
        Check if cdrom payload exist on vm
        """
        self.assertTrue(self._check_existence_of_payload(PAYLOADS_DEVICES[0]))

    @bz({'1158010': {'engine': None, 'version': None}})
    @tcms(TCMS_PLAN_ID, '304572')
    @istest
    def check_object_existence(self):
        """
        Check if payload object exist under vm
        """
        self.assertTrue(vms.getVmPayloads(True, self.vm_name)[0])


class UpdateVmWithCdromPayloadAndCheckPayloadObject(PayloadViaUpdate):
    """
    Create new vm with cdrom payload via update and check if payload exist
    """
    __test__ = True
    payload_filename = PAYLOADS_FILENAME[0]
    payload_content = PAYLOADS_CONTENT[1]
    payload_type = PAYLOADS_TYPE[0]

    @tcms(TCMS_PLAN_ID, '222050')
    @istest
    def check_existence_of_payload(self):
        """
        Check if cdrom payload exist on vm
        """
        self.assertTrue(self._check_existence_of_payload(PAYLOADS_DEVICES[0]))


@attr(tier=1)
class CdromPayloadComplexContent(PayloadViaUpdate):
    """
    Create new vm with cdrom payload, that have complex content via update
    and check if payload exist
    """
    __test__ = True
    payload_filename = PAYLOADS_FILENAME[0]
    payload_content = PAYLOADS_CONTENT[4]
    payload_type = PAYLOADS_TYPE[0]

    @tcms(TCMS_PLAN_ID, '304571')
    @istest
    def check_existence_of_payload(self):
        """
        Check if cdrom payload exist on vm
        """
        self.assertTrue(self._check_existence_of_payload(PAYLOADS_DEVICES[0]))


class CreateVmWithFloppyPayload(PayloadViaCreate):
    """
    Create new vm with floppy payload via create and check if payload exist
    """
    __test__ = True
    payload_filename = PAYLOADS_FILENAME[1]
    payload_content = PAYLOADS_CONTENT[2]
    payload_type = PAYLOADS_TYPE[1]

    @tcms(TCMS_PLAN_ID, '302730')
    @istest
    def check_existence_of_payload(self):
        """
        Check if floppy payload exist on vm
        """
        self.assertTrue(self._check_existence_of_payload(PAYLOADS_DEVICES[1]))


class UpdateVmWithFloppyPayload(PayloadViaUpdate):
    """
    Create new vm with floppy payload via update and check if payload exist
    """
    __test__ = True
    payload_filename = PAYLOADS_FILENAME[1]
    payload_content = PAYLOADS_CONTENT[3]
    payload_type = PAYLOADS_TYPE[1]

    @tcms(TCMS_PLAN_ID, '302731')
    @istest
    def check_existence_of_payload(self):
        """
        Check if floppy payload exist on vm
        """
        self.assertTrue(self._check_existence_of_payload(PAYLOADS_DEVICES[1]))
