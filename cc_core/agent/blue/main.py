import os
import sys
import subprocess
import json
import tempfile
import itertools

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

        if not outputs and 'outputs' in blue_data:
            del blue_data['outputs']

        if outputs and 'outputs' not in blue_data:
            raise AssertionError('-o/--outputs argument is set, \
            but no outputs section with RED connector settings is defined in REDFILE')

        # import, validate and execute connectors
        connector_manager.import_input_connectors(blue_data['inputs'])
        if outputs:
            connector_manager.import_output_connectors(blue_data['outputs'])

        connector_manager.prepare_directories()
        connector_manager.validate_connectors()
        connector_manager.mount_send_connectors()
        connector_manager.receive_connectors()

        # execute command
        command = blue_data['command']
        print('execute: "{}"'.format(command))

        # send files and directories
        connector_manager.send_connectors()

    except Exception as e:
        result['debugInfo'] = exception_format()
        result['state'] = 'failed'
        for i in result['debugInfo']:
            print(i)
        print_exception(e)
    finally:
        # umount directories
        connector_manager.umount_connectors()

    return result


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

    std_out = result['stdOut']
    if (result['returnCode'] == 0) and isinstance(std_out, list) and len(std_out) == 1:
        return std_out[0]
    else:
        std_err = result['stdErr']
        if isinstance(std_err, list):
            std_err = '\n'.join(std_err)
        raise ConnectorError('Could not detect cli version for connector "{}". Failed with following message:\n{}'
                             .format(connector_command, std_err))


class ConnectorExecutor:
    """
    A ConnectorExecutor can be used to execute the different functions of a Connector.

    A ConnectorExecutor subclass is associated with a connector cli-version.
    Subclasses implement different cli-versions for connectors.

    A ConnectorExecutor instance is associated with a blue input, that uses a connector.
    For every blue input, that uses a connector a new ConnectorExecutor instance is created.
    """
    def __init__(self, input_key, connector_command, input_class, mount, access, path, listing=None):
        """
        Initiates a ConnectorExecutor.

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
         :return: Returns whether this executor is mounting or not.
        """
        return self._mount

    def execute_connector(self, top_level_argument, access=None, path=None, listing=None):
        access_file = None
        if access is not None:
            access_file = tempfile.NamedTemporaryFile('w')
            json.dump(access, access_file)
            access_file.flush()

        listing_file = None
        if listing is not None:
            listing_file = tempfile.NamedTemporaryFile('w')
            json.dump(listing, listing_file)
            listing_file.flush()

        command = [self._connector_command, top_level_argument]
        if access_file is not None:
            command.append('"{}"'.format(access_file.name))
        if path is not None:
            command.append('"{}"'.format(path))
        if listing_file is not None:
            command.append('--listing="{}"'.format(listing_file.name))

        # TODO: execute
        print('For input key: "{}"'.format(self._input_key))
        print('command: {}'.format(' '.join(command)))
        if access_file is not None:
            print('content of {}:\n{}\n'.format(access_file.name, access))

        if access_file is not None:
            access_file.close()
        if listing_file is not None:
            listing_file.close()

    def prepare_directory(self):
        """
        In case of input_class == 'Directory' creates path.
        In case of input_class == 'File' creates os.path.dirname(path).
        :raise ConnectorError: If the directory could not be created or if the path already exist.
        """
        if os.path.exists(self._path):
            raise ConnectorError('Failed to prepare directory for key "{}". Path "{}" already exists.'
                                 .format(self._input_key, self._path))

        path_to_create = self._path if self._input_class == 'Directory' else os.path.dirname(self._path)

        try:
            if self._input_class == 'Directory':
                os.makedirs(self._path)
            elif self._input_class == 'File':
                os.makedirs(os.path.dirname(self._path), exist_ok=True)
        except PermissionError as e:
            raise ConnectorError('Could not prepare directory for input key "{}" with path "{}".'
                                 'Permission denied:\n{}'.format(self._input_key, path_to_create, str(e)))

    def validate_receive(self):
        """
        Executes receive_file_validate or receive_dir_validate depending on input_class
        """
        if self._input_class == 'Directory':
            if self._mount:
                self.receive_mount_validate()
            else:
                self.receive_dir_validate()
        elif self._input_class == 'File':
            self.receive_file_validate()

    def validate_send(self):
        """
        Executes send_file_validate, send_dir_validate or send_mount_validate depending on input_class and mount
        """
        if self._input_class == 'Directory':
            if self._mount:
                self.send_mount_validate()
            else:
                self.send_dir_validate()
        elif self._input_class == 'File':
            self.send_file_validate()

    def receive(self):
        """
        Executes receive_file, receive_directory or receive_mount depending on input_class and mount
        """
        if self._input_class == 'Directory':
            if self._mount:
                self.receive_mount()
                self._has_mounted = True
            else:
                self.receive_dir()
        elif self._input_class == 'File':
            self.receive_file()

    def try_send_mount(self):
        """
        Executes send_mount if input_class is 'Directory' and mount is True
        """
        if self._mount and self._input_class == 'Directory':
            self.send_mount()
            self._has_mounted = True

    def try_send(self):
        """
        Executes send_file or send_dir depending on input_class.
        Does nothing, if the associated connector is mounting.
        """
        if not self._mount:
            if self._input_class == 'File':
                self.send_file()
            elif self._input_class == 'Directory':
                self.send_dir()

    def try_umount(self):
        """
        Executes umount, if connector is mounting and has mounted, otherwise does nothing.
        """
        if self._mount and self._has_mounted:
            self.umount()

    def receive_file(self):
        raise NotImplementedError()

    def receive_file_validate(self):
        raise NotImplementedError()

    def send_file(self):
        raise NotImplementedError()

    def send_file_validate(self):
        raise NotImplementedError()

    def receive_dir(self):
        raise NotImplementedError()

    def receive_dir_validate(self):
        raise NotImplementedError()

    def send_dir(self):
        raise NotImplementedError()

    def send_dir_validate(self):
        raise NotImplementedError()

    def receive_mount(self):
        raise NotImplementedError()

    def receive_mount_validate(self):
        raise NotImplementedError()

    def send_mount(self):
        raise NotImplementedError()

    def send_mount_validate(self):
        raise NotImplementedError()

    def umount(self):
        raise NotImplementedError()


