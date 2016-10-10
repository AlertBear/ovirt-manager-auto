#!/usr/bin/env python

# Copyright (C) 2010 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

import logging
import tempfile

from os import path

from utilities.machine import Machine

logger = logging.getLogger("art.ll_lib.hooks")

CHMOD = "/bin/chmod"


def check_for_file_existence_and_content(
        positive, ip, password,
        filename, content=None,
        user="root"
):
    """
    Checks for file existence and content on given address
    Author: jvorcak
    Args:
        positive (bool): expected result
        ip (str): address of the machine
        password (str): password for accessing th machine
        filename (str): file name
        content (str): expected content of the remote file
    Kwargs:
        user (str): username for accessing the machine
    Returns:
        bool. True if there were no errors while checking file existence
    """
    vm = Machine(ip, user, password).util("linux")

    new_filename = path.join(tempfile.gettempdir(), path.basename(filename))

    if not vm.copyFrom(filename, new_filename):
        logger.error("Couldn't copy filename %s from address %s", filename, ip)
        return False

    if content:
        content = content.strip()
        with open(new_filename, "r") as f:
            file_content = f.read().strip()

        if file_content != content:
            logger.error(
                (
                    "Content of the file differs from expected content:"
                    "\tExpected content: {0}"
                    "\tActual content: {1}"
                ).format(content, file_content)
            )
            return False

    return positive


def create_one_line_shell_script(
        ip, password, script_name,
        command, arguments, target,
        user="root", os_type="linux"
):
    """
    This function creates a shell script with the given command and args.
    Author: talayan
    Args:
        ip (str): IP of the machine where the script should be injected.
        password (str): the users' password to connect to the machine
        script_name (str): the name of the file to be created
        command (str): the command which the script file will hold
        arguments (str): the args for the command
        target (str): target directory to place the script on the destination
        host
    Kwargs:
        user (str): username to access the destination machine
        os_type (str): Type of the destination machine
    Returns:
        bool. True if script was created successfully, False if there were
            any errors
    """
    content = (
        "#!/usr/bin/env bash\n\n"
        "{0} {1}\n"
    ).format(command, arguments)

    with open(script_name, "w+") as fd:
        fd.write(content)
    try:
        host = Machine(ip, user, password).util(os_type)
        host.copyTo(script_name, target, 300)
        cmd = [CHMOD, "755", path.join(target, script_name)]
        host.runCmd(cmd)

        return True

    except IOError as err:
        logger.error("Copy data to %s : %s", ip, err)

    except Exception as err:
        logger.error(
            "Oops! something went wrong in"
            " connecting or copying data to %s : %s",
            ip,
            err
        )
    return False


def create_python_script_to_verify_custom_hook(
        ip, password, script_name,
        custom_hook, target, output_file,
        user="root", os_type="linux"
):
    """
    This function creates an ad-hoc python script which creates
     a file on host to test hook mechanism.
    Author: talayan
    Args:
        ip (str): IP of the machine where th script should be injected
        password (str): the users' password to connect to the machine
        script_name (str): the name of the file to be created
        custom_hook (str): the name of the custom hook will testing
        target (str): target directory to place the script on the destination
            machine
        output_file (str): the name and path where the file to be created
    Kwargs:
        user (str): username to access the destination machine
        os_type (str): Type of the destination machine
    Returns:
        bool. True if script was created successfully and False if there were
            any errors
    """

    content = (
        "#!/usr/bin/env python2\n\n"
        "import os\n\n"
        "with open(\"{0}\", \"w\") as fo:\n"
        "\tfo.write(os.environ[\"{1}\"])\n"
    ).format(output_file, custom_hook)

    with open(script_name, "w+") as fd:
        fd.write(content)
    try:
        host = Machine(ip, user, password).util(os_type)
        host.copyTo(script_name, target, 300)
        cmd = [CHMOD, "755", path.join(target, script_name)]
        host.runCmd(cmd)

        return True

    except IOError as err:
        logger.error("Copy data to %s : %s", ip, err)

    except Exception as err:
        logger.error(
            "Oops! something went wrong "
            "in connecting or copying data to %s : %s",
            ip,
            err
        )
    return False
