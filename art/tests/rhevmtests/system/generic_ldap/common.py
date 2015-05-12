__test__ = False

import os
import logging

from functools import wraps
from art.test_handler.exceptions import SkipTest
from art.core_api.apis_exceptions import APIException
from rhevmtests.system.generic_ldap import config
from art.rhevm_api.tests_lib.low_level import users, mla, general
from art.rhevm_api.utils.aaa import copy_extension_file
from art.rhevm_api.utils.test_utils import restart_engine


LOGGER = logging.getLogger(__name__)
SKIP_MESSAGE = 'Configuration was not setup for this test. Skipping.'
INTERVAL = 5
ATTEMPTS = 25


# Extensions utils
def enableExtensions(service, host):
    """ restart service """
    LOGGER.info('Restarting service %s.' % service)
    if service == config.OVIRT_SERVICE:
        restart_engine(config.ENGINE, INTERVAL, INTERVAL * ATTEMPTS)
    else:
        host.service(service).restart()


def cleanExtDirectory(ext_dir, files=['*']):
    """ remove files from extension directory """
    ext_files = [os.path.join(ext_dir, f) for f in files]
    with config.ENGINE_HOST.executor().session() as ss:
        ss.run_cmd(['rm', '-f', ' '.join(ext_files)])


def prepareExtensions(module_name, ext_dir, extensions, clean=True,
                      service=config.OVIRT_SERVICE, host=config.ENGINE_HOST,
                      chown=None, enable=True):
    '''
    prepare all extension for module_name
    Parameters:
        module_name - current test module
        ext_dir - directory where extensions should be prepared
        extensions - dictionary where is stored if setup was successfull
        clean - if True clean $ext_dir before preparing configurations
        service - service which should be restarted at the end of function
        host - host where extensions should be prepared
        chown - change owner and group to of properties files
    '''
    if clean:
        cleanExtDirectory(ext_dir)

    ext_path = os.path.dirname(os.path.abspath(__file__))
    LOGGER.info(module_name)
    dir_from = os.path.join(
        ext_path,
        config.FIXTURES,
        module_name,
    )
    confs = os.listdir(dir_from)

    for conf in confs:
        ext_file = os.path.join(dir_from, conf)
        target_file = os.path.join(ext_dir, conf)
        try:
            copy_extension_file(host, ext_file, target_file, chown)
            extensions[conf] = True
        except AssertionError as e:
            LOGGER.error('Configuration "%s" has NOT been copied. Tests with '
                         'this configuration will be skipped. %s', conf, e)
            extensions[conf] = False

    if enable:
        enableExtensions(service, host)


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
    if create_user:
        assert users.addExternalUser(
            True,
            user_name=user_name,
            domain=provider,
            principal=principal
        ), "Can't add user '%s' from provider '%s'" % (user_name, provider)

    return mla.addClusterPermissionsToUser(
        True, user_name, cluster, role, provider
    )


def connectionTest():
    try:
        return general.getProductName()[0]
    except (APIException, AttributeError):
        # We expect either login will fail (wrong user) or
        # general.getProductName() will return None (correct user + filter set)
        return False
    return True


def loginAsAdmin():
    users.loginAsUser('admin', 'internal', '123456', False)


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


def importCertificateToTrustStore(session, filename, truststore, password):
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


def listTrustStore(session, truststore, password):
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


def createTrustStore(hosts, truststore, password, temp_dir='/tmp'):
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

            importCertificateToTrustStore(ss, crt_file, truststore, password)

        LOGGER.info('Truststore content is:\n%s',
                    listTrustStore(ss, truststore, password))


def removeTrustStore(truststore):
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
