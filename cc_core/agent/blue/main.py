import os
import sys
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
    result = {
        'command': None,
        'inputFiles': None,
        'process': None,
        'outputFiles': None,
        'debugInfo': None,
        'state': 'succeeded'
    }

    try:
        with open(blue_file, 'r') as f:
            blue_data = json.load(f)

        if not outputs and 'outputs' in blue_data:
            del blue_data['outputs']

        if outputs and 'outputs' not in blue_data:
            raise AssertionError('-o/--outputs argument is set, \
            but no outputs section with RED connector settings is defined in REDFILE')

        connector_manager = ConnectorManager()
        connector_manager.import_input_executors(blue_data['inputs'])

        if outputs:
            connector_manager.import_output_executors(blue_data['outputs'])

        connector_manager.validate_connectors()

        print('num input executors: {}'.format(len(connector_manager._input_executors)))
        print(blue_data)
    except Exception as e:
        result['debugInfo'] = exception_format()
        result['state'] = 'failed'
        for i in result['debugInfo']:
            print(i)
        print_exception(e)

    return result


def resolve_connector_cli_version(connector_command):
    """
    Returns the cli-version of the given connector.
    :param connector_command: The connector command to resolve the cli-version for.
    :return: The string of the given connector
    :raise Exception: If the cli-version could not be resolved.
    """
    result = execute([connector_command, 'cli-version'])

    if result['returnCode'] == 0:
        return result['stdOut'][0]
    else:
        raise Exception('Could not detect cli version for connector "{}". Failed with following message:\n{}'
                        .format(connector_command, result['stdErr']))


class ConnectorExecutor:
    """
    A ConnectorExecutor can be used to execute the different functions of a Connector.

    A ConnectorExecutor subclass is associated with a connector cli-version.
    Subclasses implement different cli-versions for connectors.

    A ConnectorExecutor instance is associated with a blue input, that uses a connector.
    For every blue input, that uses a connector a new ConnectorExecutor instance is created.
    """
    def __init__(self, connector_command, input_class, mount, access, path, listing):
        self._connector_command = connector_command
        self._input_class = input_class
        self._mount = mount
        self._access = access
        self._path = path
        self._listing = listing

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
        print('command: {}'.format(' '.join(command)))
        if access_file is not None:
            print('content of {}:\n{}'.format(access_file.name, access))

        if access_file is not None:
            access_file.close()
        if listing_file is not None:
            listing_file.close()

    def validate_receive(self):
        """
        Executes receive_file_validate or receive_dir_validate depending on input_class
        """
        if self._input_class == 'Directory':
            self.receive_dir_validate()
        elif self._input_class == 'File':
            self.receive_file_validate()

    def validate_send(self):
        """
        Executes send_file_validate or send_dir_validate depending on input_class
        """
        if self._input_class == 'Directory':
            self.send_dir_validate()
        elif self._input_class == 'File':
            self.send_file_validate()

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
    This ConnectorExecutor implements the connector cli-version 0.1.
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


def create_connector_executor(input_value):
    """
    Creates a proper ConnectorExecutor instance for the given connector command.
    :param input_value: The input to create an executor for
    :return: A ConnectorExecutor
    """
    connector_command = input_value['connector']['command']
    cli_version = resolve_connector_cli_version(connector_command)
    input_class = input_value['class']
    mount = input_value.get('mount', False)
    access = input_value['connector']['access']
    path = input_value['path']
    listing = input_value.get('listing')

    connector_executor_class = CONNECTOR_CLI_VERSION_EXECUTOR_MAPPING.get(cli_version)
    if connector_executor_class is None:
        raise Exception('This agent does not support connector cli-version "{}", but needed by connector "{}"'
                        .format(cli_version, connector_command))

    connector_executor = connector_executor_class(connector_command, input_class, mount, access, path, listing)

    return connector_executor


def execute(command):
    """
    Executes a given command and returns a dictionary with keys: 'returnCode', 'stdOut', 'stdErr'
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
        self._input_executors = {}
        self._output_executors = {}

    @staticmethod
    def _import_executors_into(inputs, executors):
        """
        Adds proper executors into <executors> for every entry in inputs.
        :param inputs: The inputs to create executors for.
        :param executors: The dictionary where to put executors.
        """
        for input_key, input_value in inputs.items():
            if input_value['class'] in ConnectorManager.CONNECTOR_CLASSES:
                executor = create_connector_executor(input_value)
                executors[input_key] = executor

    def import_input_executors(self, inputs):
        ConnectorManager._import_executors_into(inputs, self._input_executors)

    def import_output_executors(self, outputs):
        ConnectorManager._import_executors_into(outputs, self._output_executors)

    def validate_connectors(self):
        """
        Validates connectors.
        """
        for key, executor in self._input_executors.items():
            executor.validate_receive()

        for key, executor in self._output_executors.items():
            executor.validate_send()


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
    print('[{}]\n{}'.format(type(exception).__name__, str(exception)), file=sys.stderr)


if __name__ == '__main__':
    main()
