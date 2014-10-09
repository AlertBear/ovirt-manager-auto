__test__ = False

import os
import logging

from utilities import machine
from functools import wraps
from art.test_handler.exceptions import SkipTest
from art.core_api.apis_exceptions import APIException
from art.rhevm_api.utils import test_utils
from rhevmtests.system.generic_ldap import config
from art.rhevm_api.tests_lib.low_level import users, mla, general
from art.unittest_lib.common import is_bz_state


LOGGER = logging.getLogger(__name__)
SKIP_MESSAGE = 'Configuration was not setup for this test. Skipping.'
INTERVAL = 5
ATTEMPTS = 25
TIMEOUT = 70
BZ1147900_FIXED = is_bz_state('1147900')


# Extensions utils
def enableExtensions():
    ''' just restart ovirt engine service '''
    LOGGER.info('Restarting engine...')
    machineObj = machine.Machine(config.VDC_HOST, config.VDC_ROOT_USER,
                                 config.VDC_ROOT_PASSWORD).util(machine.LINUX)
    test_utils.restartOvirtEngine(machineObj, INTERVAL, ATTEMPTS, TIMEOUT)


def cleanExtDirectory(ext_dir):
    ''' remove all files from extension directory '''
    ext_files = os.path.join(ext_dir, '*')
    machineObj = machine.Machine(config.VDC_HOST, config.VDC_ROOT_USER,
                                 config.VDC_ROOT_PASSWORD).util(machine.LINUX)
    machineObj.removeFile(ext_files)


def prepareExtensions(module_name, ext_dir, extensions, clean=True):
    '''
    prepare all extension for module_name
    Parameters:
        module_name - current test module
        ext_dir - directory where extensions should be prepared
        extensions - dictionary where is stored if setup was successfull
        clean - if True clean $ext_dir before preparing configurations
    '''
    if clean:
        cleanExtDirectory(ext_dir)

    ext_path = os.path.dirname(os.path.abspath(__file__))
    machineObj = machine.Machine(config.VDC_HOST, config.VDC_ROOT_USER,
                                 config.VDC_ROOT_PASSWORD).util(machine.LINUX)
    LOGGER.info(module_name)
    confs = os.listdir(os.path.join(ext_path, config.FIXTURES, module_name))

    for conf in confs:
        ext_file = os.path.join(ext_path, config.FIXTURES, module_name, conf)
        try:
            assert machineObj.copyTo(ext_file, ext_dir)
            res = machineObj.runCmd(['chown', 'ovirt:ovirt', ext_file])
            assert res[0], res[1]
            LOGGER.info('Configuration "%s" has been copied.', conf)
            extensions[conf] = True
        except AssertionError as e:
            LOGGER.error('Configuration "%s" has NOT been copied. Tests with '
                         'this configuration will be skipped. %s', conf, e)
            extensions[conf] = False

    enableExtensions()


# Check if extension was correctly copied, and could be tested.
def check(ext=None):
    def decorator(method):
        @wraps(method)
        def f(self, *args, **kwargs):
            if ext and not ext.get(self.conf['authz_file'], False):
                LOGGER.warn(SKIP_MESSAGE)
                raise SkipTest(SKIP_MESSAGE)
            return method(self, *args, **kwargs)
        return f
    return decorator


# -- MLA utils --
def assignUserPermissionsOnCluster(user_name, provider, principal=None,
                                   role=config.USERROLE,
                                   cluster=config.DEFAULT_CLUSTER_NAME,
                                   create_user=True):
    '''
    Assign user permissions on cluster.
    Parameters:
     * user_name - username of user
     * provider - provider where user exists
     * principal - principal
     * role - role which should be assign him
     * cluster - cluster where role should be added
     * create_user - True/False if user should be added before perms assigned

    return True if operation succeed False otherwise
    '''
    if (create_user and not users.addUser(True, user_name=user_name,
                                          domain=provider,
                                          principal=principal)):
        if BZ1147900_FIXED:
            return False

    return mla.addClusterPermissionsToUser(True, user_name, cluster,
                                           role, provider)


