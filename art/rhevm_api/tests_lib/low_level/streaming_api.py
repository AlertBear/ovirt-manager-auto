#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
)
from art.unittest_lib import testflow
from art.test_handler import exceptions
from art.test_handler.settings import ART_CONFIG, GE
from concurrent.futures import ThreadPoolExecutor
import ovirtsdk4 as sdk
import ovirtsdk4.types as types
import ssl
import shlex
from subprocess import Popen, PIPE
import os
import time
from httplib import HTTPSConnection
from urlparse import urlparse
import logging
logger = logging.getLogger(__name__)


ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
STORAGE_TYPE_NFS = ENUMS['storage_type_nfs']
STORAGE_TYPE_ISCSI = ENUMS['storage_type_iscsi']
STORAGE_TYPE_FCP = ENUMS['storage_type_fcp']
STORAGE_TYPE_CEPH = ENUMS['storage_type_ceph']
ENGINE_URL = GE['api_url']
ADMIN_USER_NAME = GE['username']
ORIG_VDC_PASSWORD = GE['password']
CA_FILE = '/var/tmp/ca.crt'
TARGET_FILE_PATH = os.path.expanduser('~')
TARGET_FILE = os.path.expanduser('~/target_download_file')
DEBUG_LOG = os.path.expanduser('~/download_image_debug_log')
MD5SUM_BLOCK_IMAGE_PATH = 'md5sum /dev/%s/%s'
MD5SUM_FILE_IMAGE_PATH = 'md5sum /rhev/data-center/%s/%s/images/%s/%s'
DISK_SPACE_CMD = 'df -B1'
LV_CHANGE_CMD = 'lvchange -a %s %s/%s'
IMAGE_FILE_SIZE_CMD = 'ls -l /rhev/data-center/%s/%s/images/%s/%s'
TRANSFER_INITIALIZING_STATE_TIMEOUT = 300


