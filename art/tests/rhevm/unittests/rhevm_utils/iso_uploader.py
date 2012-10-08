
# Usage: rhevm-iso-uploader [options] list
#        rhevm-iso-uploader [options] upload [file].[file]...[file]
#
# The ISO uploader can be used to list ISO storage domains and upload files to
# storage domains.  The upload operation supports multiple files (separated by
# spaces) and wildcarding.
#
# Options:
#   --version             show program's version number and exit
#   -h, --help            show this help message and exit
#   --quiet               intended to be used with "upload" operations to reduce
#                         console output. (default=False)
#   --log-file=PATH       path to log file (default=/var/log/rhevm/rhevm-iso-
#                         uploader.log)
#   --conf-file=PATH      path to configuration file
#                         (default=/etc/rhevm/isouploader.conf)
#   -v, --verbose
#   -f, --force           replace like named files on the target file server
#                         (default=off)
#
#   RHEV-M Configuration:
#     The options in the RHEV-M group are used by the tool to gain
#     authorization to the RHEV-M REST API. The options in this group are
#     available for both list and upload commands.
#
#     -u user@rhevm.example.com, --user=user@rhevm.example.com
#                         username to use with the RHEV-M REST API.  This should
#                         be in UPN format.
#     -r rhevm.example.com, --rhevm=rhevm.example.com
# WARN: there is difference between RHEVM and oVirt
#     -r rhevm.example.com, --engine=rhevm.example.com
#                         hostname or IP address of the RHEV-M
#                         (default=localhost:8443).
#
#   ISO Storage Domain Configuration:
#     The options in the upload configuration group should be provided to
#     specify the ISO storage domain to which files should be uploaded.
#
#     -i ISODOMAIN, --iso-domain=ISODOMAIN
#                         the ISO domain to which the file(s) should be uploaded
#     -n NFSSERVER, --nfs-server=NFSSERVER
#                         the NFS server to which the file(s) should be
#                         uploaded. This option is an alternative to iso-domain
#                         and should not be combined with iso-domain.  Use this
#                         when you want to upload files to a specific NFS server
#                         (e.g.--nfs-server=example.com:/path/to/some/dir)
#
#   Connection Configuration:
#     By default the program uses NFS to copy files to the ISO storage
#     domain. To use SSH file transfer, instead of NFS, provide a ssh-user.
#
#     --ssh-user=root     the SSH user that the program will use for SSH file
#                         transfers.  This user must either be root or a user
#                         with a UID and GID of 36 on the target file server.
#     --ssh-port=PORT     the SSH port to connect on
#     -k KEYFILE, --key-file=KEYFILE
#                         the identity file (private key) to be used for
#                         accessing the file server. If a identity file is not
#                         supplied the program will prompt for a password.  It
#                         is strongly recommended to use key based
#                         authentication with SSH because the program may make
#                         multiple SSH connections resulting in multiple
#                         requests for the SSH password.
#
# Return values:
#     0: The program ran to completion with no errors.
#     1: The program encountered a critical failure and stopped.
#     2: The program did not discover any ISO domains.
#     3: The program encountered a problem uploading to an ISO domain.
#     4: The program encountered a problem un-mounting and removing the temporary directory.


import os
import re
from rhevm_utils.base import Utility, logger, RHEVMUtilsTestCase
from rhevm_utils import errors
from utilities import machine

NAME = 'iso-uploader'

OPT_HELP = set(('h', 'help'))
OPT_USER = set(('u', 'user'))
OPT_ISO_DOMAIN = set(('i', 'iso-domain'))
OPT_NFS_SERVER = set(('n', 'nfs-server'))

ACTION_LIST = 'list'
ACTION_UPLOAD = 'upload'

CONNECTION_COLUMN = 'connection'
STORAGE_DOMAIN_TYPE_COLUMN = 'storage_domain_type'
STORAGE_NAME_COLUMN = 'storage_name'
STORAGE_SERVER_CONNECTIONS_TABLE = 'storage_server_connections'
STORAGE_DOMAINS_TABLE = 'storage_domains'
STORAGE_COLUMN = 'storage'
ID_COLUMN = 'id'

XID_FILE_ATTR = 36
NOBODY_XID = 99

ISO_DOMAIN_UID = '11111111-1111-1111-1111-111111111111'

# ( pattern, exeption, names of params, (sub errors, .. ) )
ERROR_PATTERNS = ()