class ConnectorExecutor01(ConnectorExecutor):
    """
    This ConnectorExecutor implements the connector cli-version 0.1
    """
    def receive_file(self):
        self.execute_connector('receive-file', access=self._access, path=self._path)

    def receive_file_validate(self):
        self.execute_connector('receive-file-validate', access=self._access)

    def send_file(self):
        self.execute_connector('send-file', access=self._access, path=self._path)

    def send_file_validate(self):
        self.execute_connector('send-file-validate', access=self._access)

    def receive_dir(self):
        self.execute_connector('receive-dir', access=self._access, path=self._path, listing=self._listing)

    def receive_dir_validate(self):
        self.execute_connector('receive-dir-validate', access=self._access, listing=self._listing)

    def send_dir(self):
        self.execute_connector('send-dir', access=self._access, path=self._path, listing=self._listing)

    def send_dir_validate(self):
        self.execute_connector('send-dir-validate', access=self._access, listing=self._listing)

    def receive_mount(self):
        self.execute_connector('receive-mount', access=self._access, path=self._path)

    def receive_mount_validate(self):
        self.execute_connector('receive-mount-validate', access=self._access)

    def send_mount(self):
        self.execute_connector('send-mount', access=self._access, path=self._path)

    def send_mount_validate(self):
        self.execute_connector('send-mount-validate', access=self._access)

    def umount(self):
        self.execute_connector('umount', path=self._path)


CONNECTOR_CLI_VERSION_EXECUTOR_MAPPING = {
    '0.1': ConnectorExecutor01,
}


