#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Virt - Payloads Test
Check different cases for adding payloads to vm, via creation or update, also
check mount of different types of payloads, cdrom, floppy.
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/Compute/Virt_Payload
"""

import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import helper
from art.test_handler.tools import polarion
from art.unittest_lib import VirtTest, testflow
from art.unittest_lib import (
    tier2,
    tier3,
)
from fixtures import (
    create_vm_with_payloads, remove_payload_files
)
from rhevmtests.compute.virt.fixtures import (
    start_vms, remove_vm
)


@pytest.mark.usefixtures(
    create_vm_with_payloads.__name__,
    start_vms.__name__,
    remove_vm.__name__,
    remove_payload_files.__name__
)
class TestCreateVmWithCdromPayload(VirtTest):
    """
    Create new vm with cdrom payload via create and check if payload exist,
    also check if payload object exist under vm
    """

    vm_name = 'CreateVmWithCdromPayload'
    payload_filename = config.PAYLOADS_FILENAME[0]
    payload_content = config.PAYLOADS_CONTENT[0]
    payload_type = config.PAYLOADS_TYPE[0]

    @tier2
    @polarion("RHEVM3-10061")
    def test_check_existence_of_payload(self):
        """
        Check if cdrom payload exist on vm
        """
        testflow.setup("Check if CD-ROM payload exist on VM")
        assert helper.check_existence_of_payload(
            vm_name=self.vm_name,
            payload_filename=self.payload_filename,
            payload_content=self.payload_content,
            payload_type=self.payload_type,
            payload_device=config.PAYLOADS_DEVICES[0]
        )

    @tier2
    @polarion("RHEVM3-10074")
    def test_check_object_existence(self):
        """
        Check if payload object exist under vm
        """
        testflow.setup("Check if payload object exist")
        assert ll_vms.getVmPayloads(True, self.vm_name)[0]


@pytest.mark.usefixtures(
    create_vm_with_payloads.__name__,
    start_vms.__name__,
    remove_vm.__name__,
    remove_payload_files.__name__
)
class TestUpdateVmWithCdromPayloadAndCheckPayloadObject(VirtTest):
    """
    Create new vm with cdrom payload via update and check if payload exist
    """

    vm_name = 'UpdateVmWithCdromPayload'
    payload_filename = config.PAYLOADS_FILENAME[0]
    payload_content = config.PAYLOADS_CONTENT[1]
    payload_type = config.PAYLOADS_TYPE[0]

    @tier2
    @polarion("RHEVM3-10063")
    def test_check_existence_of_payload(self):
        """
        Check if cdrom payload exist on vm
        """
        testflow.setup("Check if cdrom payload exist on VM")
        assert helper.check_existence_of_payload(
            vm_name=self.vm_name,
            payload_filename=self.payload_filename,
            payload_content=self.payload_content,
            payload_type=self.payload_type,
            payload_device=config.PAYLOADS_DEVICES[0]
        )


@pytest.mark.usefixtures(
    create_vm_with_payloads.__name__,
    start_vms.__name__,
    remove_vm.__name__,
    remove_payload_files.__name__
)
class TestCdromPayloadComplexContent(VirtTest):
    """
    Create new vm with cdrom payload, that have complex content via update
    and check if payload exist

    """
    vm_name = 'CdromPayloadComplexContent'
    payload_filename = config.PAYLOADS_FILENAME[0]
    payload_content = config.PAYLOADS_CONTENT[4]
    payload_type = config.PAYLOADS_TYPE[0]

    @tier3
    @polarion("RHEVM3-12155")
    def test_check_existence_of_payload(self):
        """
        Check if cdrom payload exist on vm
        """
        testflow.setup("Check if cdrom payload exist on VM")
        assert helper.check_existence_of_payload(
            vm_name=self.vm_name,
            payload_filename=self.payload_filename,
            payload_content=self.payload_content,
            payload_type=self.payload_type,
            payload_device=config.PAYLOADS_DEVICES[0]
        )


@pytest.mark.usefixtures(
    create_vm_with_payloads.__name__,
    start_vms.__name__,
    remove_vm.__name__,
    remove_payload_files.__name__
)
class TestCreateVmWithFloppyPayload(VirtTest):
    """
    Create new vm with floppy payload via create and check if payload exist
    """

    vm_name = 'CreateVmWithFloppyPayload'
    payload_filename = config.PAYLOADS_FILENAME[1]
    payload_content = config.PAYLOADS_CONTENT[2]
    payload_type = config.PAYLOADS_TYPE[1]

    @tier2
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-10070")
    def test_check_existence_of_payload(self):
        """
        Check if floppy payload exist on vm
        """
        testflow.setup("Check if floppy payload exist on VM")
        assert helper.check_existence_of_payload(
            vm_name=self.vm_name,
            payload_filename=self.payload_filename,
            payload_content=self.payload_content,
            payload_type=self.payload_type,
            payload_device=config.PAYLOADS_DEVICES[1]
        )


@pytest.mark.usefixtures(
    create_vm_with_payloads.__name__,
    start_vms.__name__,
    remove_vm.__name__,
    remove_payload_files.__name__
)
class TestUpdateVmWithFloppyPayload(VirtTest):
    """
    Create new vm with floppy payload via update and check if payload exist
    """

    vm_name = 'UpdateVmWithFloppyPayload'
    payload_filename = config.PAYLOADS_FILENAME[1]
    payload_content = config.PAYLOADS_CONTENT[3]
    payload_type = config.PAYLOADS_TYPE[1]

    @tier2
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-10072")
    def test_check_existence_of_payload(self):
        """
        Check if floppy payload exist on vm
        """
        testflow.setup("Check if floppy payload exist on VM")
        assert helper.check_existence_of_payload(
            vm_name=self.vm_name,
            payload_filename=self.payload_filename,
            payload_content=self.payload_content,
            payload_type=self.payload_type,
            payload_device=config.PAYLOADS_DEVICES[1]
        )