def connectionTest():
    try:
        return general.getProductName()[0]
    except (APIException, AttributeError):
        # We expect either login will fail (wrong user) or
        # general.getProductName() will return None (correct user + filter set)
        return False
    return True


def loginAsAdmin():
    users.loginAsUser(config.VDC_ADMIN_USER, config.VDC_ADMIN_DOMAIN,
                      config.VDC_PASSWORD, False)


# -- Truststore utils --
def generateCertificate(session, ssl_host, crt_dir, port='636'):
    '''
    Create temp file with certificate of service runnning on @host at @port.
    Parameters:
     * session - ssh session
     * ssl_host - host where service is running
     * crt_dir - directory where certificate should be generated
     * port - default port which is used when host doesn't contain port
    return True if cert was successfully obtained, False otherwise
    '''
    if ssl_host.find(':') == -1:
        ssl_host += ':' + str(port)
    crt_file = '%s/%s' % (crt_dir, ssl_host)
    cmd = ['echo', '|', 'openssl', 's_client', '-connect', ssl_host, '2>&1',
           '|', 'sed', '-ne', '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p',
           '>', crt_file]
    rc, _, _ = session.run_cmd(cmd)
    return rc, crt_file


def importCertificateToTruststore(session, filename, truststore, password):
    '''
    Import certificate into truststore.
    Parameters:
     * session - ssh session
     * filename - filename with certificate to be imported
     * truststore - truststore where certificate should be imported
     * password - truststore password
    '''
    cmd = ['keytool', '-import', '-noprompt', '-storepass', password,
           '-file', filename, '-alias', filename, '-keystore', truststore]
    return session.run_cmd(cmd)


def listTruststore(session, truststore, password):
    '''
    Return list of certificates in truststore. For debug purposes.
    Parameters:
     * session - ssh session
     * truststore - truststore which should be listed
     * password - truststore password
    Return output of keytool list command
    '''
    cmd = ['keytool', '-list', '-storepass', password, '-keystore', truststore]
    rc, out, _ = session.run_cmd(cmd)
    return out


def createTrustore(hosts, truststore, password, temp_dir='/tmp'):
    '''
    Parameters:
     * hosts - list of host:port strings where certs should be obtained
     * truststore - full path of truststore
     * password - truststore password
     * temp_dir - directory where temporary cert are stored
    '''
    executor = config.ENGINE_HOST.executor()
    with executor.session() as ss:
        for ssl_host in hosts:
            rc, crt_file = generateCertificate(ss, ssl_host, temp_dir)
            if rc:
                LOGGER.error('Cert for %s was not obtained.', ssl_host)
                continue

            importCertificateToTruststore(ss, crt_file, truststore, password)

        LOGGER.info('Truststore content is:\n%s',
                    listTruststore(ss, truststore, password))


def removeTruststore(truststore):
    '''
    Parameters:
     * truststore - full path of truststore
    '''
    executor = config.ENGINE_HOST.executor()
    executor.run_cmd(['rm', '-f', truststore])


# engine configurations
def changeEngineProperties(confname, key, value,
                           conf_dir=config.PROPERTIES_DIRECTORY):
    """
    Changes properties of engine.
    Parameters:
     * confname - name of confile to be created
     * key - name of property key to be changed
     * value - value of property to be changed
    """
    filepath = os.path.join(conf_dir, confname)
    property = '%s="\${%s} %s"' % (key, key, value)
    cmd = ['echo', property, '>', filepath,
           '&&', 'chown', 'ovirt:ovirt', filepath]

    executor = config.ENGINE_HOST.executor()
    return executor.run_cmd(cmd)


def removeFile(filepath):
    """
    Remove file on engine.
    Parameters:
     * filepath - file to be removed
    """
    executor = config.ENGINE_HOST.executor()
    return executor.run_cmd(['rm', '-f', filepath])
