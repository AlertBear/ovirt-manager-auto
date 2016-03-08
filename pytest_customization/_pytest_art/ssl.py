"""
Module implements all necessary actions to  sets up SSL certificates
used to connect securely with RHEVM SDK and CLI.
"""

import os
from OpenSSL import crypto
from subprocess import Popen
from art.test_handler.settings import opts
import rrmngmnt

DIR = '/var/tmp'
CA_PATH = os.path.join(DIR, 'ca.crt')
KEY_PATH = os.path.join(DIR, 'ART.key')
CERT_PATH = os.path.join(DIR, 'ART.crt')
KEY_STORE_PATH = os.path.join(DIR, 'server.truststore')
PARAMETERS = 'PARAMETERS'
VDC_PASSWD = 'vdc_root_password'
DEFAULT_ROOT_PASSWORD = 'qum5net'


def configure(art_config):
    opts[VDC_PASSWD] = art_config[PARAMETERS].get(
        VDC_PASSWD, DEFAULT_ROOT_PASSWORD
    )
    __download_ca_certificate()
    __generate_client_certificates()
    __generate_key_store_file()

    opts['ssl_ca_file'] = CA_PATH
    opts['ssl_cert_file'] = CERT_PATH
    opts['ssl_key_file'] = KEY_PATH
    opts['ssl_key_store_file'] = KEY_STORE_PATH


def __download_ca_certificate():
    _cmd = [
        'openssl', 's_client', '-showcerts', '-connect', 'localhost:443',
        '<', '/dev/null'
    ]
    vdc = rrmngmnt.Host(opts['host'])
    vdc.users.append(rrmngmnt.User('root', opts[VDC_PASSWD]))
    cert_text = '-----{0} CERTIFICATE-----'
    start_cert = cert_text.format('BEGIN')
    end_cert = cert_text.format('END')
    with vdc.executor().session() as session:
        rc, out, err = session.run_cmd(_cmd)

    if rc:
        raise Exception(
            "Failed to get certificate from host %s with ERR: %s, RC: %s" %
            (opts['host'], err, rc)
        )
    certificate = out.split(start_cert)[-1].split(end_cert)[0]
    with open(CA_PATH, 'w') as ca_file:
        ca_file.write(start_cert)
        ca_file.write(certificate)
        ca_file.write(end_cert)


def __generate_key_store_file():
    # remove the file if exist
    Popen(['rm', '-f', KEY_STORE_PATH]).communicate()
    # command to generate the key store file for secured java api
    cmd = [
        'keytool', '-noprompt', '-import', '-alias', '"server.crt truststore"',
        '-file', CA_PATH, '-keystore', KEY_STORE_PATH,
        '-storepass', opts['ssl_key_store_password'], '-keypass',
        opts['ssl_key_store_password'],
    ]
    p = Popen(cmd)
    p.communicate()
    if p.returncode:
        raise Exception("Generation of keystore failed: %s" % " ".join(cmd))


def __generate_client_certificates():
    # generate key
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 1024)

    # create a self-signed certificate for the client
    cert = crypto.X509()
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(2 * 24 * 60 * 60)  # Two days
    cert.set_pubkey(key)
    cert.sign(key, 'sha1')

    with open(KEY_PATH, 'w') as key_file:
        key_file.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    with open(CERT_PATH, 'w') as cert_file:
        cert_file.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
