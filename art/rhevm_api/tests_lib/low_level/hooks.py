#!/usr/bin/env python2.7

# Copyright (C) 2010-2016 Red Hat, Inc.
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

logger = logging.getLogger("art.ll_lib.hooks")


def check_for_file_existence_and_content(
        positive, host,
        filename, content=None,
):
    """
    Description:
        Checks for file existence and content equality on given host.
    Args:
        positive (bool): Expected result.
        host (Host): Host object.
        filename (str): File name on host.
        content (str): Expected content of the remote file.
    Returns:
        bool: True if there were no errors checking file existence.
    """
    new_filename = path.join(tempfile.gettempdir(), path.basename(filename))

    try:
        host.fs.get(filename, new_filename)
    except IOError as err:
        logger.error(err)
        return False

    if content:
        content = content.strip()
        with open(new_filename, "r") as f:
            file_content = f.read().strip()

        if file_content != content:
            logger.error(
                (
                    "Content of the file differs from expected content:\n"
                    "\tExpected content: {0}"
                    "\tActual content: {1}"
                ).format(content, file_content)
            )
            return False

    return positive


def create_one_line_shell_script(
        host, script_name,
        command, arguments, target
):
    """
    Description:
        Creates a shell script with the given command and args.
    Args:
        host (Host): Host object.
        script_name (str): Name of the scrip file to be created.
        command (str): Command the script file will hold.
        arguments (str): Args for the script's command.
        target (str): Target directory to place the script on the remote host.
    Returns:
        bool: True if script was created successfully, False if there were
        any errors.
    """
    content = (
        "#!/usr/bin/env bash\n\n"
        "{0} {1}\n"
    ).format(command, arguments)

    try:
        script_path = path.join(target, script_name)
        host.fs.create_script(content, script_path)
        return True
    except Exception as err:
        logger.error(err)
        return False


def create_python_script_to_verify_custom_hook(
        host, script_name,
        custom_hook, target, output_file
):
    """
    Description:
        This function creates an ad-hoc python script which creates
        a file on host to test hook mechanism.
    Args:
        host (Host): Host object.
        script_name (str): Name of the file to be created.
        custom_hook (str): Name of the custom hook will be testing.
        target (str): Target directory to place the script on the remote host.
        output_file (str): Name and path where the file will be created.
    Returns:
        bool: True if script was created successfully and False otherwise.
    """

    content = (
        "#!/usr/bin/python\n\n"
        "import os\n"
        "import sys\n"
        "if os.environ.has_key(\"{1}\"):\n"
        "\twith open(\"{0}\", \"w\") as fo:\n"
        "\t\tfo.write(os.environ[\"{1}\"])\n"
        "else:\n"
        "\tsys.exit(0)\n"
    ).format(output_file, custom_hook)

    try:
        script_path = path.join(target, script_name)
        host.fs.create_script(content, script_path)
        return True
    except Exception as err:
        logger.error(err)
        return False
