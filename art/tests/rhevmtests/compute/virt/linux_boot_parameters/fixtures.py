#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Fixtures module for CPU hotplug test
"""
import shlex

import pytest

import helper
import rhevmtests.helpers as helpers
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_sd
)
from art.test_handler import exceptions
from art.unittest_lib.common import testflow
from rhevmtests.compute.virt import config

ISO_UPLOADER_FILE = "/etc/ovirt-engine/isouploader.conf"


@pytest.fixture(scope="class")
def attach_iso(request):
    """
    Attach iso domain
    """
    def fin():
        """
        Move the ISO domain to maintenance and detach it.
        """
        testflow.teardown(
            "Move ISO Domain %s to maintenance", config.ISO_DOMAIN_NAME
        )
        assert ll_sd.deactivateStorageDomain(
            True, config.DC_NAME[0], storagedomain=config.ISO_DOMAIN_NAME
        )
        testflow.teardown("Detach ISO domain %s", config.ISO_DOMAIN_NAME)
        assert ll_sd.detachStorageDomain(
            True, config.DC_NAME[0], storagedomain=config.ISO_DOMAIN_NAME
        )

    request.addfinalizer(fin)

    testflow.setup("Attach ISO domain %s", config.ISO_DOMAIN_NAME)
    assert ll_sd.attachStorageDomain(
        True, config.DC_NAME[0], storagedomain=config.ISO_DOMAIN_NAME
    )


@pytest.fixture(scope="class")
def copy_files_to_iso(request):
    """
    Copying the initrd and vmlinuz files to iso domain.
    Note - this function is working on rhel7.4 only.
    """
    vm_name = request.cls.vm_name
    vm_resource = helpers.get_vm_resource(vm=vm_name)
    request.cls.root_device = helper.get_vm_root_device(vm_resource)

    # parameters to add to iso uploader conf file
    user = "user=%s" % config.VDC_ADMIN_JDBC_LOGIN
    passwd = "passwd=%s" % config.VDC_PASSWORD

    def fin():
        """
        Remove VM of Linux boot parameters test
        """
        for line in user, passwd:
            command = ('sed -e s/%s//g -i %s' % (line, ISO_UPLOADER_FILE))
            rc, _, _ = config.ENGINE_HOST.run_command(shlex.split(command))

            if rc:
                raise exceptions.VMException(
                    "Failed to run command %s", command
                )

    request.addfinalizer(fin)

    for file, suffix in ({"vmlinuz": None, "initramfs": "img"}.iteritems()):
        command = (
            'cat /etc/grub2.cfg | grep %s  |awk "NR==2" | cut -d " " -f 2 '
            % file
        )
        rc, file_path, _ = vm_resource.run_command(shlex.split(command))
        if rc:
            raise exceptions.VMException("Failed to run command %s", command)
        file_dest_path = file if not suffix else "%s.%s" % (file, suffix)
        file_dest_path = "/tmp/%s" % file_dest_path
        file_source_path = ("/boot/%s" % file_path.strip())
        testflow.setup("Transfer files %s to engine", file_source_path)
        vm_resource.fs.transfer(
            file_source_path, config.ENGINE_HOST, file_dest_path
        )
        config.ENGINE_HOST.run_command(
            shlex.split(
                "echo -e '%s \n%s' >> %s" % (user, passwd, ISO_UPLOADER_FILE)
            )
        )
        if config.ENGINE_HOST.run_command(
            shlex.split(
                "engine-iso-uploader upload %s -i %s --force" %
                (file_dest_path, config.ISO_DOMAIN_NAME)
            )
        )[0]:
            raise exceptions.VMException(
                "Failed to upload file %s to %s",
                file_dest_path, config.ISO_DOMAIN_NAME
            )


@pytest.fixture()
def clean_vm(request):
    """
    Stop VM and Reset to default values
    """
    vm_name = request.cls.vm_name
    assert ll_vms.stop_vms_safely([vm_name])
    assert ll_vms.updateVm(
        positive=True, vm=vm_name, kernel="", initrd="", cmdline=""
    )
