import paramiko
import re
import subprocess
import logging
import os
import signal
from utilities.machine import Machine
import argparse

logger = logging.getLogger(__name__)


class Timeout():
    """Timeout class using ALARM signal."""
    class Timeout(Exception):
        pass

    def __init__(self, sec):
        self.sec = sec

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.raise_timeout)
        signal.alarm(self.sec)

    def __exit__(self, *args):
        signal.alarm(0)    # disable alarm

    def raise_timeout(self, *args):
        raise Timeout.Timeout()


class LogListener():
    """
    listener class, watch files for changes (look for requested pattern) and
    executes a command (given by the user).
    The file can be on your local machine or on a remote one.
    The command that should be executed can executed also,
    on your local machine or on a remote machine
    """

    def __init__(self, ip_for_files, username, password):
        self.ssh = None
        self.channel = None
        self.machine = None
        logger.info("Trying to open a channel to ip: %s with username %s "
                    "and password %s" % (ip_for_files, username, password))
        if not self.set_connection_for_remote(ip_for_files, username,
                                              password):
            raise Exception("No Channel opened")

    def set_connection_for_remote(self, ip, username, password):
        """
        Sets up a connection (ssh) and creates a channel for transfer data
        Return True if succeeded, otherwise False.
        """
        if ip:
            logger.info('connecting to remote machine %s ...', ip)
            self.machine = Machine(host=ip, user=username,
                                   password=password).util('linux')
            self.ssh = self.machine.ssh

            try:
                transport = self.ssh._getTransport()
                self.channel = transport.open_session()

            except paramiko.AuthenticationException, msg:
                logger.info("Can't SSH to IP %s due to exception %s", ip, msg)
                return False

            if not (self.ssh and self.channel):
                return False
            logger.info('Connection Success')
        return True

    def execute_command(self, run_locally, command_to_exec,
                        ip_for_execute_command=None,
                        remote_username=None, remote_password=None):
        """
        Executes command on a local or remote machine -
        if "ip_for_execute_command" is None then command will executes on the
        same host as the file
        """

        if not run_locally:
            if ip_for_execute_command:
                machine_for_command = Machine(host=ip_for_execute_command,
                                              user=remote_username,
                                              password=
                                              remote_password).util('linux')
            else:
                machine_for_command = self.machine

            logger.info("run command %s on ip %s", command_to_exec,
                        ip_for_execute_command)
            machine_for_command.runCmd(command_to_exec, timeout=90, bg=False,
                                       conn_timeout=90, cmd_list=False)

        else:
            try:
                logger.info("run command %s locally", command_to_exec)
                os.system(command_to_exec)
            except RuntimeError, ex:
                logger.info("Can't run command %s, exception is %s",
                            command_to_exec, ex)

    def watch_for_remote_changes(self, files_to_watch, regex):
        """
        method that runs "tail -f 'file_name'" command remotely

        return:
        - True if the regex is found
        - False otherwise

          execute the "tail -f" command through communication_
          components_list[1] (channel)
        """

        try:
            logger.info("run 'tail -f' command on file/s %s", files_to_watch)
            self.channel.exec_command("tail -f " + files_to_watch)
        except RuntimeError, ex:
            logger.info("Can't run command %s, exception is %s", "tail -f", ex)

        recv = ""
        while True:
            try:
                # receive the output from the channel
                recv = "".join([recv, self.channel.recv(1024)])
                reg = re.search(regex, recv)

                if reg:
                    logger.info("regex %s found..", regex)
                    return True

            except KeyboardInterrupt:
                self.channel.close()
                self.ssh.close()
                raise Exception("close connections")
        return False

    def watch_for_local_changes(self, files_to_watch, regex):
        """
        method that runs "tail -f 'file_name'" command locally

        return:
        - True if the regex is found
        - False otherwise
        """
        try:
            logger.info("run 'tail -f' command on file/s %s", files_to_watch)
            f = subprocess.Popen(['tail', '-F', files_to_watch,
                                  '| stdbuf -o0'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)

        except RuntimeError:
            logger.info("Can't run command %s on %s, exception is %s", 'tail',
                        files_to_watch, RuntimeError.message)
        recv = ""
        while True:
            try:
                line = f.stdout.readline()
                recv = "".join([recv, line])
                reg = re.search(regex, recv)

                if reg:
                    logger.info("regex %s found..", regex)
                    return True

            except KeyboardInterrupt:
                raise RuntimeError("Caught control-C")
        return False

    def watch_for_changes(self, run_locally, files_to_watch, regex):
        """
        method that runs "tail -f 'file_name'" command

        return:
        - True if the regex is found
        - False otherwise
        """
        logger.info("watching for regex: %s", regex)

        if not run_locally:
            logger.info("on remote machine")
            return self.watch_for_remote_changes(files_to_watch, regex)

        else:
            logger.info("on local machine")
            return self.watch_for_local_changes(files_to_watch, regex)


def watch_logs(files_to_watch, regex, command_to_exec, time_out=None,
               ip_for_files=None, username=None, password=None,
               ip_for_execute_command=None, remote_username=None,
               remote_password=None):
    """
    When importing this module, this function can be used to watch log file
    for specific event , and executes commands.

    Parameters:
        * files_to_watch - a list of full pathes of a files that need to be
        watched
        * regex - a regular expression that need to be watched for
        * command_to_exec - the command that need to execute when event in
        the file occurs
        * ip_for_files - in case that the files are located on a remote
        machine - the IP of that machine
        * username - the user name for the remote machine
        * password - the password for the remote machine
        * ip_for_execute_command - in case that the command needs to execute
        on remote machine - IP for
          that machine
        * remote_username - the user name for the remote machine that the
        command executes on
        * remote_password - the password for the remote machine that the
        command executes on

    Returns: True if the regex has found and the command was successfully
    executes, False otherwise

    -  In case that "ip_for_execute_command" is None -> assign "ip" to it so
       that
       the command will executes on same machine that the "files_to_watch"
       is on
    """

    run_locally = False
    if not ip_for_execute_command:
        if not ip_for_files:
            # indicates if the command should executes locally
            run_locally = True
        else:
            ip_for_execute_command = ip_for_files
        remote_username = username
        remote_password = password

    listener = LogListener(ip_for_files, username, password)

    found_regex = None
    try:
        if time_out:
            with Timeout(time_out):
                found_regex = listener.watch_for_changes(run_locally,
                                                         files_to_watch,
                                                         regex)
        else:
            found_regex = listener.watch_for_changes(run_locally,
                                                     files_to_watch,
                                                     regex)
    except Timeout.Timeout:
        logger.info("Timeout: Did not find regex %s in files %s",
                    regex,
                    files_to_watch)

    if found_regex:
        listener.execute_command(run_locally, command_to_exec,
                                 ip_for_execute_command,
                                 remote_username, remote_password)
    else:
        logger.debug("Didn't find regex %s in files %s" % (regex,
                                                           files_to_watch))


def main():
    """
    In case of manual execution -
    (files_to_watch,regex,command_to_exec,ip,username,password,
    ip_for_execute_command,remote_username,remote_password,time_out)

    1. in case of remote machine:
        - ip: the remote machine IP
        - username/password: authentication

    2. for all cases (local & remote)
        - files_to_watch: absolute path of the file that should be watched (
          start with "/")
        - regex: regular expression to look for
        - command_to_exec: the command that should be executed in case that
          the regex has found
        - ip_for_execute_command: the !!! IP !!! of the machine that the
          command should exec on
        - remote_username: username for the second machine
        - remote_password: password for the second machine
        - time_out: limited time for watching

    Options -
        * -m, --machine : if the file is on remote machine then '-m' followed
          by ip,username & password
          (e.g. -m 10.0.0.0 root P@SSW0RD)
        * -f,--files : option that followed by the absolute path of the files
          that need to watch for.
          each file should be preceded by -f separately
          (e.g. -f /var/log/vdsm/vdsm.log -f /tmp/my_log)
        * -r, --regex : option for regex (e.g. -r <REGULAR_EXPRESSION>)
        * -c, --command : followed by the command that should be executed in
          case of log event
          (e.g. -c 'ls -l') <- note that parameters with white space MUST be
          surrounds by " ' "
        * -M, --Machine : in case that the command should executes on
          different machine , this option followed
          by IP,username & password
          (e.g. -M 10.0.0.0 root P@SSW0RD)
        * -t, --timeout : limited time for watching
          (e.g. -t 3)

    """

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

    usage = "usage: %prog [options] arg1 arg2"
    parser = argparse.ArgumentParser(description='this function can be used '
                                                 'to watch log file for '
                                                 'specific event ,'
                                                 'and executes commands.')

    parser.add_argument("-m", "--machine", action="store", dest="ip", nargs=3,
                        help="if the file is on remote machine then '-m' "
                             "followed by ip,username & password",
                        default=(None, None, None))

    parser.add_argument("-f", "--file", action="append", dest="files_to_watch",
                        help="option that followed by "
                             "the absolute path of the "
                             "file that need to watch for, each file should "
                             "be preceded by -f separately",
                        default=[])

    parser.add_argument("-r", "--regex", action="store", type=re.compile,
                        dest="regex",
                        help="option for regex (e.g. -r <REGULAR_EXPRESSION>)")

    parser.add_argument("-c", "--command", action="store",
                        dest="command_to_exec",
                        help="followed by the command that should be executed "
                             "in case of log event")

    parser.add_argument("-M", "--Machine", action="store",
                        dest="ip_for_execute_command", nargs=3,
                        help="in case that the command should executes on "
                             "different machine , "
                             "this option followed by IP,username & password",
                        default=(None, None, None))

    parser.add_argument("-t", "--timeout", action="store", type=int,
                        dest="time_out",
                        help="limited time for watching")

    options = parser.parse_args()

    if len(options.files_to_watch) > 0 and options.regex and \
            options.command_to_exec:
        files_to_watch = " ".join(options.files_to_watch)
        regex = options.regex
        command_to_exec = options.command_to_exec
    else:
        raise RuntimeError("Missing arguments! usage : %s", usage)

    time_out = options.time_out

    ip_for_execute_command = None
    ip = None

    if options.ip:
        ip, username, password = options.ip

    if options.ip_for_execute_command:
        ip_for_execute_command, remote_username, remote_password = \
            options.ip_for_execute_command

    logger.info("start watching...")
    watch_logs(files_to_watch, regex.pattern, command_to_exec,
               time_out=time_out,
               ip_for_files=ip, username=username,
               password=password,
               ip_for_execute_command=ip_for_execute_command,
               remote_username=remote_username,
               remote_password=remote_password)

    logger.info("Done !!!")

if __name__ == '__main__':
    main()
