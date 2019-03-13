import glob
import os
import sys

import stat
import subprocess
import json
import tempfile

from argparse import ArgumentParser
from traceback import format_exc

DESCRIPTION = 'Run an experiment as described in a BLUEFILE.'
JSON_INDENT = 2


def attach_args(parser):
    parser.add_argument(
        'blue_file', action='store', type=str, metavar='BLUEFILE',
        help='BLUEFILE (json) containing an experiment description as local PATH or http URL.'
    )
    parser.add_argument(
        '-o', '--outputs', action='store_true',
        help='Enable connectors specified in the RED FILE outputs section.'
    )
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help='Write debug info, including detailed exceptions, to stdout.'
    )
    parser.add_argument(
        '--leave-directories', action='store_true',
        help='Leave temporary inputs and working directories.'
    )


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    attach_args(parser)
    args = parser.parse_args()

    result = run(**args.__dict__)

    if args.__dict__.get('debug'):
        print(json.dumps(result, indent=JSON_INDENT))

    if result['state'] == 'succeeded':
        return 0

    return 1


def run(blue_file, outputs, leave_directories, **_):
    del leave_directories
    result = {
        'command': None,
        'inputFiles': None,
        'process': None,
        'outputFiles': None,
        'debugInfo': None,
        'state': 'succeeded'
    }

    connector_manager = ConnectorManager()
    try:
        with open(blue_file, 'r') as f:
            blue_data = json.load(f)

        working_dir = blue_data['workDir']
        create_working_dir(working_dir)

        if not outputs and 'outputs' in blue_data:
            del blue_data['outputs']

        if outputs and 'outputs' not in blue_data:
            raise AssertionError('-o/--outputs argument is set, \
            but no outputs section with RED connector settings is defined in REDFILE')

        # import, validate and execute connectors
        connector_manager.import_input_connectors(blue_data['inputs'])
        if outputs:
            connector_manager.import_output_connectors(blue_data['outputs'], blue_data['cli']['outputs'])

        connector_manager.prepare_directories()
        connector_manager.validate_connectors()
        connector_manager.receive_connectors()

        # execute command
        command = blue_data['command']
        execution_result = execute(command, work_dir=working_dir)
        if not execution_result.successful():
            raise ExecutionError('Execution of command "{}" failed with the following message:\n{}'
                                 .format(' '.join(command), execution_result.get_std_err()))

        # send files and directories
        connector_manager.send_connectors(working_dir)

    except Exception as e:
        print_exception(e)
        result['debugInfo'] = exception_format()
        result['state'] = 'failed'
        for i in result['debugInfo']:
            print(i, file=sys.stderr)
        print('', file=sys.stderr)
        sys.stderr.flush()
    finally:
        # umount directories
        connector_manager.umount_connectors()

    return result


def create_working_dir(working_dir):
    """
    Tries to create the working directory for the executed process.
    :param working_dir: The directory where to execute the main command and from where to search output-files.
    :raise Exception: If working_dir could not be created
    """
    try:
        ensure_directory(working_dir)
    except FileExistsError:
        raise FileExistsError('Could not create working dir "{}", because it already exists and is not empty.'
                              .format(working_dir))
    except PermissionError as e:
        raise PermissionError('Failed to create working_dir "{}", because of insufficient permissions.\n{}'
                              .format(working_dir, str(e)))


def ensure_directory(d):
    """
    Ensures that directory d exists, is empty and is writable
    :param d: The directory that you want to make sure is either created or exists already.
    :raise PermissionError: If
    """
    if os.path.exists(d):
        if os.listdir(d):
            raise FileExistsError('Directory "{}" already exists and is not empty.')
        else:
            return
    os.makedirs(d)

    # check write permissions
    st = os.stat(d)
    user_has_permissions = bool(st.st_mode & stat.S_IRUSR) and bool(st.st_mode & stat.S_IWUSR)
    group_has_permissions = bool(st.st_mode & stat.S_IRGRP) and bool(st.st_mode & stat.S_IWGRP)
    others_have_permissions = bool(st.st_mode & stat.S_IROTH) and bool(st.st_mode & stat.S_IWOTH)

    if (not user_has_permissions) and (not group_has_permissions) and (not others_have_permissions):
        raise PermissionError('Directory "{}" is not writable.'.format(d))