def create_input_connector_executor(input_key, input_value):
    """
    Creates a proper ConnectorExecutor instance for the given connector command.

    :param input_key: The input key of the executor
    :param input_value: The input to create an executor for
    :return: A ConnectorExecutor
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

    connector_executor_class = CONNECTOR_CLI_VERSION_EXECUTOR_MAPPING.get(cli_version)
    if connector_executor_class is None:
        raise Exception('This agent does not support connector cli-version "{}", but needed by connector "{}"'
                        .format(cli_version, connector_command))

    connector_executor = connector_executor_class(input_key,
                                                  connector_command,
                                                  input_class,
                                                  mount,
                                                  access,
                                                  path,
                                                  listing)

    return connector_executor


def execute(command):
    """
    Executes a given commandline command and returns a dictionary with keys: 'returnCode', 'stdOut', 'stdErr'
    :param command: The command to execute as list of strings.
    """
    try:
        sp = subprocess.Popen(command,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              universal_newlines=True,
                              encoding='utf-8')
    except TypeError:
        sp = subprocess.Popen(command,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              universal_newlines=True)

    std_out, std_err = sp.communicate()
    return_code = sp.returncode

    return {
        'stdOut': [l for l in std_out.split(os.linesep) if l],
        'stdErr': [l for l in std_err.split(os.linesep) if l],
        'returnCode': return_code,
    }


class ConnectorManager:
    CONNECTOR_CLASSES = {'File', 'Directory'}

    def __init__(self):
        self._input_executors = []
        self._output_executors = []

    def import_input_connectors(self, inputs):
        for input_key, input_value in inputs.items():
            if input_value['class'] in ConnectorManager.CONNECTOR_CLASSES:
                executor = create_input_connector_executor(input_key, input_value)
                self._input_executors.append(executor)

    def import_output_connectors(self, outputs):
        for input_key, input_value in outputs.items():
            if input_value['class'] in ConnectorManager.CONNECTOR_CLASSES:
                executor = create_input_connector_executor(input_key, input_value)
                self._input_executors.append(executor)

    def prepare_directories(self):
        """
        Tries to create directories needed to execute the connectors.
        :raise ConnectorError: If the needed directory could not be created, or if a received file does already exists
        """
        for executor in itertools.chain(self._input_executors, self._output_executors):
            executor.prepare_directory()

    def validate_connectors(self):
        """
        Validates connectors.
        """
        for executor in self._input_executors:
            executor.validate_receive()

        for executor in self._output_executors:
            executor.validate_send()

    def receive_connectors(self):
        """
        Executes receive_file, receive_dir or receive_mount for every input with connector.
        Schedules the mounting executors first for performance reasons.
        """
        not_mounting_executors = []
        # receive mounting input executors
        for executor in self._input_executors:
            if executor.is_mounting():
                executor.receive()
            else:
                not_mounting_executors.append(executor)

        # receive not mounting input executors
        for executor in not_mounting_executors:
            executor.receive()

    def mount_send_connectors(self):
        """
        Mounts every output executor that is mounting
        """
        for executor in self._output_executors:
            executor.try_send_mount()

    def send_connectors(self):
        """
        Tries to executes send for all output connectors
        """
        for executor in self._output_executors:
            executor.try_send()

    def umount_connectors(self):
        """
        Tries to execute umount for every connector.
        """
        for executor in itertools.chain(self._input_executors, self._output_executors):
            executor.try_umount()


def exception_format():
    exc_text = format_exc()
    return [_lstrip_quarter(l.replace('"', '').replace("'", '').rstrip()) for l in exc_text.split('\n') if l]


def _lstrip_quarter(s):
    len_s = len(s)
    s = s.lstrip()
    len_s_strip = len(s)
    quarter = (len_s - len_s_strip) // 4
    return ' ' * quarter + s


def print_exception(exception):
    """
    Prints the exception message and the name of the exception class to stderr.

    :param exception: The exception to print
    """
    print('[{}]\n{}\n'.format(type(exception).__name__, str(exception)), file=sys.stderr)


class ConnectorError(Exception):
    pass


if __name__ == '__main__':
    main()
