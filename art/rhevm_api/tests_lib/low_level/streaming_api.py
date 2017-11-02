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
import time
from httplib import HTTPSConnection
from urlparse import urlparse
import logging
import os
logger = logging.getLogger(__name__)


ENUMS = ART_CONFIG['elements_conf']['RHEVM Enums']
STORAGE_TYPE_NFS = ENUMS['storage_type_nfs']
STORAGE_TYPE_ISCSI = ENUMS['storage_type_iscsi']
STORAGE_TYPE_FCP = ENUMS['storage_type_fcp']
STORAGE_TYPE_CEPH = ENUMS['storage_type_ceph']
ENGINE_URL = GE['api_url']
ADMIN_USER_NAME = GE['username']
ORIG_VDC_PASSWORD = GE['password']
CA_FILE = "ca.crt"
WORKSPACE_PATH = os.getenv('WORKSPACE', '~/')
CA_FILE_PATH = os.path.expanduser(os.path.join(WORKSPACE_PATH, CA_FILE))
FILE_PATH = os.path.expanduser('~')
UPLOAD_FILES_LOCALHOST = [
    os.path.expanduser('~/qcow2_v2_rhel7.4_ovirt4.2_guest_disk_1G'),
    os.path.expanduser('~/qcow2_v3_cow_sparse_disk_1G'),
    os.path.expanduser('~/test_raw_to_delete')

]
MD5SUM_BLOCK_IMAGE_PATH = 'md5sum /dev/%s/%s'
MD5SUM_FILE_IMAGE_PATH = 'md5sum /rhev/data-center/%s/%s/images/%s/%s'
DISK_SPACE_CMD = 'df -B1 %s'
LV_CHANGE_CMD = 'lvchange -a %s %s/%s'
HOST_IMAGE_FILE_SIZE_CMD = 'ls -l /rhev/data-center/%s/%s/images/%s/%s'
LOCAL_IMAGE_FILE_SIZE_CMD = 'ls -l %s'
TRANSFER_INITIALIZING_STATE_TIMEOUT = 300
DOWNLOAD = 'download'
UPLOAD = 'upload'


