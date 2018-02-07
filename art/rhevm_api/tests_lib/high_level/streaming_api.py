#!/usr/bin/env python

# Copyright (C) 2018 Red Hat, Inc.
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
    streaming_api as ll_streaming_api,
)
from art.unittest_lib import testflow
from art.test_handler import exceptions
from concurrent.futures import ThreadPoolExecutor
import logging
import os
logger = logging.getLogger("art.hl_lib.streaming_api")
DOWNLOAD_DIR_PATH = '~/download/'
FILE_PATH = os.path.expanduser(DOWNLOAD_DIR_PATH)
UPLOAD_DIR_PATH = '~/upload/'
UPLOAD_FILES_LOCALHOST = [
    os.path.expanduser(
        UPLOAD_DIR_PATH + 'qcow2_v2_rhel7.4_ovirt4.2_guest_disk_1G'
    ),
    os.path.expanduser(UPLOAD_DIR_PATH + 'qcow2_v3_cow_sparse_disk_1G'),
    os.path.expanduser(UPLOAD_DIR_PATH + 'test_raw_to_delete')
]
DOWNLOAD = 'download'
UPLOAD = 'upload'


class StreamingApiHl(ll_streaming_api.StreamingApi):
    """
    Represents an object with the ability to download or upload Red Hat
    Virtualization images (for example, virtual machine images) using the
    Red Hat Virtualization ImageIO API.
    """
    result = None

    @property
    def image_path(self):
        return super(StreamingApiHl, self).image_path

    @property
    def image_size(self):
        return super(StreamingApiHl, self).image_size

    @property
    def direction(self):
        return super(StreamingApiHl, self).direction

    def __init__(self, image_path, image_size, direction):
        """
        Args:
            image_path (str): Image source/target path for upload/download on
            localhost
            image_size (int): Image size in bytes
            direction (str): Direction of image transfer download/upload
        """
        super(StreamingApiHl, self).__init__(image_path, image_size, direction)

    def md5sum_before_transfer(
        self, host=None, storage_type=None, disk_object=None, sp_id=None,
        image_path=image_path
    ):
        """
        Returns the md5sum of a specific disk before transfer(download/upload)
        Download direction- ms5sum before transfer will be on the VDSM host
        Upload direction - ms5sum before transfer will be on the local host

        Args:
            host (host): Host resource object
            storage_type (str): Specific storage type
            disk_object (Disk): The disk object
            sp_id (str): Storage pool id (only needed for File)
            image_path (str): Path of the transferred image on the local host

        Returns:
            str: The md5sum of a specific disk image before transfer

        """
        if self.direction == DOWNLOAD:
            logger.info(
                "Checking md5sum on disk name %s before download",
                disk_object.get_alias()
            )
            out = self.md5sum_on_vdsm_host(
                host=host, storage_type=storage_type, disk_object=disk_object,
                sp_id=sp_id
            )
        else:
            logger.info(
                "Checking md5sum on disk name %s before upload", image_path
            )
            out = self.md5sum_on_localhost(image_path)

        return out

    def md5sum_after_transfer(
        self, host=None, storage_type=None, disk_object=None, sp_id=None,
        image_path=None
    ):
        """
        Returns the md5sum output of a specific disk after image transfer
        Download direction- ms5sum after transfer will be on localhost
        Upload direction - ms5sum before transfer will be on VDSM host

        Args:
            host (host): Host resource object
            storage_type (str): Specific the storage type
            disk_object (str): The disk object
            sp_id (str): Storage pool id (only needed for File)
            image_path (str): Path of the transferred image on the local host

        Returns:
            str: The md5sum of the image after transfer

        """
        info = "Checking md5sum on disk name %s after %s"
        if self.direction == UPLOAD:
            logger.info(info, disk_object.get_alias(), self.direction)
            out = self.md5sum_on_vdsm_host(
                host, storage_type, disk_object, sp_id
            )
        else:
            logger.info(info, image_path, self.direction)
            out = self.md5sum_on_localhost(image_path)

        return out

    def md5sums_sizes_before_transfer(
        self, host=None, storage_type=None, disk_names=None, sp_id=None,
        image_paths=UPLOAD_FILES_LOCALHOST, snapshot=False,
        sdisks_objects=None, extend=False
    ):
        """
        Returns the md5sums and sizes of selected disks before image transfer

        Args:
            host (host): Host resource object
            storage_type (str): Specify the storage type
            disk_names (list): Disks names about to be downloaded
            sp_id (str): Storage pool id (only needed for File)
            image_paths (list): Upload image paths on local host
            snapshot (bool): True testing a snapshot disk false otherwise
            sdisks_objects (list): Relevant snapshot disks objects list
            extend (bool): True if disk was extended,False otherwise

        Returns:
            list: lists of md5sums and sizes of selected disks before download

        """
        info = "Checking %s before %s on %s:\n %s"
        if self.direction == DOWNLOAD and snapshot:
            # As disk names and snapshot disk names are the same , only needed
            # snapshots disks are checked
            logger.info(
                info, "md5sums", self.direction, "disks snapshot", disk_names
            )
            md5sums_before = [
                self.md5sum_before_transfer(
                    host, storage_type, sdisks_objects[i], sp_id
                ) for i in range(len(disk_names))
            ]

            logger.info(
                info, "sizes", self.direction, "disks snapshot", disk_names
            )

            sizes_before = [
                self.image_size_for_transfer(
                    host, storage_type, sdisks_objects[i], sp_id
                ) for i in range(len(disk_names))
            ]

        elif self.direction == DOWNLOAD:
            logger.info(info, "md5sums", self.direction, "disks", disk_names)

            md5sums_before = [
                self.md5sum_before_transfer(
                    host, storage_type, ll_disks.get_disk_obj(disk), sp_id
                ) for disk in disk_names
            ]
            logger.info(info, "sizes", self.direction, "disks", disk_names)

            sizes_before = [
                self.image_size_for_transfer(
                    host, storage_type, ll_disks.get_disk_obj(disk), sp_id,
                    extend=extend
                ) for disk in disk_names
            ]

        else:
            logger.info(info, "md5sums", self.direction, "disks", image_paths)
            md5sums_before = [
                self.md5sum_before_transfer(image_path=path)
                for path in image_paths
            ]
            logger.info(info, "sizes", self.direction, "disks", image_paths)
            sizes_before = [
                self.image_size_for_transfer(image_path=path)
                for path in image_paths
            ]

        return md5sums_before, sizes_before

    def compare_md5sum_before_after_transfer(
        self, md5sum_before, output=image_path, host=None, storage_type=None,
        disk_object=None, sp_id=None
    ):
        """
        Compare md5sum before and after image transfer

        Args:
            md5sum_before (str): The md5sum value fo the disk before download
            output (str): Output path of the downloaded file
            host (host): Host resource object
            storage_type (str): Specific the storage type
            disk_object (Disk): The disk object
            sp_id (str): Storage pool id (only needed for File)


        Raises:
            AssertionError: if md5sum is not the same before and after the
                download
        """
        if self.direction == DOWNLOAD:
            md5sum_after = self.md5sum_after_transfer(image_path=output)
        else:
            md5sum_after = self.md5sum_after_transfer(
                host, storage_type, disk_object, sp_id
            )
        logger.info("Comparing md5sum before and after transfer")
        assert md5sum_before == md5sum_after, (
            "Md5sum not the same before transfer is: %s and after its: %s" % (
                md5sum_before, md5sum_after
            )
        )
        logger.info("Md5sum comparison before and after transfer successful")

    def transfer_image(
        self, image_id, image_path=image_path, transfer_size=image_size,
        positive=True, snapshot=False, pause=False, interrupt=False,
        vm_name=None, disk_name=None
    ):
        """
        Transfer disk image

        Args:
            image_id (str): Id of the disk image
            image_path (str): Image location before transfer on localhost
            transfer_size (int): Actual size of the transferred image in bytes
            positive (bool): True if transfer is expected to be successful
            snapshot (bool): True if snapshot disk is transfered
            pause (bool): True performing pause during transfer,False otherwise
            interrupt (bool): True if additional action is planed during
                disk download, False otherwise
            vm_name (string): Name of the VM
            disk_name (string): Name of the transferred disk
        """
        (
            connection, transfer_service, transfer_headers,
            proxy_url, proxy_connection, transfer
        ) = self.prepare_for_transfer(image_id, snapshot=snapshot)

        if self.direction == DOWNLOAD:
            if snapshot is True and positive is True:
                logger.info("Starting disk snapshot id %s download", image_id)
                assert self.download_disk_snapshot(
                    connection, transfer_service, proxy_url, proxy_connection,
                    image_path=image_path, image_id=image_id,
                ), "Download disk snapshot id %s failed" % image_id

            elif positive:
                logger.info("Starting disk id %s download", image_id)
                assert self.download_disk(
                    connection, transfer_service, transfer_headers, proxy_url,
                    proxy_connection, image_path=image_path,
                    transfer_size=transfer_size, image_id=image_id,
                    pause=pause, interrupt=interrupt, vm_name=vm_name,
                    disk_name=disk_name
                ), "Download disk %s failed" % image_id
            else:
                logger.info(
                    "Starting disk id %s download - expected to fail", image_id
                )
                assert not self.download_disk(
                    connection, transfer_service, transfer_headers, proxy_url,
                    proxy_connection, image_path=image_path,
                    transfer_size=transfer_size, image_id=image_id,
                    pause=pause, interrupt=interrupt, vm_name=vm_name,
                    disk_name=disk_name
                ), "Download disk %s succeeded" % image_id
        else:
            if positive:
                logger.info("Starting disk %s upload", image_path)
                assert self.upload_disk(
                    connection, transfer_service, proxy_url,
                    proxy_connection, transfer, image_path=image_path,
                    transfer_size=transfer_size, pause=pause
                ), "Upload disk %s failed" % image_path
            else:
                logger.info(
                    "Starting disk %s upload - expected to fail", image_path
                )
                assert not self.upload_disk(
                    connection, transfer_service, proxy_url,
                    proxy_connection, transfer, image_path=image_path,
                    transfer_size=transfer_size, pause=pause
                ), "Upload disk %s succeeded" % image_path

        logger.info("Waiting for disk %s to go back to 'OK' state", image_id)
        ll_disks.wait_for_disks_status([image_id], key='id')

    def transfer_results(self, positive, results, disk_ids):
        """
        Deals with multi threading results objects due to transfer operation

        Args:
            positive (bool): True if we expect transfer to succeed
            results (list): The results objects list of the transfers threads
            disk_ids (list): The transfer disks/disks snapshot id list
        """

        if self.direction == DOWNLOAD:
            for index, result in enumerate(results):
                if result.exception() and positive is True:
                    raise result.exception()
                elif result.exception() and positive is False:
                    logger.info(
                        "Download disk id %s failed as expected %s",
                        disk_ids[index], result.exception()
                    )
                if not result.result and positive is True:
                    raise exceptions.DiskException(
                        "Download disk id %s failed", disk_ids[index]
                    )
                if not result.result and positive is False:
                    logger.info(
                        "Download disk id %s failed as expected %s",
                        disk_ids[index], result.exception()
                    )

                logger.info(
                    "Download disk id %s succeeded", disk_ids[index]
                )
        else:
            for index, result in enumerate(results):
                if result.exception() and positive is True:
                    raise result.exception()
                elif result.exception() and positive is False:
                    logger.info(
                        "Download disk id %s failed as expected with %s",
                        disk_ids[index], result.exception()
                    )
                if not result.result and positive is True:
                    raise exceptions.DiskException(
                        "Upload image id %s failed", disk_ids[index]
                    )
                elif not result.result and positive is False:
                    logger.info(
                        "Download disk id %s failed as expected",
                        disk_ids[index]
                    )

    def transfer_multiple_disks(
        self, disk_names=None, sizes_before=None, positive=True,
        snapshot=False, sdisk_objs=None, pause=False, interrupt=False,
        vm_name=None
    ):
        """
        Transfer multiple disk images in parallel

        Args:
            disk_names (list): list of disks names about to be transferred
            sizes_before (list): list of disks sizes about to be transferred
            positive (bool): True if transfer is expected to succeed, False
                otherwise
            snapshot (bool): True if we transfer disks of a specific snapshot
            sdisk_objs (list): Relevant snapshot disk objects list
            pause (bool): True performing pause during transfer,False otherwise
            interrupt (bool): True if additional action is planed during
                disk downlaod, False otherwise

        Returns:
            list: Output path list of the image location before/after transfer

        Raises:
            DiskException: If transfer fails
        """
        results = list()
        disk_ids = list()
        output_path = list()

        if self.direction == DOWNLOAD and snapshot is True:
            logger.info("Starting multi threaded snapshot disks downloads")
            with ThreadPoolExecutor(
                max_workers=len(sdisk_objs)
            ) as executor:
                for index, sdisk_obj in enumerate(sdisk_objs):
                    disk_ids.append(sdisk_obj.get_image_id())
                    output_path.append(FILE_PATH + '/' + sdisk_obj.get_alias())
                    self.check_disk_space_before_download_image(
                        image_size=sdisk_obj.get_provisioned_size()
                    )
                    testflow.step("Download image id %s", disk_ids[index])
                    results.append(
                        executor.submit(
                            self.transfer_image, disk_ids[index],
                            output_path[index], sizes_before[index],
                            positive=positive, snapshot=True,
                        )
                    )

        elif self.direction == DOWNLOAD:
            logger.info("Starting multi threaded disks downloads")
            with ThreadPoolExecutor(
                max_workers=len(disk_names)
            ) as executor:
                for index, disk in enumerate(disk_names):
                    disk_ids.append(ll_disks.get_disk_obj(disk).get_id())
                    output_path.append(FILE_PATH + '/' + disk)
                    self.check_disk_space_before_download_image(
                        disk_ids[index]
                    )
                    testflow.step("Download image id %s", disk_ids[index])
                    results.append(
                        executor.submit(
                            self.transfer_image, disk_ids[index],
                            output_path[index], sizes_before[index],
                            positive=positive, pause=pause,
                            interrupt=interrupt, vm_name=vm_name,
                            disk_name=disk
                        )
                    )
            self.transfer_results(positive, results, disk_ids)

        else:
            logger.info("Starting multi threaded disks uploads")
            with ThreadPoolExecutor(
                max_workers=len(disk_names)
            ) as executor:
                for index, disk in enumerate(disk_names):
                    disk_ids.append(ll_disks.get_disk_obj(disk).get_id())
                    output_path.append(UPLOAD_FILES_LOCALHOST[index])
                    testflow.step("Upload image id %s", disk_ids[index])
                    results.append(
                        executor.submit(
                            self.transfer_image, disk_ids[index],
                            output_path[index], sizes_before[index],
                            positive=positive, pause=pause
                        )
                    )
            self.transfer_results(positive, results, disk_ids)

        return output_path