class ISOUploadUtility(Utility):
    """
    Encapsulation of rhevm-iso-upload utility
    """
    def __init__(self, *args, **kwargs):
        super(ISOUploadUtility, self).__init__(*args, **kwargs)
        self.opt_host = set(('r', self.setup.product))
        self.action = None
        self.files = None
        self.kwargs = None

    def __call__(self, *args, **kwargs):
        self.action = None
        self.files = None
        if len(args) >= 1:
            action = args[0]
            files = args[1:]
        self.kwargs = self.clearParams(kwargs)

        if self.opt_host in self.kwargs:
            # TODO:
            raise NotImplementedError(\
                    "this functionality is not covered yet: %s", self.opt_host)

        cmd = self.createCommand(NAME, self.kwargs)

        if self.action is not None:
            cmd.append(self.action)

        if self.files is not None:
            for name in self.files:
                cmd.append(self.checkPassedFile(name))

        self.execute(NAME, cmd)

        #self.autoTest()


    def retrieveInfo(self, storage_name, count=None):
        """
        Fetch info about storage domain
        Parameters:
         * storage_name - str name
         * count - expected count of storage domains
        Return: ((path, str_id, str_type, str_name), ...)
        """
        sql = "SELECT c.%s, s.%s, s.%s, s.%s FROM %s c "\
              "INNER JOIN %s s ON (s.%s = c.%s) WHERE %s LIKE '%s';"
        info = self.setup.psql(sql, CONNECTION_COLUMN, ID_COLUMN, \
                STORAGE_DOMAIN_TYPE_COLUMN, STORAGE_NAME_COLUMN, \
                STORAGE_SERVER_CONNECTIONS_TABLE, STORAGE_DOMAINS_TABLE, \
                STORAGE_COLUMN, ID_COLUMN, STORAGE_NAME_COLUMN, storage_name)

        if count is not None and count != len(count):
            msg = "failed to retrieve data about storage domain '%s': %s" \
                    % (storage_name, self.out)
            raise errors.ISOUploadUtilityError(msg)
        return info

    def checkFilesThere(self, root):
        """
        Verifies the files was uploaded properly
        Parameters:
         * root - path to base directory
        """
        passed = True
        for path in self.files:
            expected = os.path.join(root, os.path.basename(path))
            if not os.path.exists(expected):
                logger.error("failed to find file '%s' which was expected '%s'", path, expected)
                passed = False
                continue
            attrs = os.stat(expected)
            if attrs.st_uid != XID_FILE_ATTR or attrs.st_gid != XID_FILE_ATTR:
                if attrs.st_uid == NOBODY_XID or attrs.st_gid == NOBODY_XID:
                    logger.warn("it seems like idmapd problem. you should setup idmapd properly")
                logger.error("unexpected permission on '%s' %s", expected, attrs)
                passed = False
        return passed

    # ====== TESTS ========

    def autoTest(self):
        if OPT_HELP in self.kwargs:
            self.testReturnCode()
            return
        if self.rc == 1 and "Unauthorized" in self.err:
            raise errors.AuthorizationError(self.err)
        if ACTION_UPLOAD == self.action:
            self.testUpload()
        if ACTION_LIST == self.action:
            self.testList()

    def testUpload(self):
        localMachine = machine.Machine().util(machine.LINUX)
        if OPT_ISO_DOMAIN in self.kwargs:
            info = self.retrieveInfo(self.kwargs[OPT_ISO_DOMAIN], 1)[0]
            if info[2] != '2':
                raise errors.ISOUploadUtilityError("%s is not iso-domain" % self.kwargs[OPT_ISO_DOMAIN])
            with localMachine.mount(info[0]) as target:
                path = os.path.join(target, info[1], 'images', ISO_DOMAIN_UID)
                if not self.checkFilesThere(path):
                    msg = "failed to validate files on iso domain: %s" % info[0]
                    raise errors.ISOUploadUtilityError(msg)

        if OPT_NFS_SERVER in self.kwargs:
            with localMachine.mount(self.kwargs[OPT_NFS_SERVER]) as target:
                if not self.checkFilesThere(target):
                    msg = "failed to validate files on nfs domain: %s" % \
                            self.kwargs[OPT_NFS_SERVER]
                    raise errors.ISOUploadUtilityError(msg)

    def testList(self):
        localMachine = machine.Machine().util(machine.LINUX)
        info = [x for x in self.retrieveInfo('%') if x[2] == '2']
        if not info:
            expMsg = 'There are no ISO storage domains'
            if expMsg not in self.err:
                raise errors.OutputVerificationError(expMsg, self.err)
            self.testReturnCode(2)
        else:
            self.testReturnCode()
            res = re.findall('.+[|].+[|].+', self.out)
            if len(res) < 2 and self.rc == 0:
                raise errors.ISOUploadUtilityError("expected list if ISO doamins: %s, %s" % (self.out, info))
            res = set( x.split('|')[0].strip() for x in res[1:] )
            if len(info) != len(set(x[3] for x in info) & res):
                raise errors.ISOUploadUtilityError(\
                        "list doens't contain expected list: %s != %s" % (info, res))


#### UNITTESTS #####


class ISOUploaderTestCase(RHEVMUtilsTestCase):

    __test__ = False # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = ISOUploadUtility
    _multiprocess_can_split_ = True


