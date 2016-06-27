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

import os
import tempfile
import logging
from utilities.machine import Machine

logger = logging.getLogger("art.ll_lib.hooks")

CHMOD = "/bin/chmod"


def checkForFileExistenceAndContent(positive, ip, password, filename,
                                    content=None, user='root'):
    '''
    Checks for file existence and content on given address
    Author: jvorcak
    Parameters:
       * ip - address of the machine
       * password - password for accessing the machine
       * filename - file name
       * content - content of the remote file
       * user - username for accessing the machine
    '''

    vm = Machine(ip, user, password).util('linux')
    new_filename = tempfile.gettempdir() + os.sep + os.path.basename(filename)

    if not vm.copyFrom(filename, new_filename):
        logger.error("Couldn't copy filename %s from address %s", filename, ip)
        return False

    if content:
        content = content.strip()
        with open(new_filename, "r") as f:
            file_content = f.read().strip()

        if file_content != content:
            logger.error("Content of the file differs from expected content")
            logger.error("Expected content: %s" % content)
            logger.error("Actual content: %s" % file_content)
            return False

    return positive


def createOneLineShellScript(ip, password, scriptName, command,
                             arguments, target, user='root', osType='linux'):
    '''
    This function creates a shell script with the given command and args.
    Author: talayan
    Parameters:
       * ip - IP of the machine where the script should be injected.
       * password - the users' password to connect to the machine
       * scriptName - the name of the file to be created
       * command - the command which the script file will hold
       * arguments - the args for the command
       * target - target directory to place the script on the destination
                  machine
       * user - username to access the destination machine
       * osType - Type of the destination machine
    '''
    with open(scriptName, 'w+') as fd:
        fd.write('''#!/bin/bash\n%s %s\n''' % (command, arguments))
    try:
        host = Machine(ip, user, password).util(osType)
        host.copyTo(scriptName, target, 300)
    except IOError as err:
        logger.error("Copy data to %s : %s" % (ip, err))
    except Exception as err:
        logger.error("Oops! something went wrong in"
                     " connecting or copying data to %s" % (ip, err))
    cmd = [CHMOD, "755", os.path.join(target, scriptName)]
    host.runCmd(cmd)

    return True


def createPythonScriptToVerifyCustomHook(ip, password, scriptName, customHook,
                                         target, outputFile, user='root',
                                         osType='linux'):
    """
    This function creates an ad-hoc python script which creates
     a file on host to test hook mechanism.
    Author: talayan
    Parameters:
       * ip - IP of the machine where th script should be injected.
       * password - the users' password to connect to the machine
       * scriptName - the name of the file to be created
       * customHook - the name of the custom hook that we are willing to test
       * target - target directory to place
          the script on the destination machine
       * outputFile - the name and path where the file to be created
       * user - username to access the destination machine
       * osType - Type of the destination machine
    """
    with open(scriptName, 'w+') as fd:
        fd.write("""#!/usr/bin/python\nimport os\n"""
                 """with open("%s", 'w') as fo:\n"""
                 """\tfo.write(os.environ['%s'])\n"""
                 % (outputFile, customHook))
    try:
        host = Machine(ip, user, password).util(osType)
        host.copyTo(scriptName, target, 300)
    except IOError as err:
        logger.error("Copy data to %s : %s" % (ip, err))
    except Exception as err:
        logger.error("Oops! something went wrong "
                     "in connecting or copying data to %s" % (ip, err))

    cmd = [CHMOD, "755", os.path.join(target, scriptName)]
    host.runCmd(cmd)

    return True
