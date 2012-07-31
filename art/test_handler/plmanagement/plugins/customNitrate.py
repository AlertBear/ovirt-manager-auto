import os.path
import logging
import traceback
from subprocess import call

import utilities.utils as utils
import utilities.errors as errors
from utilities.enum import Enum

try:
    # From /usr/lib64/python2.7/nitrate.py @qtms.qa.lab.tlv.redhat.com (most up-to-dated)
    import nitrate as nitrateApi
except ImportError:
    # From the current project folder (most stable)
    import nitrateApi

# TCMS entity names
eTcmsEntity = Enum( TestPlan=1,
                    TestRun=2,
                    TestCase=3,
                    TestCaseRun=4,
                    Product=5,
                    ProductVersion=6,
                    ProductCategory=7,
                    Build=8)

URL = "http://"
SECURE_URL = "https://"


class NitrateObjectCreationError(errors.GeneralException):
    message = "failed to create CustomNitrateKerbXmlrpc object"


class UnsupportedEntityTypeError(errors.GeneralException):
    message = "no such entity in TCMS model"


class CustomNitrateKerbXmlrpc(nitrateApi.NitrateXmlrpc):
    """
        This class supports login-on-demand into Nitrate xmlrpc service.
        We need it for supporting deserialization process of TcmsAgent class object
        when no need to perform an additional login since the ticket-granting
        ticket is already stored in the credentials cahce on a client machine.
        NOTE: the user must be registered as a principal with the Key Distribution
        Center (KDC) prior to running kinit utility, must have its own keytab file
        under testMachine:/usr/share/rhevm-atf/data/keytab_files and should have proper permissions
        to be able to create test cases and test/case runs on TCMS site.
    """
    def __init__(self, url, userName=None, keytabFile=None):
        """
            C'tor.
            Author: mbenenso
            Parameters:
             * url - URL to Nitrate xmlrpc service
             * userName - the name of the user (optional)
             * keytabFile - path to user's keytab file (optional)
            Return: none
            Throws: NitrateObjectCreationError
        """
        if not utils.valid(url):
            raise NitrateObjectCreationError("tcms url is empty")

        # Support secure http only
        if url.startswith(SECURE_URL):
            self._transport = nitrateApi.KerbTransport()
        elif url.startswith(URL):
            raise NitrateObjectCreationError("only secure http is supported")
        else:
            raise NitrateObjectCreationError("unrecognized URL scheme")

        self.logger = logging.getLogger("nitrate")
        try:
            # Create xmlrpc server
            self._transport.cookiejar = nitrateApi.CookieJar()
            self.server = nitrateApi.xmlrpclib.ServerProxy(url,
                                                    transport=self._transport,
                                                    verbose=nitrateApi.VERBOSE)
            if userName is not None:
                # Try to login into Nitrate xmlrpc service
                if self._obtainKerberosTicket(userName, keytabFile):
                    self.runCommand("Auth.login_krbv")
        except Exception as err:
            self.logger.error(traceback.format_exc())
            raise NitrateObjectCreationError("%s" % str(err))

    def _obtainKerberosTicket(self, principalName, keytabFilePath):
        """
            Obtain Kerberos ticket for principal with principalName using keytabFilePath.
            Author: mbenenso
            Parameters:
             * userName - principal name (name@REDHAT.COM)
             * keytabFilePath - path to principal's keytab file
            Return: returncode attribute, 0 on success, a negative integer otherwise
            Throws: WrongParameterError, FileNotFoundException
        """
        if not utils.valid(principalName, keytabFilePath):
            raise errors.WrongParameterError(principalName, keytabFilePath)

        if not os.path.exists(keytabFilePath):
            raise errors.FileNotFoundException(keytabFilePath)

        cmd = ['kinit', principalName, "-k", "-t", keytabFilePath]
        retCode = call(cmd)
        if retCode != 0:
            self.logger.error("failed to obtain Kerberos ticket, return code: %s", retCode)
            return False
        return True

    def runCommand(self, verb, *args):
        """
            Run xmlrpc command using Nitrate API.
            Author: mbenenso
            Parameters:
            * verb - the verb to execute
            * args - variable-length argument list for the verb
            Return: a list with TCMS entry objects on success, an empty list otherwise
        """
        if not utils.valid(verb):
            self.logger.error("command verb is empty")
        else:
            try:
                res = self.do_command(verb, list(args))
                if isinstance(res, dict) and res:
                    return [res]    # Return non-empty dictionary inside a list
                elif res:
                    return res      # Return non-empty list
            except nitrateApi.NitrateXmlrpcError as err:
                if "duplicate entry" in str(err).lower():
                    msg = "skip creation of duplicate entry for verb '%s' with args '%s"
                    self.logger.warning(msg, verb, args)
                else:
                    msg = "received Nitrate xmlrpc error: %s"
                    self.logger.error(msg, traceback.format_exc())
            except Exception:
                msg = "failed to run TCMS command '%s' with args '%s': %s"
                self.logger.error(msg, verb, args, traceback.format_exc())
        return []

    def getById(self, entityType, id):
        """
            Fetch TCMS entry by its ID.
            Author: mbenenso
            Parameters:
            * entityType - the type of TCMS entry
            * id - an ID of the TCMS entry
            Return: a dictionary with TCMS entry details on success, None otherwise
        """
        if not utils.valid(entityType, id):
            self.logger.error("wrong input parameters")
        else:
            cmd = "{0}.get"
            try:
                entity = eTcmsEntity.toString(entityType)
            except ValueError:
                self.logger.error("getById failed, unsupported entity type: '%s'", entityType)
            else:
                return self.runCommand(cmd.format(entity), id)
        return []

    def isConnected(self):
        """
            Verify if the agent esteblished connection with TCMS.
            Author: mbenenso
            Parameters: none
            Return: True if connection to TCMS xmlrpc service established,
                    False otherwise
        """
        # Validate if connection to TCMS established by
        # making a simple xmlrpc call for current user details
        return bool(self.runCommand("User.get_me"))