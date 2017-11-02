import config
import pytest
import shlex
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_dc,
    hosts as ll_hosts,
    storagedomains as ll_sd,
    disks as ll_disks,
)
from art.unittest_lib import testflow
from rhevmtests import helpers as rhevm_helpers
from rhevmtests.storage import helpers as storage_helpers
from subprocess import Popen, PIPE
from rhevmtests.storage.config import *  # flake8: noqa
import pexpect
from _pytest_art.ssl import configure

logger = logging.getLogger(__name__)

DISK_SIZE = 10 * GB
DISK_ALLOCATIONS = [
    ('qcow2_v2', True, 'thin'),
    ('qcow2_v3', True, 'thin'),
    ('raw', False, 'preallocated')
]


@pytest.fixture(scope='module', autouse=True)
def create_certificate_for_test(request):
    """
    Create ssl certificate needed for upload/download image and move it to a
    non shares location
    """
    testflow.setup("Create ssl certificate %s", config.CA_FILE_ORIG)
    configure()
    testflow.setup(
        "Moving ssl certificate to a non shares path %s", config.CA_FILE_NEW
    )
    # Moving the certificate location to a non shared location as flow node
    # certificate is created on the same location for all runs and therefor
    # overridden by parallel jenkins runs will cause test failures in https
    cmd = shlex.split(
        config.COPY_CERT_CMD % (config.CA_FILE_ORIG, config.CA_FILE_NEW)
    )
    output, err = Popen(cmd, stdout=PIPE, stderr=PIPE).communicate()
    assert not err, (
        "Error %s occurred when trying to execute command %s" % (err, cmd)
    )


@pytest.fixture(scope='module', autouse=True)
def copy_images_for_upload(request):
    """
    Copy upload images to localhost needed for the upload test plan only if
    they do not exist on localhost
    """
    upload_file_names = [
        config.UPLOAD_FILES_LOCALHOST_PATH[index].split('/')[-1]
        for index in xrange(len(config.UPLOAD_FILES_LOCALHOST_PATH))
    ]

    testflow.setup(
        "Copy images %s needed for upload tests to localhost only if they do "
        "not exist",
        upload_file_names
    )
    for index in xrange(len(config.UPLOAD_FILES_LOCALHOST_PATH)):
        cmd = (
            config.RSYNC_CMD + config.HOSTS_USER + '@' + config.REMOTE_HOST +
            ':' + config.UPLOAD_IMAGES_YELLOW_PATHS[index] + ' ' +
            config.UPLOAD_FILES_LOCALHOST_PATH[index]
        )
        child = pexpect.spawn(cmd)
        fout = open(config.PEXPECT_LOG, 'wb')
        child.logfile = fout
        logger.info(
            "Command %s input and output flow is loggeed at %s",
            cmd, config.PEXPECT_LOG
        )
        pattern_list = [
            'continue connecting \(yes/no\)', 'password:', pexpect.EOF
        ]
        try:
            idx = child.expect(pattern_list, timeout=config.RSYNC_TIMEOUT)
            logger.info("Response is: %s", pattern_list[idx])

            if idx == 0:
                child.sendline('yes')
                child.expect('password:')
                child.sendline(config.YELLOW_PASS)
                logger.info(
                    "First time connection, additional question and password "
                    "required"
                )
                child.expect(pexpect.EOF, config.RSYNC_TIMEOUT)
            if idx == 1:
                child.sendline(config.YELLOW_PASS)
                logger.info("Password required")
                child.expect(pexpect.EOF, config.RSYNC_TIMEOUT)
            if idx == 2:
                logger.info("Ssh keys already exist,password not required")
                child.expect(pexpect.EOF, config.RSYNC_TIMEOUT)

        except pexpect.TIMEOUT:
            assert True, "Timeout occured,command %s took more than %s sec" % (
                (cmd, config.RSYNC_TIMEOUT)
            )

        except Exception as e:
            assert True, "The following unexpected error occured: %s" % e

        finally:
            child.close()
            fout.close()


@pytest.fixture(scope='class')
def initialize_variables(request, storage):
    """
    Initialize variables needed for the test
    """
    self = request.node.cls

    spm = ll_hosts.get_spm_host(config.HOSTS)
    self.spm_host = rhevm_helpers.get_host_resource_by_name(spm)
    data_center_obj = ll_dc.get_data_center(config.DATA_CENTER_NAME)
    self.sp_id = storage_helpers.get_spuuid(data_center_obj)
    self.storage_domain = ll_sd.getStorageDomainNamesForType(
        config.DATA_CENTER_NAME, storage
    )[0]
    self.disks_names = list()


@pytest.fixture(scope='class')
def test_detach_disks(request, storage):
    """
    Detach disks from VM before test
    """

    self = request.node.cls

    disk_ids = self.DISKS_MOUNTS_EXECUTOR[self.vm_name]['disks']
    for disk in disk_ids:
        disk_name = ll_disks.get_disk_obj(disk, attribute='id').get_name()
        self.disks_names.append(disk_name)
        testflow.setup("detach disk %s", disk_name)

        assert ll_disks.detachDisk(
            True, disk_name, self.vm_name
        ), "Failed to detach disk %s to vm %s" % (self.disk_name, self.vm_name)
    self.disks_to_remove = self.disks_names


@pytest.fixture(scope='class')
def test_delete_downloaded_files(request, storage):
    """
    Delete downloaded files from test runner machine
    """

    self = request.node.cls

    self.files_to_remove = list()

    def finalizer():
        if self.files_to_remove:
            testflow.teardown(
                "Deleting downloaded files %s", self.files_to_remove[0]
            )
            cmd = "rm %s" % " ".join(self.files_to_remove[0])
            out, err = Popen(
                shlex.split(cmd),
                stdout=PIPE, stderr=PIPE
            ).communicate()
            assert not err, (
                "Error (%s) occurred when trying to execute the command %s" % (
                    err, cmd
                )
            )
        else:
            testflow.teardown(
                "Downloaded files was not removed as they were not found ,"
                "probably due to a failed step in the test"
            )
    request.addfinalizer(finalizer)


@pytest.fixture(scope='class')
def add_disks_for_upload(request, storage):
    """
    Create matching disks for upload
    """
    self = request.node.cls

    self.disks_names = []
    self.disks_ids = []
    for name, spares, allocation_policy in DISK_ALLOCATIONS:
        disk_params = config.disk_args.copy()
        disk_name = storage_helpers.create_unique_object_name(
            '%s' % name, config.OBJECT_TYPE_DISK
        )
        testflow.setup(
            'Creating a %s %s GB disk on domain %s for image upload purposes',
            str(allocation_policy), config.DISK_SIZE / config.GB,
            self.storage_domain
        )
        disk_params['storagedomain'] = self.storage_domain
        disk_params['sparse'] = spares
        disk_params['provisioned_size'] = config.DISK_SIZE
        disk_params['alias'] = disk_name
        disk_params['format'] = config.DISK_FORMAT_RAW if not spares else (
            config.DISK_FORMAT_COW
        )
        assert ll_disks.addDisk(True, **disk_params), (
            "Failed to create disk %s" % disk_name
        )
        self.disks_names.append(disk_name)
        self.disks_ids.append(
            ll_disks.get_disk_obj(disk_name, attribute='name').get_id()
        )
    testflow.setup('Waiting for disks to be OK')
    assert ll_disks.wait_for_disks_status(self.disks_names), (
        "Disks %s failed to reach status OK" % self.disks_names
    )
    self.disks_to_remove = self.disks_names
