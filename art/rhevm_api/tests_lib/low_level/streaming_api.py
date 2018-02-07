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
)
from art.test_handler.settings import ART_CONFIG, GE
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
from time import sleep
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
UPLOAD_DIR_PATH = '~/upload/'
UPLOAD_FILES_LOCALHOST = [
    os.path.expanduser(
        UPLOAD_DIR_PATH + 'qcow2_v2_rhel7.4_ovirt4.2_guest_disk_1G'
    ),
    os.path.expanduser(UPLOAD_DIR_PATH + 'qcow2_v3_cow_sparse_disk_1G'),
    os.path.expanduser(UPLOAD_DIR_PATH + 'test_raw_to_delete')

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
COW_FORMAT = 'cow'
STATE_TIMEOUT = 60
PAUSE_SLEEP = 60
PAUSE_TRANSFER_PER = 50.00
PAUSED_USER = types.ImageTransferPhase.PAUSED_USER
RESUMING = types.ImageTransferPhase.RESUMING


class StreamingApi(object):
    """
    Represents an object with the ability to download or upload Red Hat
    Virtualization images (for example, virtual machine images) using the
    Red Hat Virtualization ImageIO API.
    """

    result = None

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
        host=None, storage_type=None, disk_object=None, sp_id=None,
        extend=False
    ):
        """
        Returns disk image size (in bytes) for download

        Args:
            host (host): Host resource object
            storage_type (str): Specify the storage type
            disk_object (Disk): The disk object
            sp_id (str): Storage pool id (only needed for File)
            extend (bool): True if image is extended,False otherwise

        Returns:
            int: Download size of a specific disk image in bytes
        """
        sd_id = (
            disk_object.get_storage_domains().get_storage_domain()[0].get_id()
        )
        if storage_type in [STORAGE_TYPE_ISCSI, STORAGE_TYPE_FCP]:
            if not extend or disk_object.get_format() != COW_FORMAT:
                transfer_size = disk_object.get_provisioned_size()
            else:
                transfer_size = disk_object.get_actual_size()
        else:
            cmd = shlex.split(
                HOST_IMAGE_FILE_SIZE_CMD % (
                    sp_id, sd_id, disk_object.get_id(),
                    disk_object.get_image_id()
                )
            )
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
        self, host=None, storage_type=None, disk_object=None, sp_id=None,
        image_path=None, extend=False
    ):
        """
        Returns disk image size (in bytes) for transfer(download/upload)

        Args:
            host (host): Host resource object
            storage_type (str): Specify the storage type
            disk_object (Disk): The disk id
            sp_id (str): Storage pool id (only needed for File)
            image_path (str): The upload file path
            extend (bool): True if disk is extended, False otherwise

        Returns:
            int: Transfer size of a specific disk image before download/upload
                in bytes

        """
        if not self.image_size:
            if self.direction == DOWNLOAD:
                transfer_size = self.image_size_for_download(
                    host=host, storage_type=storage_type,
                    disk_object=disk_object, sp_id=sp_id, extend=extend
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
        disk_id=None, file_path=FILE_PATH, image_size=None
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
    def md5sum_on_vdsm_host(
        host, storage_type=None, disk_object=None, sp_id=None
    ):
        """
        Returns the md5sum of a specific disk image on VDSM host

        Args:
            host (host): Host resource object
            storage_type (str): Specific the storage type
            disk_object (Disk): The disk id
            sp_id (str): Storage pool id (only needed for File)

        Returns:
            str: The md5sum of a specific disk image before download

        Raises:
            AssertionError: If any of the commands fails
        """
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
                MD5SUM_FILE_IMAGE_PATH % (
                    sp_id, sd_id, disk_object.get_id(), image_id
                )
            )
            rc, output, error = host.run_command(cmd)
            assert not rc, "Md5sum command %s failed %s" % (cmd, error)

        logger.info("Md5sum is: %s", shlex.split(output)[0])

        return shlex.split(output)[0]

    def prepare_for_transfer(self, image_id=None, snapshot=False):
        """
        Prepare for transfer and returns all needed services&arguments.

        This function initialize all needed services & arguments needed for
        transfer to accur which are:
        connection,system_service,transfer_service,transfer_headers,
        proxy_connection,proxy_url,disks_service

        Args:
            image_id (str): Id of the disk/snapshot disk
            snapshot (bool): True when transferring a disk snapshot

        Returns:
            list: Returns a list with all needed arguments for transfer
        """
        prepare_transfer_args = list()

        def get_connection():
            """
            Get the connection object to the server

            Returns:
                connection object: responsible for managing an HTTP connection
                    to the engine server
            """
            # Create the connection to the server:
            return sdk.Connection(
                url=ENGINE_URL,
                username=ADMIN_USER_NAME,
                password=ORIG_VDC_PASSWORD,
                ca_file=CA_FILE_PATH,
                debug=True,
                log=logger,
            )

        def get_disk_service(connection):
            """
            Get the disks service object that reference to the service that
                manages the disks available in the storage domain.

            Args:
                connection (Connection): Object responsible for managing an
                    HTTP connection to the engine server

            Returns:
                Service: disk service object
            """
            disks_service = connection.system_service().disks_service()
            return disks_service.disk_service(image_id)

        def get_disk(disk_service):
            """
            Get the object that reference to the service that manages a
                specific disk.

            Args:
                disk_service (Service): The object responsible for managing a
                    specific disk

            Returns:
                Service: object that manages a specific disk
            """
            return disk_service.get()

        def get_transfer_service(
            image_id, disk=None, snapshot=False, system_service=None
        ):
            """
            Get the reference to the service that manages the image transfer

            Args:
                image_id (str): Id of the disk/snapshot disk image
                disk (Disk): disk object from the disk service object
                snapshot (bool): True if transfer is for a disk snapshot
                system_service (Service): system_service object is the
                    reference to the root of the services

            Returns:
                Service: ImageTransferService object
            """
            transfers_service = system_service.image_transfers_service()

            # Add a new image transfer:
            if self.direction == DOWNLOAD and snapshot is True:
                transfer = transfers_service.add(
                    types.ImageTransfer(
                        snapshot=types.DiskSnapshot(id=image_id),
                        direction=types.ImageTransferDirection.DOWNLOAD,
                    )
                )

            elif self.direction == DOWNLOAD:
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

            # Get reference to the created transfer service:
            transfer_service = transfers_service.image_transfer_service(
                transfer.id
            )
            while transfer.phase == types.ImageTransferPhase.INITIALIZING:
                time.sleep(1)
                transfer = transfer_service.get()

            # After adding a new transfer for the disk, the transfer's status
            # will be INITIALIZING. Wait until the init phase is over.
            # The actual transfer can start when its status is "Transferring".
            init_phase_time = 0
            while transfer.phase == types.ImageTransferPhase.INITIALIZING:
                time.sleep(1)
                init_phase_time += 1
                assert (
                    init_phase_time == TRANSFER_INITIALIZING_STATE_TIMEOUT
                ), (
                    "Transfer status is in init state for %s seconds" %
                    TRANSFER_INITIALIZING_STATE_TIMEOUT
                )
                transfer = transfer_service.get()

            return transfer_service

        def get_proxy_connection(proxy_url):
            """
            Returns the proxy_connection connection object which create a new
                HTTPS connection to the proxy server

            At this stage, the SDK granted the permission to start
            transferring the disk, and the user should choose its preferred
            tool for doing it - regardless of the SDK.
            In this example, we will use Python's httplib.HTTPSConnection
            for transferring the data.

            Args:
                proxy_url (str): The address of a proxy server to the image

             Returns:
                HTTPConnection: returns a new HTTPS connection object
                  to the proxy server
            """

            context = ssl.create_default_context()

            # Note that ovirt-imageio-proxy by default checks the certificates,
            #  so if you don't have your CA certificate of the engine in the
            # system, you need to pass it to HTTPSConnection.
            context.load_verify_locations(cafile=CA_FILE_PATH)

            return HTTPSConnection(
                proxy_url.hostname,
                proxy_url.port,
                context=context,
            )

        # Create a connection to the server:
        connection = get_connection()
        prepare_transfer_args.append(connection)

        # Get reference to the created transfer service:
        system_service = connection.system_service()
        logger.info(
            "Get the reference to the root service %s", system_service
        )
        if not snapshot:
            disk_service = get_disk_service(connection)
            disk = get_disk(disk_service)
            transfer_service = get_transfer_service(
                image_id, disk=disk, system_service=system_service
            )
        else:
            transfer_service = get_transfer_service(
                image_id, snapshot=snapshot, system_service=system_service
            )

        prepare_transfer_args.append(transfer_service)

        transfer = transfer_service.get()

        if self.direction == DOWNLOAD:
            # Set needed headers for downloading:
            transfer_headers = {
                'Authorization': transfer.signed_ticket,
            }
        else:
            transfer_headers = None

        prepare_transfer_args.append(transfer_headers)
        proxy_url = urlparse(transfer.proxy_url)
        prepare_transfer_args.append(proxy_url)
        proxy_connection = get_proxy_connection(proxy_url)
        prepare_transfer_args.append(proxy_connection)
        prepare_transfer_args.append(transfer)

        return prepare_transfer_args

    @staticmethod
    def check_for_timeout(start_time, state):
        """
        If the time it took to change to the required state took more than the
            designated timeout fail the test

        Args:
            start_time (float): Start time in seconds of an operation like
                pause or resume image transfer
            state (str): State of the the transfer_service object like
                "paused_user" or "resuming"

        """
        now = time.time()
        assert now - start_time < STATE_TIMEOUT, (
            "Waiting for %s state for more than %s seconds" % (
                state, STATE_TIMEOUT
            )
        )

    def resume(self, transfer_service, image_indicator=None):
        """
        Perform resume after disks have been paused

        Args:
            transfer_service (Service): Get a reference to the service that
                manages the image transfer that was added in the previous
            image_indicator (str): For download its the id of the disk image,
                for upload its the image location on the local host
        """

        # Resume disk transfer
        logger.info("Resume transfer on image %s" % image_indicator)
        start = time.time()
        transfer = transfer_service.get()
        transfer_service.resume()
        # Check the transfer phase until it changes to "resuming"
        while transfer.phase == RESUMING:
            time.sleep(1)
            transfer = transfer_service.get()
            logger.info(
                "Image %s is in phase %s", image_indicator,
                transfer.phase
            )
            self.check_for_timeout(start, RESUMING)

    def pause(
        self, transfer_service, pos=None, size=None, image_indicator=None
    ):

        """
        Perform pause during disks transfer

        Args:
            transfer_service (Service): Get a reference to the service that
                manages the image transfer that was added in the previous
            pos (int): The position in bytes of the current disk transfer
            size (int): Actual size of the transferred image in bytes
            image_indicator (str): For download its the id of the disk image,
                for upload its the image location on the local host
        """
        logger.info("Pause transfer on image %s", image_indicator)
        transfer_service.pause()
        start = time.time()
        transfer = transfer_service.get()
        # Check the transfer phase until it changes to "paused_user"
        while transfer.phase != PAUSED_USER:
            time.sleep(1)
            logger.info(
                "Current Image %s transfer phase is not paused_user yet "
                "but in phase: %s", image_indicator, transfer.phase
            )
            transfer = transfer_service.get()
            if transfer.phase == PAUSED_USER:
                logger.info(
                    "Image %s phase is %s", image_indicator, transfer.phase
                )
                break
            self.check_for_timeout(start, PAUSED_USER)
        # Now that disk transfer is paused , sleep for a while , in this
        # case for PAUSE_SLEEP
        logger.info("Sleeping for 1min on image %s", image_indicator)
        sleep(PAUSE_SLEEP)

    def download_disk(
        self, connection=None, transfer_service=None, transfer_headers=None,
        proxy_url=None, proxy_connection=None, image_path=None,
        transfer_size=None, image_id=None, pause=False, interrupt=False,
        vm_name=None, disk_name=None
    ):
        """
        Download disk from VDSM host to localhost running the test

        Args:

            connection (Connection): Object responsible for managing an HTTP
                connection to the engine server
            transfer_service (Service): Get a reference to the service that
                manages the image transfer that was added in the previous
            transfer_headers(dict): Set needed headers for transfer disk image
            proxy_url (str): The address of a proxy server to the image
            proxy_connection(HTTPConnection): Create new HTTPS connection to
                the proxy server
            image_path (str): Image location before transfer on localhost
            transfer_size (int): Actual size of the transferred image in bytes
            image_id (str): Id of the disk image
            pause (bool): True performing pause during transfer,False otherwise
            interrupt (bool): True if additional action is planed during
                 disk download, False otherwise
            vm_name (string): Name of the VM
            disk_name (string): Name of the transferred disk

         Returns:
            bool: True if download succeeded False if failed
        """
        status = True

        try:
            path = image_path

            with open(path, "wb") as mydisk:
                size = transfer_size
                logger.info("Provisioned size: %s", size)
                chunk_size = 64 * 1024 * 1024
                pos = 0
                while pos < size:
                    completed_transfer_per = pos / float(size) * 100
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
                        status = False
                        break

                    # Write the content to file:
                    mydisk.write(r.read())
                    logger.info("Completed: %s%% on disk id %s", int(
                        completed_transfer_per), image_id)

                    if pause and completed_transfer_per == PAUSE_TRANSFER_PER:
                        self.pause(
                            transfer_service, pos=pos, size=size,
                            image_indicator=image_id
                        )
                        self.resume(transfer_service, image_indicator=image_id)

                    if interrupt:
                        if int(completed_transfer_per) == 50:
                            logger.info(
                                "Start additonal action during transfer on "
                                "disk %s", disk_name
                            )
                            logger.info(
                                "Attaching disk %s to vm %s", disk_name,
                                vm_name
                            )
                            assert ll_disks.attachDisk(
                                positive=False, alias=disk_name,
                                vm_name=vm_name
                            ), (
                                "Succeeded to attach disk %s to vm %s during "
                                "download , attach should fail"
                                % (disk_name, vm_name)
                            )

                    # Continue to next chunk.
                    pos += chunk_size

        finally:
            # Finalize the session.
            transfer_service.finalize()
            # Close the connection to the server:
            connection.close()
        return status

    @staticmethod
    def download_disk_snapshot(
        connection=None, transfer_service=None, proxy_url=None,
        proxy_connection=None, image_path=None, image_id=None
    ):
        """
        Download disk snapshot from VDSM host to localhost running the test

        Args:
            connection (Connection): Object responsible for managing an HTTP
                connection to the engine server
            transfer_service (Service): Get a reference to the service that
                manages the image transfer that was added in the previous
            proxy_url (str): The address of a proxy server to the image
            proxy_connection (HTTPConnection): Create new HTTPS connection
                object to connect to the proxy server
            image_path (str): Image location before transfer on localhost
            image_id (str): Id of the disk snapshot

         Returns:
            bool: True if disk snapshot download succeeded False if failed
        """

        logger.info("Downloading disk snapshot id %s" % image_id)

        status = True

        try:
            transfer_service = transfer_service
            transfer = transfer_service.get()
            proxy_url = proxy_url
            proxy_connection = proxy_connection
            path = image_path

            with open(path, "wb") as mydisk:
                # Set needed headers for downloading:
                transfer_headers = {
                    'Authorization': transfer.signed_ticket,
                }

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
                    logger.info("Error: %s" % r.read())
                    status = False

                bytes_to_read = int(r.getheader('Content-Length'))
                chunk_size = 64 * 1024 * 1024

                logger.info(
                    "Disk snapshot size: %s bytes" % str(bytes_to_read)
                )

                while bytes_to_read > 0:
                    # Calculate next chunk to read
                    to_read = min(bytes_to_read, chunk_size)

                    # Read next chunk
                    chunk = r.read(to_read)

                    if chunk == "":
                        status = False
                        logger.error("Socket disconnected")
                        break

                    # Write the content to file:
                    mydisk.write(chunk)

                    # Update bytes_to_read
                    bytes_to_read -= len(chunk)

                    completed = 1 - (
                        bytes_to_read / float(r.getheader('Content-Length'))
                    )

                    logger.info("Completed: %s%% disk snapshot id %s", int(
                        completed * 100), image_id)
        finally:
            # Finalize the session.
            if transfer_service is not None:
                transfer_service.finalize()
            # Close the connection to the server:
            connection.close()

        return status

    def upload_disk(
        self, connection=None, transfer_service=None, proxy_url=None,
        proxy_connection=None, transfer=None, image_path=None,
        transfer_size=None, pause=False
    ):
        """
        Upload disk from localhost to a VDSM host

        Args:

            connection (Connection): Object responsible for managing an HTTP
                connection to the engine server
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
            pause (bool): True performing pause during transfer,False otherwise

         Returns:
            bool: True if upload succeeded False if failed

        """
        size = transfer_size
        path = image_path
        start = last_progress = last_extend = time.time()
        status = True

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
                completed_transfer_per = pos / float(size) * 100
                # Extend the transfer session once per minute.
                now = time.time()

                # Report progress every 10 seconds
                if now - last_progress > 10:
                    logger.info(
                        "Uploaded %.2f%%" % completed_transfer_per
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
                    logger.error("Unexpected end of file at pos=%d" % pos)
                    return False

                proxy_connection.send(chunk)
                pos += len(chunk)

                if pause and completed_transfer_per == PAUSE_TRANSFER_PER:
                    self.pause(
                        transfer_service, pos=pos, size=size,
                        image_indicator=image_path
                    )
                    self.resume(transfer_service, image_indicator=image_path)

        # Get the response
        response = proxy_connection.getresponse()
        if response.status != 200:
            status = False
            transfer_service.pause()
            logger.error(
                "Upload failed: %s %s" % (response.status, response.reason)
            )

        # Successful cleanup
        transfer_service.finalize()
        connection.close()

        elapsed = time.time() - start
        logger.info(
            "Uploaded %.2fg in %.2f seconds %.2fm/s",
            size / float(1024 ** 3), elapsed, size / 1024 ** 2 / elapsed
        )
        return status