def resolve_connector_cli_version(connector_command):
    """
    Returns the cli-version of the given connector.
    :param connector_command: The connector command to resolve the cli-version for.
    :return: The cli version string of the given connector
    :raise ConnectorError: If the cli-version could not be resolved.
    """
    try:
        result = execute([connector_command, 'cli-version'])
    except FileNotFoundError:
        raise ConnectorError('Could not find connector "{}"'.format(connector_command))

    std_out = result.std_out
    if result.successful() and len(std_out) == 1:
        return std_out[0]
    else:
        std_err = result.get_std_err()
        raise ConnectorError('Could not detect cli version for connector "{}". Failed with following message:\n{}'
                             .format(connector_command, std_err))


def execute_connector(connector_command, top_level_argument, access=None, path=None, listing=None):
    """
    Executes the given connector command with
    :param connector_command: The connector command to execute
    :param top_level_argument: The top level argument of the connector
    :param access: An access dictionary, if given the connector is executed with a temporary file as argument, that
    contains the access information
    :param path: The path where to receive the file/directory to or which file/directory to send
    :param listing: An optional listing, that is given to the connector as temporary file
    :return: A dictionary with keys 'returnCode', 'stdOut', 'stdErr'
    """
    # create access file
    access_file = None
    if access is not None:
        access_file = tempfile.NamedTemporaryFile('w')
        json.dump(access, access_file)
        access_file.flush()

    # create listing file
    listing_file = None
    if listing is not None:
        listing_file = tempfile.NamedTemporaryFile('w')
        json.dump(listing, listing_file)
        listing_file.flush()

    # build command
    command = [connector_command, top_level_argument]
    if access_file is not None:
        command.append('{}'.format(access_file.name))
    if path is not None:
        command.append('{}'.format(path))
    if listing_file is not None:
        command.append('--listing={}'.format(listing_file.name))

    # execute connector
    execution_result = execute(command)

    # remove temporary files
    if access_file is not None:
        access_file.close()
    if listing_file is not None:
        listing_file.close()

    return execution_result


