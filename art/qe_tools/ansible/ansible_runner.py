import os
import logging
from subprocess import Popen, PIPE, list2cmdline
from threading import Thread
from Queue import Queue
from time import sleep

logger = logging.getLogger("Ansible-runner")

WORKSPACE = os.environ.get("WORKSPACE")
LOG_FILE = os.path.join(WORKSPACE, "logs/ansible_runner.log")


class ThreadSafeExecutor(object):

    def __init__(self, env={}, commands=[]):
        self.closed = False
        self.rc = 0
        self.env = env
        self.flushed_queues = False
        self.commands = commands
        self.proc = Popen(
            ['/usr/bin/bash', '-e'], env=self.env, stdout=PIPE, stderr=PIPE,
            stdin=PIPE, bufsize=1, close_fds=True
        )
        self.q_out = Queue()
        self.q_err = Queue()

    def close(self):
        """
        Close Popen process, wait till ends and return its RC

        Retruns (int): RC of last command sent to process
        """
        self.proc.stdin.close()
        self.closed = True
        return self.proc.wait()

    def empty_queues(self):
        """
        Check if both queues for stdout and stderr are clean.

        Returns (boolean): True if queues are clean False otherwise.
        """
        for queue in (self.q_out, self.q_err):
            if not queue.empty():
                return False
        return True

    def wait_till_empty_queues(self):
        """
        Wait till stderr and stdout queues are empty.
        """
        while not self.empty_queues():
            sleep(5)

    def cmd_to_stdin(self, cmd):
        """
        Send command to stdin of proc.

        Args:
            cmd (str): command you would like to run in string.
        """
        global last_command
        print "Executing cmd: %s" % cmd
        self.proc.stdin.write(cmd + "\n")

    def enqueue_output(self, out, queue):
        """
        Read stdout/stderr output from process and put it to the queue.

        Args:
            out (file): stdout/stderr of Popen process
            queue (Queue): instance of the Queue object where to put output
        """
        for line in iter(out.readline, b''):
            queue.put(line)
            if self.flushed_queues:
                break

    def __enter__(self):
        self.t_out = Thread(
            target=self.enqueue_output, args=(self.proc.stdout, self.q_out)
        )
        self.t_err = Thread(
            target=self.enqueue_output, args=(self.proc.stderr, self.q_err)
        )
        self.t_out.daemon = True
        self.t_err.daemon = True
        self.t_out.start()
        self.t_err.start()
        for cmd in self.commands:
            self.cmd_to_stdin(cmd)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.closed:
            self.rc = self.close()
        self.wait_till_empty_queues()
        self.flushed_queues = True


def _run_local_cmd(cmd, workspace=WORKSPACE):
    """
    Run command on local machine.

    Args:
        cmd (list): command in list like ['rm', '-f', '/path/to/remove'].
        workspace (str): Path to workspace.
    Return:
        tuple: (RC, OUT, ERR)
    """

    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, cwd=workspace)
    logger.info("Executing local cmd: %s", list2cmdline(cmd))
    out, err = proc.communicate()
    if proc.returncode:
        logger.error(
            "Failed to exec cmd %s: RC=%s, out=%s, err=%s",
            list2cmdline(cmd), proc.returncode, out, err
        )
    return proc.returncode, out, err


def prepare_env_group_vars(product, version):
    """
    Copy group vars from ansible-playbooks/variables/{product}-{version} into
    groupvars folder in workspace.

    Args:
        product (str): Product name.
        version (str): Version of product.
    Returns:
        bool: True if successfully, False otherwise.
    """

    cmd_rm_groupvars = [
        "rm", "-rf", "group_vars"
    ]
    cmd = [
        "cp", "-rf", "ansible-playbooks/variables/{product}-{version}".format(
            product=product, version=version
        ), "group_vars"
    ]
    _run_local_cmd(cmd_rm_groupvars)
    rc, _, _ = _run_local_cmd(cmd)
    if rc:
        return False
    return True


def read_queue_and_log(queue, lines, tse, level="info"):
    """
    Reader of stdout/stderr from queue. This is the place where we can later do
    whatever we want to do with ansible output.. for now we just write to logs
    to proper logger and fill lines list with output.

    Args:
        queue (Queue): Queue to read output from.
        lines (list): list where to put output from queue
        tse (ThreadSafeExecutor): object of ThreadSafeExecutor
        level (str): logg level where to put output
    """
    while not tse.flushed_queues:
        if queue.empty():
            continue
        line = queue.get()
        lines.append(line)
        if level == "info":
            logger.info(line)
        elif level == "error":
            logger.error(line)
        queue.task_done()


def run_ansible_playbook(
    playbook, ansible_params="", inventory="./inventory",
    workspace=WORKSPACE, log_file=LOG_FILE
):
    """
    Run ansible playbook in different shell. It expcect that .ansible virtual
    env and ansible-playbooks/run-playbook.sh exist in workspace.

    Args:
        playbook (str): Path to playbook.
        ansible_params (str): Parameters for ansible.
        inventory (str): Path to inventory file (default: ./inventory).
        workspace (str): Path to workspace.
        log_file (str): Path to logfile
    """

    env = {
        'WORKSPACE': workspace,
        'HOME': '/root',
        'ANSIBLE_HOST_KEY_CHECKING': 'False',
        "ANSIBLE_LOG_PATH": log_file,
    }
    run_ansible_cmd = (
        "bash ansible-playbooks/run-playbook.sh {playbook} {inventory} "
        "{ansible_params}"
    )

    with ThreadSafeExecutor(env) as tse:
        out_lines = []
        err_lines = []
        t_out_reader = Thread(
            target=read_queue_and_log,
            args=(tse.q_out, out_lines, tse, "info")
        )
        t_err_reader = Thread(
            target=read_queue_and_log,
            args=(tse.q_err, err_lines, tse, "error")
        )
        t_out_reader.daemon = True
        t_err_reader.daemon = True
        t_out_reader.start()
        t_err_reader.start()
        tse.cmd_to_stdin("source .ansible/bin/activate")
        tse.cmd_to_stdin(
            run_ansible_cmd.format(
                playbook=playbook, ansible_params=ansible_params,
                inventory=inventory
            )
        )
    out = "".join(out_lines)
    err = "".join(err_lines)

    return tse.rc, out, err
