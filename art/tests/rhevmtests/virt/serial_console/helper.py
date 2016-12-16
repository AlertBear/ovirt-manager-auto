import re
import string
import copy
import random
import pexpect

import logging
import config as sc_conf
import rhevmtests.helpers as rhevm_helpers

from art.rhevm_api.tests_lib.low_level import users as usr
from art.rhevm_api.tests_lib.high_level import vms as hl_vms
from art.core_api.apis_utils import TimeoutingSampler
from art.core_api.apis_exceptions import APITimeout
from art.core_api.apis_exceptions import EntityNotFound

logger = logging.getLogger('serial_console_logger')


def get_ssh_key_object(user_name):
    """
    Method designed to obtain the ssh_public_keys object.
    Args:
        user_name (str): user name to get ssh_public keys object for.

    Returns:
        list: list with ssh public key object as single element or an empty
              list if there is no public key set yet.

    Raises:
        EntityNotFound: error is reproduced if there is no 'sshpublickeys' rel
                        in the response body.
    """
    users_obj = usr.get_user_obj(user_name)
    for data in users_obj.link:
        if data.get_rel() == 'sshpublickeys':
            return usr.util.get(data.get_href(), 'ssh_public_key')
    raise EntityNotFound("'sshpublickeys' entity was not found")


def generate_random_text(length):
    """
    Generate random payload for test file.
    Args:
        length (int): length of the payload

    Returns:
        str: random payload with proper length
    """
    return ''.join([random.choice(string.lowercase) for _ in range(length)])


def verify_child_dead(child, action, timeout):
    """
    Method to verify if pexpect child object was terminated, meaning that SC
    session was killed.
    Args:
        child (obj): pexpect child object.
        action (str): action performed on VM that should cause SC process
                      termination.
        timeout: amount of time to wait for child process to get eliminated.

    Raises:
        AssertionError: error is reproduced if serial console connection
                        remains active.
    """
    sample = True
    sampler = TimeoutingSampler(
        timeout, 5, child.isalive
    )
    try:
        for sample in sampler:
            if not sample:
                break
    except APITimeout:
        sample = True

    assert not sample, (
        'Serial console connection remains active after {action} action on '
        'VM.'.format(action=action)
    )


def generate_test_file_via_sc(child):
    """
    Method designed to generate a file on vm with random payload via SC using
    echo command on the VM.
    Args:
        child (obj): pexpect child object.

    Returns:
        str: returns text generated in test file.

    Raises:
        AssertionError: error is being reproduced if return code of command
                        execution is not equal zero.
    """
    random_text = generate_random_text(length=100)

    cmd = sc_conf.GEN_FILE_CMD.format(
        text=random_text,
        test_file=sc_conf.TEST_FILE
    )
    child.sendline(cmd.strip())
    child.sendcontrol('m')
    rc = child.expect('.*\#')
    assert rc == 0, (
        "Didn't receive console prompt after execution file generation "
        "command."
    )
    return random_text


def verify_sc(child):
    """
    Verify SC console works by comparing payload via ordinary ssh connection
    in file which was generated via SC.
    Args:
        child (obj): pexpect child object.

    Raises:
        AssertionError: error is reproduced if file with test data is not found
                        on the test VM, or content of file is not correct.
    """
    random_text = generate_test_file_via_sc(child)
    host_ip = hl_vms.get_vm_ip(sc_conf.SERIAL_CONSOLE_VM)
    vm_resource = rhevm_helpers.get_host_resource(
        ip=host_ip,
        password=sc_conf.SERIAL_CONSOLE_VM_PASSWORD
    )
    data = vm_resource.fs.read_file(path=sc_conf.TEST_FILE)
    assert re.search(random_text, data), (
        'Test file on VM does not contain expected information.'
    )


def get_prompt(child, authorize):
    """
    Method designed to get information if SC prompt was received during
    connection via SC attempt, with option to wait for prompt to appear.
    Args:
        child (obj): pexpect child object.
        authorize (bool): describes if authorization sequence is required,
                          yes if True, no if False.

    Returns:
        bool: True if SC login prompt was received, if not - False.
    """
    def prompt_activate():
        """
        Method designed to verify if 'Login:' prompt was retrieved, if not -
        will send 'enter' signal.
        Args:

        Returns:
            Bool: True if 'Login:' prompt was returned, else - False.
        """
        try:
            if authorize:
                ret_code = child.expect('.*ogin:', timeout=15)
            else:
                ret_code = child.expect('.*\#', timeout=15)
            if not ret_code:
                return True
        except pexpect.TIMEOUT:
            child.sendcontrol('m')
            return False

    sample = False
    timeout = 60
    sampler = TimeoutingSampler(
        timeout, 20, prompt_activate
    )

    try:
        for sample in sampler:
            if sample:
                break
    except APITimeout:
        sample = False
    return sample


def sc_ssh_connector(cmd, authorize):
    """
    Method designed to create connection object to VM via SC using pexpect
    python module.
    Args:
        cmd (list of strings): command to create connection via SC.
        authorize (bool): whether to authorize to VM via SC if True or not
                          if False.

    Returns:
        object: pexpect child object.
    """
    cmd = ' '.join(cmd)
    child = pexpect.spawn(cmd, ignore_sighup=False)

    prompt_dialogue_active = get_prompt(child, authorize)
    assert prompt_dialogue_active, 'Did not receive expected prompt.'

    if authorize:
        child.send(
            '{user_name}'.format(
                user_name=sc_conf.SERIAL_CONSOLE_VM_USER
            )
        )
        child.sendcontrol('m')
        rc = child.expect('.*assword:')
        assert rc == 0, "Didn't receive password prompt."
        child.send(
            '{password}'.format(
                password=sc_conf.SERIAL_CONSOLE_VM_PASSWORD
            )
        )
        child.sendcontrol('m')
        rc = child.expect('.*\#')
        assert rc == 0, "Didn't receive console prompt after login."
    return child


def generate_command(add_flag, remove_flag=None):
    """
    Method designed to generate command required to connect via SC to VM.
    Args:
        add_flag (list): list of flags (str) that should be added to initial SC
                         connection command.
        remove_flag (list): list of flags (str) that should removed from the
                            SC connection command.

    Returns:
        list: list of command elements.
    """
    cmd = copy.deepcopy(sc_conf.CONNECT_TO_CONSOLE_COMMAND)
    for cmd_value in add_flag:
        cmd.append(cmd_value)
    if remove_flag:
        for cmd_value in remove_flag:
            cmd.pop(cmd.index(cmd_value))
    return cmd