class InputConnectorRunner:
    """
    A ConnectorRunner can be used to execute the different functions of a Connector.

    A ConnectorRunner subclass is associated with a connector cli-version.
    Subclasses implement different cli-versions for connectors.

    A ConnectorRunner instance is associated with a blue input, that uses a connector.
    For every blue input, that uses a connector a new ConnectorRunner instance is created.
    """

    def __init__(self, input_key, connector_command, input_class, mount, access, path, listing=None):
        """
        Initiates an InputConnectorRunner.

        :param input_key: The blue input key
        :param connector_command: The connector command to execute
        :param input_class: Either 'File' or 'Directory'
        :param mount: Whether the associated connector mounts or not
        :param access: The access information for the connector
        :param path: The path where to put the data
        :param listing: An optional listing for the associated connector
        """
        self._input_key = input_key
        self._connector_command = connector_command
        self._input_class = input_class
        self._mount = mount
        self._access = access
        self._path = path
        self._listing = listing

        # Is set to true, after mounting
        self._has_mounted = False

    def is_mounting(self):
        """
         :return: Returns whether this runner is mounting or not.
        """
        return self._mount

    def prepare_directory(self):
        """
        In case of input_class == 'Directory' creates path.
        In case of input_class == 'File' creates os.path.dirname(path).
        :raise ConnectorError: If the directory could not be created or if the path already exist.
        """
        path_to_create = self._path if self._input_class == 'Directory' else os.path.dirname(self._path)

        try:
            ensure_directory(path_to_create)
        except PermissionError as e:
            raise ConnectorError('Could not prepare directory for input key "{}" with path "{}". PermissionError:\n{}'
                                 .format(self._input_key, path_to_create, str(e)))
        except FileExistsError as e:
            raise ConnectorError('Could not prepare directory for input key "{}" with path "{}". '
                                 'Directory already exists and is not empty.\n{}'
                                 .format(self._input_key, path_to_create, str(e)))

    def validate_receive(self):
        """
        Executes receive_file_validate, receive_dir_validate or mount_dir_validate depending on input_class and mount
        """
        if self._input_class == 'Directory':
            if self._mount:
                self.mount_dir_validate()
            else:
                self.receive_dir_validate()
        elif self._input_class == 'File':
            self.receive_file_validate()

    def receive(self):
        """
        Executes receive_file, receive_directory or receive_mount depending on input_class and mount
        """
        if self._input_class == 'Directory':
            if self._mount:
                self.mount_dir()
                self._has_mounted = True
            else:
                self.receive_dir()
        elif self._input_class == 'File':
            self.receive_file()

    def try_umount(self):
        """
        Executes umount, if connector is mounting and has mounted, otherwise does nothing.
        """
        if self._mount and self._has_mounted:
            self.umount_dir()

    def receive_file(self):
        raise NotImplementedError()

    def receive_file_validate(self):
        raise NotImplementedError()

    def receive_dir(self):
        raise NotImplementedError()

    def receive_dir_validate(self):
        raise NotImplementedError()

    def mount_dir_validate(self):
        raise NotImplementedError()

    def mount_dir(self):
        raise NotImplementedError()

    def umount_dir(self):
        raise NotImplementedError()


class OutputConnectorRunner:
    """
    A OutputConnectorRunner can be used to execute different output functions of a Connector.

    A ConnectorRunner subclass is associated with a connector cli-version.
    Subclasses implement different cli-versions for connectors.

    A ConnectorRunner instance is associated with a blue input, that uses a connector.
    For every blue input, that uses a connector a new ConnectorRunner instance is created.
    """

    def __init__(self, output_key, connector_command, output_class, access, glob_pattern, listing=None):
        """
        initiates a OutputConnectorRunner.

        :param output_key: The blue output key
        :param connector_command: The connector command to execute
        :param output_class: Either 'File' or 'Directory'
        :param access: The access information for the connector
        :param glob_pattern: The glob_pattern to match
        :param listing: An optional listing for the associated connector
        """
        self._output_key = output_key
        self._connector_command = connector_command
        self._output_class = output_class
        self._access = access
        self._glob_pattern = glob_pattern
        self._listing = listing

    def validate_send(self):
        """
        Executes send_file_validate, send_dir_validate or send_mount_validate depending on input_class and mount
        """
        if self._output_class == 'Directory':
            self.send_dir_validate()
        elif self._output_class == 'File':
            self.send_file_validate()

    def _resolve_glob_pattern(self, working_dir):
        """
        Tries to resolve the given glob_pattern.
        :param working_dir: The working dir from where to access output files
        :return: the resolved glob_pattern
        :raise ConnectorError: If the given glob_pattern could not be resolved or is ambiguous
        """
        glob_pattern = os.path.join(working_dir, self._glob_pattern)
        paths = glob.glob(glob_pattern)
        if len(paths) == 1:
            return paths[0]
        elif len(paths) == 0:
            raise ConnectorError('Could not resolve glob "{}" for output key "{}". File/Directory not found.'
                                 .format(glob_pattern, self._output_key))
        else:
            raise ConnectorError('Could not resolve glob "{}" for output key "{}". Glob is ambiguous.'
                                 .format(glob_pattern, self._output_key))

    def try_send(self, working_dir):
        """
        Executes send_file or send_dir depending on input_class.
        :param working_dir: The working dir from where to access output files
        :raise ConnectorError: If the given glob_pattern could not be resolved or is ambiguous.
                               Or if the executed connector fails.
        """
        path = self._resolve_glob_pattern(working_dir)
        if self._output_class == 'File':
            self.send_file(path)
        elif self._output_class == 'Directory':
            self.send_dir(path)

    def send_file_validate(self):
        raise NotImplementedError()

    def send_file(self, path):
        raise NotImplementedError()

    def send_dir_validate(self):
        raise NotImplementedError()

    def send_dir(self, path):
        raise NotImplementedError()


