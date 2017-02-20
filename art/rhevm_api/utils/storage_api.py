"""
A collection of wrappers which allow the usage of general utils functions and
storage API in the REST framework.
"""
import logging

from utilities import machine

log = logging.getLogger("storage_api")

FILE_HANDLER_TIMEOUT = 15


def setupIptables(source, userName, password, dest, command, chain,
                  target, protocol='all', persistently=False, *ports):
    """Wrapper for utilities.machine.setupIptables() method."""
    hostObj = machine.Machine(source, userName, password).util('linux')
    return hostObj.setupIptables(dest, command, chain, target,
                                 protocol, persistently, *ports)


def blockOutgoingConnection(source, userName, password, dest, port=None):
    '''
    Description: Blocks outgoing connection to an address
    Parameters:
      * source - ip or fqdn of the source machine
      * userName - username on the source machine
      * password - password on the source machine
      * dest - ip or fqdn of the machine to which to prevent traffic
      * port - outgoing port we wanna block
    Return: True if commands succeeds, false otherwise.
    '''
    if port is None:
        return setupIptables(source, userName, password, dest, '--append',
                             'OUTPUT', 'DROP')
    else:
        return setupIptables(source, userName, password, dest, '--append',
                             'OUTPUT', 'DROP', 'all', False, port)


def unblockOutgoingConnection(source, userName, password, dest, port=None):
    '''
    Description: Unblocks outgoing connection to an address
    Parameters:
      * source - ip or fqdn of the source machine
      * userName - username on the source machine
      * password - password on the source machine
      * dest - ip or fqdn of the machine to which to remove traffic block
      * port - outgoing port we wanna unblock
    Return: True if commands succeeds, false otherwise.
    '''
    if port is None:
        return setupIptables(source, userName, password, dest, '--delete',
                             'OUTPUT', 'DROP')
    else:
        return setupIptables(source, userName, password, dest, '--delete',
                             'OUTPUT', 'DROP', 'all', False, port)


def blockIncomingConnection(source, userName, password, dest):
    """Warpper for blocking incoming connection from any server to host."""
    return setupIptables(source, userName, password, dest,
                         '--append', 'INPUT', 'DROP')


def unblockIncomingConnection(source, userName, password, dest):
    """Warpper for unblocking incoming connection from any server to host."""
    return setupIptables(source, userName, password, dest,
                         '--delete', 'INPUT', 'DROP')


def flushIptables(host, userName, password, chain='', persistently=False):
    """Warpper for utilities.machine.flushIptables() method."""
    hostObj = machine.Machine(host, userName, password).util('linux')
    return hostObj.flushIptables(chain, persistently)