class StreamingApi(object):
    """
    Represents an object with the ability to download or upload Red Hat
    Virtualization images (for example, virtual machine images) using the
    Red Hat Virtualization ImageIO API.

     Args:
      image_path (str): image source/target path for upload/download
      image_size (int): image size in bytes
    """

    def __init__(self, image_path, image_size):
        self._image_path = image_path
        self._image_size = image_size

    @property
    def image_path(self):
        return self._image_path

    @property
    def image_size(self):
        return self._image_size

    @staticmethod
    def image_size_for_download(host, storage_type, disk_id, sp_id):
        """
        Returns disk image size (in bytes) for download

        Args:
            host (host): Host resource object
            storage_type (str): Specify the storage type
            disk_id (str): The disk id
            sp_id (str): Storage pool id (only needed for File)

        Returns:
            int: The size of a specific disk image before download in bytes

        """
        disk_object = ll_disks.get_disk_obj(disk_id, attribute='id')
        image_id = disk_object.get_image_id()
        sd_id = (
            disk_object.get_storage_domains().get_storage_domain()[0].get_id()
        )
        if storage_type in [STORAGE_TYPE_ISCSI, STORAGE_TYPE_FCP]:
            download_size = ll_disks.get_disk_obj(
                disk_id, attribute='id'
            ).get_provisioned_size()

        else:
            rc, output, error = host.run_command(
                shlex.split(IMAGE_FILE_SIZE_CMD % (
                    sp_id, sd_id, disk_id, image_id
                ))
            )
            assert not rc, "Size command failed with error %s" % error
            download_size = int(shlex.split(output)[4])
            logger.info("Image size is: %s", download_size)

        return download_size

    @staticmethod
    def md5sum_before_download(host, storage_type, disk_id, sp_id):
        """
        returns the md5sum of a specific disk before download

        Args:
            host (host): Host resource object
            storage_type (str): Specific the storage type
            disk_id (str): The disk id
            sp_id (str): Storage pool id (only needed for File)

        Returns:
            str: The md5sum of a specific disk image before download

        """
        disk_object = ll_disks.get_disk_obj(disk_id, attribute='id')
        image_id = disk_object.get_image_id()
        sd_id = (
            disk_object.get_storage_domains().get_storage_domain()[0].get_id()
        )

        if storage_type in [STORAGE_TYPE_ISCSI, STORAGE_TYPE_FCP]:
            logger.info(
                "Activating the disk image before md5sum"
            )
            assert host.lvm.pvscan(), (
                "Unable to refresh the physical volumes on host '%s'" % host
            )
            logger.info(
                "running command:\n " + LV_CHANGE_CMD, 'y', sd_id,
                image_id
            )
            assert host.lvm.lvchange(sd_id, image_id, activate=True), (
                "Unable to activate the disk LV"
            )
            logger.info(
                "Executing md5sum on disk path /dev/%s/%s", sd_id, image_id
            )

            rc, output, error = host.run_command(
                shlex.split(MD5SUM_BLOCK_IMAGE_PATH % (sd_id, image_id))
            )

            assert rc == 0, "Md5sum command failed %s" % error

            logger.info(
                "Running command:\n" + LV_CHANGE_CMD, 'n', sd_id,
                image_id
            )
            assert host.lvm.lvchange(sd_id, image_id, activate=False), (
                "Unable to deactivate the disk LV %s" % image_id
            )

        else:
            rc, output, error = host.run_command(
                shlex.split(
                    MD5SUM_FILE_IMAGE_PATH % (
                        sp_id, sd_id, disk_id, image_id,

                    )
                )
            )
            assert rc == 0, "Md5sum command failed %s" % error

        logger.info("Md5sum is: %s", shlex.split(output)[0])
        return shlex.split(output)[0]

    @staticmethod
    def check_disk_space_before_download_file(
        disk_id, path=TARGET_FILE_PATH, image_size=None
    ):
        """
        Check available disk space at the target directory before download.
        If there is not enough space assert .

        Args:
            disk_id (str): Disk id
            image_size (int): The size of the image in bytes
            path (str): The target file's path

        Raises:
        AssertionError: If there is not enough space to download the file
        """

        if not image_size:
            image_size = ll_disks.get_disk_obj(
                disk_id, attribute='id'
            ).get_provisioned_size()
        output, err = Popen(
            shlex.split(DISK_SPACE_CMD + " " + path),
            stdout=PIPE, stderr=PIPE
        ).communicate()
        assert not err, (
            "Error %s occurred when trying to execute the command" % err
        )
        available_space_size = shlex.split(output)[10]

        assert image_size < available_space_size, (
            "Not enough space for source image in target directory %s \n"
            "Available space size: %s \n Image size: %s \n" % (
                available_space_size, image_size, TARGET_FILE_PATH
            )
        )

    @staticmethod
    def md5sum_after_download(output=TARGET_FILE):
        """
        returns the md5sum output of a specific disk after image download

        Args:
            output (str): Output path of the downloaded image

        Returns:
            str: The md5sum of the downloaded image of a disk

        """
        out, err = Popen(
            ["md5sum", output], stdout=PIPE, stderr=PIPE
        ).communicate()
        assert not err, (
            "Error %s occurred when trying to execute the command" % err
        )
        logger.info("Md5sum is: %s", shlex.split(out)[0])
        return shlex.split(out)[0]

    def compare_md5sum_before_after_download(
        self, md5sum_before, output=TARGET_FILE
    ):
        """
        compare md5sum before & after download & asserts if it's not the same

        Args:
            md5sum_before (str): The md5sum value fo the disk before download
            output (str): Output path of the downloaded file

        Returns:

        Raises:
        AssertionError: if md5sum is not the same before & after the download
        """
        md5sum_after = self.md5sum_after_download(output=output)

        assert md5sum_before == md5sum_after, (
            "Md5sum not the same before download is: %s and after its: %s" % (
                md5sum_before, md5sum_after
            )
        )
        logger.info("Md5sum comparison before and after download successful")

    def download_multiple_disks(self, disks_names, sizes_before):
        """
        Download multiple disk images in parallel

        Args:
            disks_names (list): list of disks names about to be downloaded
            sizes_before (list): list of disks sizes about to be downloaded

        Returns:
            list: Output path list of the files location after download

        Raises:
        DiskException: If download fails
        """
        results = list()
        disk_ids = list()
        output_path = list()

        with ThreadPoolExecutor(
            max_workers=len(disks_names)
        ) as executor:
            for index, disk in enumerate(disks_names):
                disk_ids.append(ll_disks.get_disk_obj(disk).get_id())
                output_path.append(TARGET_FILE_PATH + '/' + disk)
                self.check_disk_space_before_download_file(disk_ids[index])
                testflow.step("Download disk %s", disk_ids[index])
                results.append(
                    executor.submit(
                        self.download_image, disk_ids[index],
                        output_path[index], sizes_before[index]
                    )
                )
        for index, result in enumerate(results):
            if result.exception():
                raise result.exception()
            if not result.result:
                raise exceptions.DiskException(
                    "Download of disk id %s failed", disk_ids[index]
                )
            logger.info(
                "Download of disk id %s succeeded", disk_ids[index]
            )
        return output_path

    def download_image(
        self, disk_id, output_file=TARGET_FILE, download_size=None,
    ):
        """
         Download disk image

        Args:
            disk_id (str): Id of the disk
            output_file (str): The downloaded file location after download
            download_size (int): Actual size of the downloaded image in bytes

        """

        # Create the connection to the server:
        connection = sdk.Connection(
            url=ENGINE_URL,
            username=ADMIN_USER_NAME,
            password=ORIG_VDC_PASSWORD,
            ca_file=CA_FILE,
            debug=True,
            log=logger,
        )

        # Get the reference to the root service:
        system_service = connection.system_service()
        logger.info(
            "Get the reference to the root service %s", system_service
        )

        # Get the reference to the disks service:
        disks_service = connection.system_service().disks_service()

        logger.info(
            "Get the reference to the disks service %s", disks_service
        )

        disk_service = disks_service.disk_service(disk_id)
        disk = disk_service.get()
        # Get a reference to the service that manages the image
        # transfer that was added in the previous step:
        transfers_service = system_service.image_transfers_service()

        # Add a new image transfer:
        transfer = transfers_service.add(
            types.ImageTransfer(
                image=types.Image(
                    id=disk.id
                ),
                direction=types.ImageTransferDirection.DOWNLOAD,
            )
        )

        # Get reference to the created transfer service:
        transfer_service = transfers_service.image_transfer_service(
            transfer.id)

        # After adding a new transfer for the disk, the transfer's status will
        # be INITIALIZING. Wait until the init phase is over.
        # The actual transfer can start when its status is "Transferring".
        init_phase_time = 0
        while transfer.phase == types.ImageTransferPhase.INITIALIZING:
            time.sleep(1)
            init_phase_time += 1
            assert init_phase_time == TRANSFER_INITIALIZING_STATE_TIMEOUT, (
                "Transfer status is in init state for %s seconds" %
                TRANSFER_INITIALIZING_STATE_TIMEOUT
            )
            transfer = transfer_service.get()

        # Set needed headers for downloading:
        transfer_headers = {
            'Authorization': transfer.signed_ticket,
        }

        # At this stage, the SDK granted the permission to start transferring
        # the disk, and the user should choose its preferred tool for doing it
        # regardless of the SDK . In this example, we will use Python's
        # httplib.HTTPSConnection for transferring the data.
        proxy_url = urlparse(transfer.proxy_url)
        context = ssl.create_default_context()

        # Note that ovirt-imageio-proxy by default checks the certificates,
        # so if you don't have your CA certificate of the engine in the system,
        # you need to pass it to HTTPSConnection.
        context.load_verify_locations(cafile=CA_FILE)

        proxy_connection = HTTPSConnection(
            proxy_url.hostname,
            proxy_url.port,
            context=context,
        )

        try:
            path = output_file
            mib_per_request = 1
            with open(path, "wb") as mydisk:
                size = download_size
                logger.info("Provisioned size: %s", size)
                chunk_size = 1024 * 1024 * mib_per_request
                pos = 0
                while pos < size:
                    # Extend the transfer session.
                    transfer_service.extend()
                    # Set the range, according to the chunk being downloaded.
                    transfer_headers['Range'] = 'bytes=%d-%d' % (
                        pos, min(size, pos + chunk_size) - 1
                    )
                    # Perform the request.
                    proxy_connection.request(
                        'GET',
                        proxy_url.path,
                        headers=transfer_headers,
                    )
                    # Get response
                    r = proxy_connection.getresponse()

                    # Check the response status:
                    if r.status >= 300:
                        logger.info("Error: %s", r.read())
                        break

                    # Write the content to file:
                    mydisk.write(r.read())
                    logger.info("Completed: %s%% on disk id %s", int(
                        pos / float(size) * 100), disk_id)
                    # Continue to next chunk.
                    pos += chunk_size

        finally:
            # Finalize the session.
            transfer_service.finalize()

        logger.info("Completed %s%% on disk id %s", int(
            pos / float(size) * 100
        ), disk_id)

        # Close the connection to the server:
        connection.close()

        logger.info("Waiting for disk %s to go back to 'OK' state", disk_id)
        ll_disks.wait_for_disks_status([disk_id], key='id')

    def md5sums_sizes_before_download(
        self, host, storage_type, disks_names, sp_id
    ):
        """
        Returns the md5sums & sizes of selected disks before image download

        Args:
            host (host): Host resource object
            storage_type (str): Specify the storage type
            disks_names (list): list of disks names about to be downloaded
            sp_id (str): Storage pool id (only needed for File)

        Returns:
            list: lists of md5sums & sizes of selected disk before download

        """

        md5sums_before = [self.md5sum_before_download(
            host, storage_type, ll_disks.get_disk_obj(disk).get_id(),
            sp_id
        ) for disk in disks_names]
        sizes_before = [self.image_size_for_download(
            host, storage_type, ll_disks.get_disk_obj(disk).get_id(),
            sp_id
        ) for disk in disks_names]
        return md5sums_before, sizes_before