class InputConnectorRunner01(InputConnectorRunner):
    """
    This InputConnectorRunner implements the connector cli-version 0.1
    """

    def receive_file(self):
        execution_result = execute_connector(self._connector_command,
                                             'receive-file',
                                             access=self._access,
                                             path=self._path)

        if not execution_result.successful():
            raise ConnectorError('Connector failed to receive file for input key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._input_key, execution_result.get_std_err()))

    def receive_file_validate(self):
        execution_result = execute_connector(self._connector_command,
                                             'receive-file-validate',
                                             access=self._access)
        if not execution_result.successful():
            raise ConnectorError('Connector failed to validate receive file for input key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._input_key, execution_result.std_err))

    def receive_dir(self):
        execution_result = execute_connector(self._connector_command,
                                             'receive-dir',
                                             access=self._access,
                                             path=self._path,
                                             listing=self._listing)

        if not execution_result.successful():
            raise ConnectorError('Connector failed to receive directory for input key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._input_key, execution_result.get_std_err()))

    def receive_dir_validate(self):
        execution_result = execute_connector(self._connector_command,
                                             'receive-dir-validate',
                                             access=self._access,
                                             listing=self._listing)

        if not execution_result.successful():
            raise ConnectorError('Connector failed to validate receive directory for input key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._input_key, execution_result.get_std_err()))

    def mount_dir(self):
        execution_result = execute_connector(self._connector_command,
                                             'mount-dir',
                                             access=self._access,
                                             path=self._path)

        if not execution_result.successful():
            raise ConnectorError('Connector failed to mount directory for input key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._input_key, execution_result.get_std_err()))

    def mount_dir_validate(self):
        execution_result = execute_connector(self._connector_command,
                                             'mount-dir-validate',
                                             access=self._access)

        if not execution_result.successful():
            raise ConnectorError('Connector failed to validate mount directory for input key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._input_key, execution_result.get_std_err()))

    def umount_dir(self):
        execution_result = execute_connector(self._connector_command,
                                             'umount-dir', path=self._path)

        if not execution_result.successful():
            raise ConnectorError('Connector failed to umount directory for input key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._input_key, execution_result.get_std_err()))


class OutputConnectorRunner01(OutputConnectorRunner):
    """
    This OutputConnectorRunner implements the connector cli-version 0.1
    """

    def send_file(self, path):
        execution_result = execute_connector(self._connector_command,
                                             'send-file',
                                             access=self._access,
                                             path=path)

        if not execution_result.successful():
            raise ConnectorError('Connector failed to send file for output key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._output_key, execution_result.get_std_err()))

    def send_file_validate(self):
        execution_result = execute_connector(self._connector_command,
                                             'send-file-validate',
                                             access=self._access)

        if not execution_result.successful():
            raise ConnectorError('Connector failed to validate send file for output key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._output_key, execution_result.get_std_err()))

    def send_dir(self, path):
        execution_result = execute_connector(self._connector_command,
                                             'send-dir',
                                             access=self._access,
                                             path=path,
                                             listing=self._listing)

        if not execution_result.successful():
            raise ConnectorError('Connector failed to validate send file for output key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._output_key, execution_result.get_std_err()))

    def send_dir_validate(self):
        execution_result = execute_connector(self._connector_command,
                                             'send-dir-validate',
                                             access=self._access,
                                             listing=self._listing)

        if not execution_result.successful():
            raise ConnectorError('Connector failed to validate send directory for output key "{}".\n'
                                 'Failed with the following message:\n{}'
                                 .format(self._output_key, execution_result.get_std_err()))


CONNECTOR_CLI_VERSION_INPUT_RUNNER_MAPPING = {
    '0.1': InputConnectorRunner01,
}


def create_input_connector_runner(input_key, input_value):
    """
    Creates a proper InputConnectorRunner instance for the given connector command.

    :param input_key: The input key of the runner
    :param input_value: The input to create an runner for
    :return: A ConnectorRunner
    """
    connector_data = input_value['connector']
    connector_command = connector_data['command']
    cli_version = resolve_connector_cli_version(connector_command)
    mount = connector_data.get('mount', False)
    access = connector_data['access']

    input_class = input_value['class']
    path = input_value['path']
    listing = input_value.get('listing')

    if mount and input_class != 'Directory':
        raise ConnectorError('Connector for input key "{}" has mount flag set but class is "{}". '
                             'Unable to mount if class is different from "Directory"'
                             .format(input_key, input_class))

    connector_runner_class = CONNECTOR_CLI_VERSION_INPUT_RUNNER_MAPPING.get(cli_version)
    if connector_runner_class is None:
        raise Exception('This agent does not support connector cli-version "{}", but needed by connector "{}"'
                        .format(cli_version, connector_command))

    connector_runner = connector_runner_class(input_key,
                                              connector_command,
                                              input_class,
                                              mount,
                                              access,
                                              path,
                                              listing)

    return connector_runner


CONNECTOR_CLI_VERSION_OUTPUT_RUNNER_MAPPING = {
    '0.1': OutputConnectorRunner01,
}


def create_output_connector_runner(output_key, output_value, cli_output_value):
    """
    Creates a proper OutputConnectorRunner instance for the given connector command.

    :param output_key: The output key of the runner
    :param output_value: The output to create a runner for
    :param cli_output_value: The cli description for the runner
    :return: A ConnectorRunner
    """
    connector_data = output_value['connector']
    connector_command = connector_data['command']
    cli_version = resolve_connector_cli_version(connector_command)
    mount = connector_data.get('mount', False)
    access = connector_data['access']

    output_class = output_value['class']
    glob_pattern = cli_output_value['outputBinding']['glob']
    listing = output_value.get('listing')

    if mount and output_class != 'Directory':
        raise ConnectorError('Connector for input key "{}" has mount flag set but class is "{}". '
                             'Unable to mount if class is different from "Directory"'
                             .format(output_key, output_class))

    connector_runner_class = CONNECTOR_CLI_VERSION_OUTPUT_RUNNER_MAPPING.get(cli_version)
    if connector_runner_class is None:
        raise Exception('This agent does not support connector cli-version "{}", but needed by connector "{}"'
                        .format(cli_version, connector_command))

    connector_runner = connector_runner_class(output_key,
                                              connector_command,
                                              output_class,
                                              access,
                                              glob_pattern,
                                              listing)

    return connector_runner


class ExecutionResult:
    def __init__(self, std_out, std_err, return_code):
        """
        Initializes a new ExecutionResult
        :param std_out: The std_err of the execution as list of strings
        :param std_err: The std_out of the execution as list of strings
        :param return_code: The return code of the execution
        """
        self.std_out = std_out
        self.std_err = std_err
        self.return_code = return_code

    def get_std_err(self):
        return '\n'.join(self.std_err)

    def get_std_out(self):
        return '\n'.join(self.std_out)

    def successful(self):
        return self.return_code == 0


def _exec(command, shell, work_dir):
    try:
        sp = subprocess.Popen(command,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              shell=shell,
                              cwd=work_dir,
                              universal_newlines=True,
                              encoding='utf-8')
    except TypeError:
        sp = subprocess.Popen(command,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              shell=shell,
                              cwd=work_dir,
                              universal_newlines=True)
    return sp


def execute(command, shell=False, work_dir=None):
    """
    Executes a given commandline command and returns a dictionary with keys: 'returnCode', 'stdOut', 'stdErr'
    :param command: The command to execute as list of strings.
    :param shell: Execute command as string
    :param work_dir: The working directory for the executed command
    :return: An ExecutionResult
    """
    try:
        sp = _exec(command, shell, work_dir)
    except FileNotFoundError as e:
        return ExecutionResult([], _split_lines(str(e)), 1)

    std_out, std_err = sp.communicate()
    return_code = sp.returncode

    return ExecutionResult(_split_lines(std_out), _split_lines(std_err), return_code)


class ConnectorManager:
    CONNECTOR_CLASSES = {'File', 'Directory'}

    def __init__(self):
        self._input_runners = []
        self._output_runners = []

    def import_input_connectors(self, inputs):
        for input_key, input_value in inputs.items():
            if input_value['class'] in ConnectorManager.CONNECTOR_CLASSES:
                runner = create_input_connector_runner(input_key, input_value)
                self._input_runners.append(runner)

    def import_output_connectors(self, outputs, cli_outputs):
        """
        Creates ConnectorRunner for every key in outputs.
        :param outputs: The outputs to create runner for.
        :param cli_outputs: The output cli description.
        """
        for output_key, output_value in outputs.items():
            if output_value['class'] in ConnectorManager.CONNECTOR_CLASSES:
                cli_output_value = cli_outputs[output_key]
                runner = create_output_connector_runner(output_key, output_value, cli_output_value)
                self._output_runners.append(runner)

    def prepare_directories(self):
        """
        Tries to create directories needed to execute the connectors.
        :raise ConnectorError: If the needed directory could not be created, or if a received file does already exists
        """
        for runner in self._input_runners:
            runner.prepare_directory()

    def validate_connectors(self):
        """
        Validates connectors.
        """
        for runner in self._input_runners:
            runner.validate_receive()

        for runner in self._output_runners:
            runner.validate_send()

    def receive_connectors(self):
        """
        Executes receive_file, receive_dir or receive_mount for every input with connector.
        Schedules the mounting runners first for performance reasons.
        """
        not_mounting_runners = []
        # receive mounting input runners
        for runner in self._input_runners:
            if runner.is_mounting():
                runner.receive()
            else:
                not_mounting_runners.append(runner)

        # receive not mounting input runners
        for runner in not_mounting_runners:
            runner.receive()

    def send_connectors(self, working_dir):
        """
        Tries to executes send for all output connectors.
        If a send runner fails, will try to send the other runners and fails afterwards.
        :param working_dir: The working dir where command is executed
        :raise ConnectorError: If one ore more OutputRunners fail to send.
        """
        errors = []
        for runner in self._output_runners:
            try:
                runner.try_send(working_dir)
            except ConnectorError as e:
                errors.append(e)

        errors_len = len(errors)
        if errors_len == 1:
            raise errors[0]
        elif errors_len > 1:
            error_strings = [_format_exception(e) for e in errors]
            raise ConnectorError('{} output connectors failed:\n{}'.format(errors_len, '\n'.join(error_strings)))

    def umount_connectors(self):
        """
        Tries to execute umount for every connector.
        """
        for runner in self._input_runners:
            runner.try_umount()


def exception_format():
    exc_text = format_exc()
    return [_lstrip_quarter(l.replace('"', '').replace("'", '').rstrip()) for l in exc_text.split('\n') if l]


def _lstrip_quarter(s):
    len_s = len(s)
    s = s.lstrip()
    len_s_strip = len(s)
    quarter = (len_s - len_s_strip) // 4
    return ' ' * quarter + s


def _format_exception(exception):
    return '[{}]\n{}\n'.format(type(exception).__name__, str(exception))


def print_exception(exception):
    """
    Prints the exception message and the name of the exception class to stderr.

    :param exception: The exception to print
    """
    print(_format_exception(exception), file=sys.stderr)


def _split_lines(lines):
    return [l for l in lines.split(os.linesep) if l]


class ConnectorError(Exception):
    pass


class ExecutionError(Exception):
    pass


if __name__ == '__main__':
    main()
