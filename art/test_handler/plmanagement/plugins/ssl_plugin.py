"""
---------------------
SSL Connection Plugin
---------------------

Plugin that sets up SSL certificates necessary
to connect securely with SDK and CLI.
To enable the plugin, put 'secure = yes' under [RUN] in conf file.
"""

import os
from OpenSSL import crypto
from subprocess import Popen
from art.test_handler.plmanagement import (Component, implements, get_logger,
                                           PluginError)
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.settings import opts
from art.core_api.http import HTTPProxy


logger = get_logger('ssl_plugin')

RUN = 'RUN'
SECURE = 'secure'
DIR = '/var/tmp'
CA_PATH = os.path.join(DIR, 'ca.crt')
KEY_PATH = os.path.join(DIR, 'ART.key')
CERT_PATH = os.path.join(DIR, 'ART.crt')
KEY_STORE_PATH = os.path.join(DIR, 'server.truststore')


class SSL_Error(PluginError):
    pass


class RHEVM_SSL_Plugin(Component):
    """
    Plugin that sets up SSL certificates necessary
    to connect securely with SDK and CLI.
    To enable the plugin, put 'secure = yes' under [RUN] in conf file.
    """
    implements(IConfigurable, IPackaging)

    name = "RHEVM SSL support"
    priority = -10000

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        self.__download_ca_certificate()
        self.__generate_client_certificates()
        self.__generate_key_store_file()

        opts['ssl_ca_file'] = CA_PATH
        opts['ssl_cert_file'] = CERT_PATH
        opts['ssl_key_file'] = KEY_PATH
        opts['ssl_key_store_file'] = KEY_STORE_PATH

    @classmethod
    def __download_ca_certificate(cls):
        proxy = HTTPProxy(opts)
        res = proxy.GET('/ca.crt')
        #TODO: check for errors
        #raise SSL_Error
        with open(CA_PATH, 'w') as ca_file:
            ca_file.write(res['body'])

    @classmethod
    def __generate_key_store_file(cls):
        # remove the file if exist
        Popen(['rm', '-f', KEY_STORE_PATH]).communicate()
        # command to generate the key store file for secured java api
        cmd = ['keytool', '-noprompt', '-import', '-alias',
               '"server.crt truststore"', '-file', CA_PATH, '-keystore',
               KEY_STORE_PATH, '-storepass', opts['password'], '-keypass',
               opts['password']]
        p = Popen(cmd)
        p.communicate()
        if p.returncode:
            raise Exception("command %s failed" % " ".join(cmd))

    @classmethod
    def __generate_client_certificates(cls):
        # generate key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 1024)

        # create a self-signed certificate for the client
        cert = crypto.X509()
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(2*24*60*60)
        cert.set_pubkey(key)
        cert.sign(key, 'sha1')

        with open(KEY_PATH, 'w') as key_file:
            key_file.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
        with open(CERT_PATH, 'w') as cert_file:
            cert_file.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    @classmethod
    def is_enabled(cls, params, conf):
        return conf[RUN].as_bool(SECURE)

    @classmethod
    def add_options(cls, parser):
        pass

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Gal Leibovici'
        params['author_email'] = 'gleibovi@redhat.com'
        params['description'] = 'Sets up SSL connection to RHEVM'
        params['long_description'] = cls.__doc__
        params['requires'] = ['pyOpenSSL']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.ssl_plugin']