class StreamingApi(object):
    """
    Represents an object with the ability to download or upload Red Hat
    Virtualization images (for example, virtual machine images) using the
    Red Hat Virtualization ImageIO API.
    """

    def __init__(self, image_path, image_size, direction):
        """
        Args:
        image_path (str): Image source/target path for upload/download on
            localhost
        image_size (int): Image size in bytes
        direction (str): Direction of image transfer download/upload
        """
        self._image_path = image_path
        self._image_size = image_size
        self._direction = direction

    @property
    def image_path(self):
        return self._image_path

    @property
    def image_size(self):
        return self._image_size

    @property
    def direction(self):
        return self._direction

    @staticmethod
    def image_size_for_download(
        host=None, storage_type=None, disk_id=None, sp_id=None
    ):
        """
        Returns disk image size (in bytes) for download

        Args:
            host (host): Host resource object
            storage_type (str): Specify the storage type
            disk_id (str): The disk id
            sp_id (str): Storage pool id (only needed for File)

        Returns:
            int: Download size of a specific disk image in bytes
        """
        disk_object = ll_disks.get_disk_obj(disk_id, attribute='id')
        image_id = disk_object.get_image_id()
        sd_id = (
            disk_object.get_storage_domains().get_storage_domain()[0].
            get_id()
        )
        if storage_type in [STORAGE_TYPE_ISCSI or STORAGE_TYPE_FCP]:
            transfer_size = ll_disks.get_disk_obj(
                disk_id, attribute='id'
            ).get_provisioned_size()

        else:
            cmd = shlex.split(HOST_IMAGE_FILE_SIZE_CMD % (
                    sp_id, sd_id, disk_id, image_id
                ))
            rc, output, error = host.run_command(cmd)
            assert not rc, "Size command %s failed with error %s" % (
                cmd, error
            )
            transfer_size = int(shlex.split(output)[4])

        return transfer_size

    @staticmethod
    def image_size_for_upload(image_path=None):
        """
        Returns disk image size (in bytes) for upload

        Args:
            image_path (str): The upload file path

        Returns:
            int: Upload size of a specific disk image in bytes
        """
        cmd = LOCAL_IMAGE_FILE_SIZE_CMD % image_path
        output, err = Popen(
            shlex.split(cmd), stdout=PIPE, stderr=PIPE
        ).communicate()
        assert not err, (
            "Error %s occurred when trying to execute the command %s"
            % (cmd, err)
        )
        return int(shlex.split(output)[4])

    def image_size_for_transfer(
        self, host=None, storage_type=None, disk_id=None, sp_id=None,
        image_path=None
    ):
        """
        Returns disk image size (in bytes) for transfer(download/upload)

        Args:
            host (host): Host resource object
            storage_type (str): Specify the storage type
            disk_id (str): The disk id
            sp_id (str): Storage pool id (only needed for File)
            image_path (str): The upload file path

        Returns:
            int: Transfer size of a specific disk image before download/upload
                in bytes

        """
        if not self.image_size:
            if self.direction == DOWNLOAD:
                transfer_size = self.image_size_for_download(
                    host=host, storage_type=storage_type, disk_id=disk_id,
                    sp_id=sp_id
                )
            else:
                transfer_size = self.image_size_for_upload(
                    image_path=image_path
                )
        else:
            transfer_size = self.image_size

        logger.info("Image size is: %s bytes", transfer_size)
        return transfer_size

    @staticmethod
    def check_disk_space_before_download_image(
        disk_id, file_path=FILE_PATH, image_size=None
    ):
        """
        Check available disk space at the target directory before download.
        If there is not enough space assert .

        Args:
            disk_id (str): Disk id
            file_path (str): The target file's path
            image_size (int): The size of the image in bytes

        Raises:
            AssertionError: If there is not enough space to download the file
        """

        if not image_size:
            image_size = ll_disks.get_disk_obj(
                disk_id, attribute='id'
            ).get_provisioned_size()
        cmd = shlex.split(DISK_SPACE_CMD % file_path)
        output, err = Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()
        assert not err, (
            "Error %s occurred when trying to execute command %s" % (err, cmd)
        )
        available_space_size = shlex.split(output)[10]

        assert image_size < available_space_size, (
            "Not enough space for source image in target directory %s \n"
            "Available space size: %s \n Image size: %s \n" % (
                available_space_size, image_size, FILE_PATH
            )
        )

    @staticmethod
    def md5sum_on_localhost(image_path=image_path):
        """
        Returns the md5sum of a specific disk before/after transfer

        Args:
            image_path (str): The path of image on the local host before
                upload/ after download

        Returns:
            str: The md5sum of a specific disk image before upload/ after
                download

        Raises:
            AssertionError: If md5sum command on local host fails
        """
        cmd = shlex.split('md5sum ' + image_path)
        out, err = Popen(
            cmd, stdout=PIPE, stderr=PIPE
        ).communicate()
        assert not err, (
            "Error %s occurred when trying to execute the command %s" % (
                err, cmd
            )
        )
        logger.info("Md5sum is: %s", shlex.split(out)[0])

        return shlex.split(out)[0]

    @staticmethod
    def md5sum_on_vdsm_host(host, storage_type=None, disk_id=None, sp_id=None):
        """
        Returns the md5sum of a specific disk image on VDSM host

        Args:
            host (host): Host resource object
            storage_type (str): Specific the storage type
            disk_id (str): The disk id
            sp_id (str): Storage pool id (only needed for File)

        Returns:
            str: The md5sum of a specific disk image before download

        Raises:
            AssertionError: If any of the commands fails
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
                "Unable to refresh the physical volumes on host '%s'" % (
                    host
                )
            )
            assert host.lvm.lvchange(sd_id, image_id, activate=True), (
                "Unable to activate the disk LV"
            )
            rc, output, error = host.run_command(
                shlex.split(MD5SUM_BLOCK_IMAGE_PATH % (sd_id, image_id))
            )
            assert not rc, "Md5sum command failed %s" % error
            assert host.lvm.lvchange(sd_id, image_id, activate=False), (
                "Unable to deactivate the disk LV %s" % image_id
            )

        else:
            cmd = shlex.split(
                MD5SUM_FILE_IMAGE_PATH % (sp_id, sd_id, disk_id, image_id)
            )
            rc, output, error = host.run_command(cmd)
            assert not rc, "Md5sum command %s failed %s" % (cmd, error)

        logger.info("Md5sum is: %s", shlex.split(output)[0])

        return shlex.split(output)[0]

    def md5sum_before_transfer(
        self, host=None, storage_type=None, disk_id=None, sp_id=None,
        image_path=image_path
    ):
        """
        Returns the md5sum of a specific disk before transfer(download/upload)
        Download direction- ms5sum before transfer will be on VDSM host
        Upload direction - ms5sum before transfer will be on localhost

        Args:
            host (host): Host resource object
            storage_type (str): Specific the storage type
            disk_id (str): The disk id
            sp_id (str): Storage pool id (only needed for File)
            image_path (str): Path of the transferred image on the local host

        Returns:
            str: The md5sum of a specific disk image before transfer

        """
        if self.direction == DOWNLOAD:
            out = self.md5sum_on_vdsm_host(host, storage_type, disk_id, sp_id)
        else:
            out = self.md5sum_on_localhost(image_path)

        return out

    def md5sum_after_transfer(
        self, host=None, storage_type=None, disk_id=None, sp_id=None,
        image_path=image_path
    ):
        """
        Returns the md5sum output of a specific disk after image transfer
        Download direction- ms5sum after transfer will be on localhost
        Upload direction - ms5sum before transfer will be on VDSM host

        Args:
            host (host): Host resource object
            storage_type (str): Specific the storage type
            disk_id (str): The disk id
            sp_id (str): Storage pool id (only needed for File)
            image_path (str): Path of the transferred image on the local host

        Returns:
            str: The md5sum of the image after transfer

        """
        if self.direction == UPLOAD:
            out = self.md5sum_on_vdsm_host(host, storage_type, disk_id, sp_id)
        else:
            out = self.md5sum_on_localhost(image_path)

        return out

    def md5sums_sizes_before_transfer(
        self, host=None, storage_type=None, disks_names=None, sp_id=None,
        image_paths=UPLOAD_FILES_LOCALHOST
    ):
        """
        Returns the md5sums and sizes of selected disks before image transfer

        Args:
            host (host): Host resource object
            storage_type (str): Specify the storage type
            disks_names (list): Disks names about to be downloaded
            sp_id (str): Storage pool id (only needed for File)
            image_paths (list): Upload image paths on local host

        Returns:
            list: lists of md5sums and sizes of selected disks before download

        """

        if self.direction == DOWNLOAD:
            md5sums_before = [self.md5sum_before_transfer(
                host, storage_type, ll_disks.get_disk_obj(disk).get_id(),
                sp_id
            ) for disk in disks_names]
            sizes_before = [self.image_size_for_transfer(
                host, storage_type, ll_disks.get_disk_obj(disk).get_id(),
                sp_id
            ) for disk in disks_names]

        else:
            md5sums_before = [
                self.md5sum_before_transfer(image_path=path)
                for path in image_paths
            ]
            sizes_before = [
                self.image_size_for_transfer(image_path=path)
                for path in image_paths
            ]

        return md5sums_before, sizes_before

    def compare_md5sum_before_after_transfer(
        self, md5sum_before, output=image_path, host=None, storage_type=None,
        disk_id=None, sp_id=None
    ):
        """
        Compare md5sum before and after image transfer

        Args:
            md5sum_before (str): The md5sum value fo the disk before download
            output (str): Output path of the downloaded file
            host (host): Host resource object
            storage_type (str): Specific the storage type
            disk_id (str): The disk id
            sp_id (str): Storage pool id (only needed for File)


        Raises:
            AssertionError: if md5sum is not the same before and after the
                download
        """
        if self.direction == DOWNLOAD:
            md5sum_after = self.md5sum_after_transfer(image_path=output)
        else:
            md5sum_after = self.md5sum_after_transfer(
                host, storage_type, disk_id, sp_id
            )

        assert md5sum_before == md5sum_after, (
            "Md5sum not the same before transfer is: %s and after its: %s" % (
                md5sum_before, md5sum_after
            )
        )
        logger.info("Md5sum comparison before and after transfer successful")

    def prepare_for_transfer(self, image_id):
        """
        Prepare for transfer and returns all needed services&arguments.

        This function initialize all needed services & arguments needed for
        transfer to accur which are:
        connection,system_service,transfer_service,transfer_headers,
        proxy_connection,proxy_url,disks_service

        Args:
            image_id (str): Id of the disk image

        Returns:
            list: Returns a list with all needed arguments for transfer
        """
        prepare_transfer_args = list()
        # Create the connection to the server:
        connection = sdk.Connection(
            url=ENGINE_URL,
            username=ADMIN_USER_NAME,
            password=ORIG_VDC_PASSWORD,
            ca_file=CA_FILE_PATH,
            debug=True,
            log=logger,
        )
        prepare_transfer_args.append(connection)
        # Get reference to the created transfer service:
        system_service = connection.system_service()
        logger.info(
            "Get the reference to the root service %s", system_service
        )

        # Get the reference to the disks service:
        disks_service = connection.system_service().disks_service()

        logger.info(
            "Get the reference to the disks service %s", disks_service
        )
        disk_service = disks_service.disk_service(image_id)
        disk = disk_service.get()

        # Get a reference to the service that manages the image
        # transfer that was added in the previous step:
        transfers_service = system_service.image_transfers_service()

        # Add a new image transfer:
        if self.direction == DOWNLOAD:
            transfer = transfers_service.add(
                types.ImageTransfer(
                    image=types.Image(
                        id=disk.id
                    ),
                    direction=types.ImageTransferDirection.DOWNLOAD,
                )
            )

        else:
            transfer = transfers_service.add(
                types.ImageTransfer(
                    image=types.Image(
                        id=disk.id
                    ),
                )
            )
        transfer_service = transfers_service.image_transfer_service(
            transfer.id
        )

        prepare_transfer_args.append(transfer_service)

        # After adding a new transfer for the disk, the transfer's status
        # will be INITIALIZING. Wait until the init phase is over.
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

        if self.direction == DOWNLOAD:
            # Set needed headers for downloading:
            transfer_headers = {
                'Authorization': transfer.signed_ticket,
            }
        else:
            transfer_headers = None
        prepare_transfer_args.append(transfer_headers)

        # At this stage, the SDK granted the permission to start
        # transferring the disk, and the user should choose its preferred
        # tool for doing it regardless of the SDK . In this example, we
        # will use Python's httplib.HTTPSConnection for transferring the
        # data.
        proxy_url = urlparse(transfer.proxy_url)
        context = ssl.create_default_context()
        prepare_transfer_args.append(proxy_url)

        # Note that ovirt-imageio-proxy by default checks the certificates,
        # so if you don't have your CA certificate of the engine in the
        # system, you need to pass it to HTTPSConnection.
        context.load_verify_locations(cafile=CA_FILE_PATH)

        proxy_connection = HTTPSConnection(
            proxy_url.hostname,
            proxy_url.port,
            context=context,
        )
        prepare_transfer_args.append(proxy_connection)
        prepare_transfer_args.append(transfer)

        return prepare_transfer_args

    @staticmethod
    def download_disk(
        connection=None, transfer_service=None, transfer_headers=None,
        proxy_url=None, proxy_connection=None, image_path=None,
        transfer_size=None, image_id=None,
    ):
        """
        Download disk from VDSM host to localhost running the test

        Args:

            connection (object): responsible for managing an HTTP connection to
                the engine server
            transfer_service (Service): Get a reference to the service that
                manages the image transfer that was added in the previous
            transfer_headers(dict): Set needed headers for transfer disk image
            proxy_url(str): The address of a proxy server to the image
            proxy_connection(HTTPConnection): Create new HTTPS connection to
                the proxy server
            image_path (str): Image location before transfer on localhost
            transfer_size (int): Actual size of the transferred image in bytes
            image_id (str): Id of the disk image

        """
        try:
            path = image_path
            mib_per_request = 1

            with open(path, "wb") as mydisk:
                size = transfer_size
                logger.info("Provisioned size: %s", size)
                chunk_size = 1024 * 1024 * mib_per_request
                pos = 0
                while pos < size:
                    # Extend the transfer session.
                    transfer_service.extend()
                    # Set the range, according to the downloaded chunk .
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
                        pos / float(size) * 100), image_id)
                    # Continue to next chunk.
                    pos += chunk_size
        finally:
            # Finalize the session.
            transfer_service.finalize()
            # Close the connection to the server:
            connection.close()

    @staticmethod
    def upload_disk(
        connection=None, transfer_service=None, proxy_url=None,
        proxy_connection=None, transfer=None, image_path=None,
        transfer_size=None
    ):
        """
        Upload disk from localhost to a VDSM host

        Args:

            connection (object): responsible for managing an HTTP connection to
                the engine server
            transfer_service (Service): Get a reference to the service that
                manages the image transfer that was added in the previous
            proxy_url (str): The address of a proxy server to the image
            proxy_connection (HTTPConnection): Create new HTTPS connection to
                the proxy server
            transfer (Service) : Create a transfer by using
                <<services/image_transfers/methods/add, add>> of the
                <<services/image_transfers>> service, stating the image
                to transfer data to/from
            image_path (str): Image location before transfer on localhost
            transfer_size (int): Actual size of the transferred image in bytes
        """
        size = transfer_size
        path = image_path
        start = last_progress = last_extend = time.time()

        # This seems to give the best throughput when uploading
        # SSD to a server that drop the data.
        # You may need to tune this on your setup.
        buf_size = 128 * 1024

        # Send the request head. Note the following:
        # - We must send the Authorzation header with the signed
        # ticket received from the transfer service.
        # - the server requires Content-Range header even when
        # sending the entire file.
        # - the server requires also Content-Length.

        proxy_connection.putrequest("PUT", proxy_url.path)
        proxy_connection.putheader(
            'Authorization', transfer.signed_ticket
        )
        proxy_connection.putheader(
            'Content-Range', "bytes %d-%d/%d" % (
                0, size - 1, size)
        )
        proxy_connection.putheader('Content-Length',
                                   "%d" % (size,))
        proxy_connection.endheaders()

        with open(path, "rb") as disk:
            pos = 0
            while pos < size:
                # Extend the transfer session once per minute.
                now = time.time()

                # Report progress every 10 seconds
                if now - last_progress > 10:
                    logger.info(
                        "Uploaded %.2f%%" % (float(pos) / size * 100)
                    )
                    last_progress = now

                # Extend the transfer session once per minute.
                if now - last_extend > 60:
                    transfer_service.extend()
                    last_extend = now

                to_read = min(size - pos, buf_size)
                chunk = disk.read(to_read)
                if not chunk:
                    transfer_service.pause()
                    raise RuntimeError(
                        "Unexpected end of file at pos=%d" % pos)

                proxy_connection.send(chunk)
                pos += len(chunk)

        # Get the response
        response = proxy_connection.getresponse()
        if response.status != 200:
            transfer_service.pause()
            assert True, "Upload failed: %s %s" % (
                response.status, response.reason
            )
        # Successful cleanup
        transfer_service.finalize()
        connection.close()

        elapsed = time.time() - start
        logger.info(
            "Uploaded %.2fg in %.2f seconds %.2fm/s",
            size / float(1024 ** 3), elapsed, size / 1024 ** 2 / elapsed
        )

    def transfer_image(
        self, image_id, image_path=image_path, transfer_size=image_size,
    ):
        """
        Transfer disk image

        Args:
            image_id (str): Id of the disk image
            image_path (str): Image location before transfer on localhost
            transfer_size (int): Actual size of the transferred image in bytes
        """
        (
            connection, transfer_service, transfer_headers,
            proxy_url, proxy_connection, transfer
        ) = self.prepare_for_transfer(image_id)

        if self.direction == DOWNLOAD:
            self.download_disk(
                connection, transfer_service, transfer_headers, proxy_url,
                proxy_connection, image_path=image_path,
                transfer_size=transfer_size, image_id=image_id
            )
        else:
            self.upload_disk(
                connection, transfer_service, proxy_url,
                proxy_connection, transfer, image_path=image_path,
                transfer_size=transfer_size
            )

        logger.info("Waiting for disk %s to go back to 'OK' state", image_id)
        ll_disks.wait_for_disks_status([image_id], key='id')

    def transfer_multiple_disks(self, disks_names, sizes_before):
        """
        Transfer multiple disk images in parallel

        Args:
            disks_names (list): list of disks names about to be transferred
            sizes_before (list): list of disks sizes about to be transferred

        Returns:
            list: Output path list of the image location before/after transfer

        Raises:
            DiskException: If download fails
        """
        results = list()
        disk_ids = list()
        output_path = list()

        if self.direction == DOWNLOAD:
            with ThreadPoolExecutor(
                max_workers=len(disks_names)
            ) as executor:
                for index, disk in enumerate(disks_names):
                    disk_ids.append(ll_disks.get_disk_obj(disk).get_id())
                    output_path.append(FILE_PATH + '/' + disk)
                    self.check_disk_space_before_download_image(
                        disk_ids[index]
                    )
                    testflow.step("Download image id %s", disk_ids[index])
                    results.append(
                        executor.submit(
                            self.transfer_image, disk_ids[index],
                            output_path[index], sizes_before[index]
                        )
                    )
            for index, result in enumerate(results):
                if result.exception():
                    raise result.exception()
                if not result.result:
                    raise exceptions.DiskException(
                        "Download disk id %s failed", disk_ids[index]
                    )
                logger.info(
                    "Download disk id %s succeeded", disk_ids[index]
                )
        else:
            with ThreadPoolExecutor(
                max_workers=len(disks_names)
            ) as executor:
                for index, disk in enumerate(disks_names):
                    disk_ids.append(ll_disks.get_disk_obj(disk).get_id())
                    output_path.append(UPLOAD_FILES_LOCALHOST[index])
                    testflow.step("Upload image id %s", disk_ids[index])
                    results.append(
                        executor.submit(
                            self.transfer_image, disk_ids[index],
                            output_path[index], sizes_before[index]
                        )
                    )
            for index, result in enumerate(results):
                if result.exception():
                    raise result.exception()
                if not result.result:
                    raise exceptions.DiskException(
                        "Upload image id %s failed", disk_ids[index]
                    )

        return output_path
