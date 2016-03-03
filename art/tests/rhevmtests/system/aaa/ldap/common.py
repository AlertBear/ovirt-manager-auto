__test__ = False

import logging
import os
import tempfile

from functools import wraps
from art.test_handler.exceptions import SkipTest
from art.core_api.apis_exceptions import APIException
from rhevmtests.system.aaa.ldap import config
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
    """ remove files from extension directory except internal domain """
    internal_files = [
        'internal-authn.properties',
        'internal-authz.properties',
        'internal.properties',
    ]
    cmd = ['ls']
    cmd.extend([os.path.join(ext_dir, f) for f in files])
    cmd.extend([
        '|',
        'grep',
        '-vE',
        "'%s'" % '|'.join(internal_files),
        '|',
        'xargs',
        'rm',
        '-f',
    ])
    with config.ENGINE_HOST.executor().session() as ss:
        ss.run_cmd(cmd)


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
def import_certificate_to_truststore(host, cert_path, truststore, password):
    '''
    Import certificate from url into truststore.

    :param host: host with truststore
    :type host: resources.Host
    :param cert_path: path to certificate
    :type cert_path: str
    :param truststore: trustore to store certificate
    :type truststore: str
    :param password: password of trustore
    :type password: str
    '''
    with host.executor().session() as session:
        return session.run_cmd([
            'keytool', '-import', '-noprompt',
            '-storepass', password,
            '-file', cert_path,
            '-alias', cert_path,
            '-keystore', truststore,
        ])


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


def setup_ldap(host, conf_file):
    """
    Run ovirt-engine-extension-aaa-ldap-setup with answer file

    :param host: host where to run ldap setup
    :type host: resources.Host
    :param conf_file: path to answer file
    :type conf_file: str
    :returns: exit code of ovirt-engine-extension-aaa-ldap-setup
    :rtype: int
    """
    tempconf = tempfile.mkstemp()[1]
    copy_extension_file(host, conf_file, tempconf, None)
    with host.executor().session() as ss:
        LOGGER.info("Setting up ldap with conf file %s", conf_file)
        rc, out, err = ss.run_cmd([
            'ovirt-engine-extension-aaa-ldap-setup',
            '--config-append=%s' % tempconf,
        ])
        ss.run_cmd(['rm', '-f', tempconf])
        LOGGER.info(out)
    return not rc


def extend(properties={}):
    """
    Extend current properties file of extension with values in properties param
    """
    def decorator(method):
        @wraps(method)
        def f(self, *args, **kwargs):
            ret = None
            try:
                x = self.extended_properties.copy()
                x.update(properties)
                with self.executor.session() as ss:
                    with ss.open_file(self.ext_file, 'w') as f:
                        for k, v in x.iteritems():
                            f.write('%s = %s\n' % (k, v))

                ret = method(self, *args, **kwargs)
            finally:
                with self.executor.session() as ss:
                    with ss.open_file(self.ext_file, 'w') as f:
                        for k, v in self.extended_properties.iteritems():
                            f.write('%s = %s\n' % (k, v))

                return ret
        return f
    return decorator
