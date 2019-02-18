import json
import os
import jsonschema
import tempfile
from jsonschema.exceptions import ValidationError

from cc_core.commons.files import make_file_read_only, for_each_file
from cc_core.commons.schemas.cwl import cwl_job_listing_schema
from cc_core.commons.shell import execute
from cc_core.version import RED_VERSION
from cc_core.commons.cwl import URL_SCHEME_IDENTIFIER
from cc_core.commons.schemas.red import red_schema
from cc_core.commons.exceptions import ConnectorError, AccessValidationError, AccessError, ArgumentError, \
    RedValidationError
from cc_core.commons.exceptions import RedSpecificationError

SEND_RECEIVE_SPEC_ARGS = ['access', 'internal']
SEND_RECEIVE_SPEC_KWARGS = []
SEND_RECEIVE_VALIDATE_SPEC_ARGS = ['access']
SEND_RECEIVE_VALIDATE_SPEC_KWARGS = []

SEND_RECEIVE_DIRECTORY_SPEC_ARGS = ['access', 'internal', 'listing']
SEND_RECEIVE_DIRECTORY_SPEC_KWARGS = []
SEND_RECEIVE_DIRECTORY_VALIDATE_SPEC_ARGS = ['access']
SEND_RECEIVE_DIRECTORY_VALIDATE_SPEC_KWARGS = []


class ConnectorManager:
    def __init__(self):
        self._successfully_received = []

    @staticmethod
    def _cdata(connector_data):
        return connector_data['command'], connector_data['access']

    @staticmethod
    def _execute_connector(connector_command, top_level_argument, *file_contents, listing=None):
        """
        Executes a connector by executing the given connector_command. The content of args will be the content of the
        files handed to the connector cli.

        :param connector_command: The connector command to execute.
        :param top_level_argument: The top level command line argument for the connector cli.
        (Like 'receive' or 'send_validate')
        :param file_contents: A dict of information handed over to the connector cli.
        :param listing: A listing to provide to the connector cli. Will be ignored if None.
        :return: A tuple containing the return code of the connector and the stderr of the command as str.
        """
        # create temp_files for every file_content
        temp_files = []
        for file_content in file_contents:
            if file_content is None:
                continue
            tmp_file = tempfile.NamedTemporaryFile('w')
            json.dump(file_content, tmp_file)
            tmp_file.flush()
            temp_files.append(tmp_file)

        tmp_listing_file = None
        if listing:
            tmp_listing_file = tempfile.NamedTemporaryFile('w')
            json.dump(listing, tmp_listing_file)
            tmp_listing_file.flush()

        command = [connector_command, top_level_argument]
        command.extend([t.name for t in temp_files])

        if tmp_listing_file:
            command.append('--listing {}'.format(tmp_listing_file.name))

        result = execute(' '.join(command))

        # close temp_files
        for temp_file in temp_files:
            temp_file.close()

        if tmp_listing_file:
            tmp_listing_file.close()

        return result['returnCode'], result['stdErr']

    def receive_validate(self, connector_data, input_key):
        connector_command, access = self._cdata(connector_data)

        return_code, std_err = ConnectorManager._execute_connector(connector_command, 'receive-validate', access)

        if return_code != 0:
            raise AccessValidationError('invalid access data for input file "{}". Failed with the following message:\n'
                                        '{}'.format(input_key, str(std_err)))

    def receive_directory_validate(self, connector_data, input_key):
        connector_command, access = self._cdata(connector_data)

        return_code, std_err = ConnectorManager._execute_connector(connector_command,
                                                                   'receive-directory-validate',
                                                                   access)

        if return_code != 0:
            raise AccessValidationError('invalid access data for input directory "{}". Failed with the following '
                                        'message:\n{}'.format(input_key, str(std_err)))

    def send_validate(self, connector_data, output_key):
        connector_command, access = self._cdata(connector_data)

        return_code, std_err = ConnectorManager._execute_connector(connector_command, 'send-validate', access)

        if return_code != 0:
            raise AccessValidationError('invalid access data for output file "{}". Failed with the following message:\n'
                                        '{}'.format(output_key, str(std_err)))

    def send_directory_validate(self, connector_data, output_key):
        connector_command, access = self._cdata(connector_data)

        return_code, std_err = ConnectorManager._execute_connector(connector_command, 'send-directory-validate', access)

        if return_code != 0:
            raise AccessValidationError('invalid access data for output directory "{}". Failed with the following '
                                        'message:\n{}'.format(output_key, str(std_err)))

    def receive(self, connector_data, input_key, internal):
        connector_command, access = self._cdata(connector_data)

        return_code, std_err = ConnectorManager._execute_connector(connector_command, 'receive', access, internal)

        if return_code != 0:
            raise AccessError('invalid access data for input file "{}". Failed with the following message:\n'
                              '{}'.format(input_key, str(std_err)))
        else:
            self._successfully_received.append(input_key)

        make_file_read_only(internal[URL_SCHEME_IDENTIFIER])

    @staticmethod
    def directory_listing_content_check(directory_path, listing):
        """
        Checks if a given listing is present under the given directory path.

        :param directory_path: The path to the base directory
        :param listing: The listing to check
        :return: None if no errors could be found, otherwise a string describing the error
        """
        if listing:
            for sub in listing:
                path = os.path.join(directory_path, sub['basename'])
                if sub['class'] == 'File':
                    if not os.path.isfile(path):
                        return 'listing contains "{}" but this file could not be found on disk.'.format(path)
                elif sub['class'] == 'Directory':
                    if not os.path.isdir(path):
                        return 'listing contains "{}" but this directory could not be found on disk'.format(path)
                    listing = sub.get('listing')
                    if listing:
                        return ConnectorManager.directory_listing_content_check(path, listing)
        return None

    def receive_directory(self, connector_data, input_key, internal, listing=None):
        connector_command, access = self._cdata(connector_data)

        return_code, std_err = ConnectorManager._execute_connector(connector_command, 'receive-directory', access,
                                                                   internal, listing=listing)

        if return_code != 0:
            raise AccessError('invalid access data for input directory "{}". Failed with the following '
                              'message:\n{}'.format(input_key, str(std_err)))
        else:
            self._successfully_received.append(input_key)

        directory_path = internal[URL_SCHEME_IDENTIFIER]

        error = ConnectorManager.directory_listing_content_check(directory_path, listing)
        if error:
            raise ConnectorError('The listing of input directory "{}" is not fulfilled:\n{}'.format(input_key, error))

        for_each_file(directory_path, make_file_read_only)

    def send(self, connector_data, output_key, internal):
        connector_command, access = self._cdata(connector_data)

        return_code, std_err = ConnectorManager._execute_connector(connector_command, 'send', access, internal)

        if return_code != 0:
            raise AccessValidationError('invalid access data for output file "{}". Failed with the following message:\n'
                                        '{}'.format(output_key, str(std_err)))

    def receive_cleanup(self, connector_data, input_key, internal):
        if input_key not in self._successfully_received:
            return

        connector_command, _ = self._cdata(connector_data)

        return_code, std_err = ConnectorManager._execute_connector(connector_command, 'receive-cleanup', internal)

        if return_code != 0:
            raise AccessError('cleanup for input file "{}" failed:\n'
                              '{}'.format(input_key, str(std_err)))

    def receive_directory_cleanup(self, connector_data, input_key, internal):
        if input_key not in self._successfully_received:
            return

        connector_command, _ = self._cdata(connector_data)

        return_code, std_err = ConnectorManager._execute_connector(connector_command,
                                                                   'receive-directory-cleanup',
                                                                   internal)

        if return_code != 0:
            raise AccessError('cleanup for input directory "{}" failed:\n'
                              '{}'.format(input_key, str(std_err)))


def _red_listing_validation(key, listing):
    """
    Raises an RedValidationError, if the given listing does not comply with cwl_job_listing_schema.
    If listing is None or an empty list, no exception is thrown.

    :param key: The input key to build an error message if needed.
    :param listing: The listing to validate
    :raise RedValidationError: If the given listing does not comply with cwl_job_listing_schema
    """

    if listing:
        try:
            jsonschema.validate(listing, cwl_job_listing_schema)
        except ValidationError as e:
            raise RedValidationError('REDFILE listing of input "{}" does not comply with jsonschema: {}'
                                     .format(key, e.context))


def red_get_mount_connectors_from_inputs(inputs):
    keys = []
    for input_key, arg in inputs.items():
        arg_items = []

        if isinstance(arg, dict):
            arg_items.append(arg)

        elif isinstance(arg, list):
            arg_items += [i for i in arg if isinstance(i, dict)]

        for i in arg_items:
            connector_data = i['connector']
            if connector_data.get('mount'):
                keys.append(input_key)

    return keys


def red_get_mount_connectors_from_outputs(outputs):
    keys = []
    for output_key, arg in outputs.items():
        if not isinstance(arg, dict):
            continue

        connector_data = arg['connector']
        if connector_data.get('mount'):
            keys.append(output_key)

    return keys


def red_get_mount_connectors(red_data, ignore_outputs):
    """
    Returns a list of mounting connectors

    :param red_data: The red data to be searched
    :param ignore_outputs: If outputs should be ignored
    :return: A list of connectors with active mount option.
    """

    keys = []

    batches = red_data.get('batches')
    inputs = red_data.get('inputs')
    if batches:
        for batch in batches:
            keys.extend(red_get_mount_connectors_from_inputs(batch['inputs']))
    elif inputs:
        keys.extend(red_get_mount_connectors_from_inputs(inputs))

    if not ignore_outputs:
        outputs = red_data.get('outputs')
        if batches:
            for batch in batches:
                batch_outputs = batch.get('outputs')
                if batch_outputs:
                    keys.extend(red_get_mount_connectors_from_outputs(batch_outputs))

        elif outputs:
            keys.extend(red_get_mount_connectors_from_outputs(outputs))

    return keys


def red_validation(red_data, ignore_outputs, container_requirement=False):
    try:
        jsonschema.validate(red_data, red_schema)
    except ValidationError as e:
        raise RedValidationError('REDFILE does not comply with jsonschema: {}'.format(e.context))

    if not red_data['redVersion'] == RED_VERSION:
        raise RedSpecificationError(
            'red version "{}" specified in REDFILE is not compatible with red version "{}" of cc-faice'.format(
                red_data['redVersion'], RED_VERSION
            )
        )

    if 'batches' in red_data:
        for batch in red_data['batches']:
            for key, val in batch['inputs'].items():
                if key not in red_data['cli']['inputs']:
                    raise RedSpecificationError('red inputs argument "{}" is not specified in cwl'.format(key))

                if isinstance(val, dict) and 'listing' in val:
                    _red_listing_validation(key, val['listing'])

            if not ignore_outputs and batch.get('outputs'):
                for key, val in batch['outputs'].items():
                    if key not in red_data['cli']['outputs']:
                        raise RedSpecificationError('red outputs argument "{}" is not specified in cwl'.format(key))
    else:
        for key, val in red_data['inputs'].items():
            if key not in red_data['cli']['inputs']:
                raise RedSpecificationError('red inputs argument "{}" is not specified in cwl'.format(key))

            if isinstance(val, dict) and 'listing' in val:
                _red_listing_validation(key, val['listing'])

        if not ignore_outputs and red_data.get('outputs'):
            for key, val in red_data['outputs'].items():
                if key not in red_data['cli']['outputs']:
                    raise RedSpecificationError('red outputs argument "{}" is not specified in cwl'.format(key))

    if container_requirement:
        if not red_data.get('container'):
            raise RedSpecificationError('container engine description is missing in REDFILE')


def convert_batch_experiment(red_data, batch):
    if 'batches' not in red_data:
        return red_data

    if batch is None:
        raise ArgumentError('batches are specified in REDFILE, but --batch argument is missing')

    try:
        batch_data = red_data['batches'][batch]
    except:
        raise ArgumentError('invalid batch index provided by --batch argument')

    result = {key: val for key, val in red_data.items() if not key == 'batches'}
    result['inputs'] = batch_data['inputs']

    if batch_data.get('outputs'):
        result['outputs'] = batch_data['outputs']

    return result


def import_and_validate_connectors(connector_manager, red_data, ignore_outputs):
    for input_key, arg in red_data['inputs'].items():
        arg_items = []

        if isinstance(arg, dict):
            arg_items.append(arg)

        elif isinstance(arg, list):
            arg_items += [i for i in arg if isinstance(i, dict)]

        for i in arg_items:
            connector_class = i['class']
            connector_data = i['connector']

            if connector_class == 'File':
                connector_manager.receive_validate(connector_data, input_key)
            elif connector_class == 'Directory':
                connector_manager.receive_directory_validate(connector_data, input_key)
            else:
                raise ConnectorError('Unsupported class for connector object: "{}"'.format(connector_class))

    if not ignore_outputs and red_data.get('outputs'):
        for output_key, arg in red_data['outputs'].items():
            if not isinstance(arg, dict):
                continue

            connector_data = arg['connector']
            connector_manager.send_validate(connector_data, output_key)


def inputs_to_job(red_data, tmp_dir):
    job = {}

    for key, arg in red_data['inputs'].items():
        val = arg
        if isinstance(arg, list):
            val = []
            for index, i in enumerate(arg):
                if isinstance(i, dict):
                    path = os.path.join(tmp_dir, '{}_{}'.format(key, index))
                    val.append({
                        'class': i['class'],
                        URL_SCHEME_IDENTIFIER: path
                    })
                else:
                    val.append(i)
        elif isinstance(arg, dict):
            path = os.path.join(tmp_dir, key)
            val = {
                'class': arg['class'],
                URL_SCHEME_IDENTIFIER: path
            }

        job[key] = val

    return job


def receive(connector_manager, red_data, tmp_dir):
    for key, arg in red_data['inputs'].items():
        val = arg

        if isinstance(arg, list):
            for index, i in enumerate(arg):
                if not isinstance(i, dict):
                    continue

                # connector_class should be one of 'File' or 'Directory'
                connector_class = i['class']
                input_key = '{}_{}'.format(key, index)
                path = os.path.join(tmp_dir, input_key)
                connector_data = i['connector']
                internal = {URL_SCHEME_IDENTIFIER: path}

                if connector_class == 'File':
                    connector_manager.receive(connector_data, input_key, internal)
                elif connector_class == 'Directory':
                    listing = i.get('listing')
                    connector_manager.receive_directory(connector_data, input_key, internal, listing)

        elif isinstance(arg, dict):
            # connector_class should be one of 'File' or 'Directory'
            connector_class = arg['class']
            input_key = key
            path = os.path.join(tmp_dir, input_key)
            connector_data = val['connector']
            internal = {URL_SCHEME_IDENTIFIER: path}

            if connector_class == 'File':
                connector_manager.receive(connector_data, input_key, internal)
            elif connector_class == 'Directory':
                listing = arg.get('listing')
                connector_manager.receive_directory(connector_data, input_key, internal, listing)


def cleanup(connector_manager, red_data, tmp_dir):
    """
    Invokes the cleanup functions for all inputs.
    """
    for key, arg in red_data['inputs'].items():
        val = arg

        if isinstance(arg, list):
            for index, i in enumerate(arg):
                if not isinstance(i, dict):
                    continue

                # connector_class should be one of 'File' or 'Directory'
                connector_class = i['class']
                input_key = '{}_{}'.format(key, index)
                path = os.path.join(tmp_dir, input_key)
                connector_data = i['connector']
                internal = {URL_SCHEME_IDENTIFIER: path}

                if connector_class == 'File':
                    connector_manager.receive_cleanup(connector_data, input_key, internal)
                elif connector_class == 'Directory':
                    connector_manager.receive_directory_cleanup(connector_data, input_key, internal)

        elif isinstance(arg, dict):
            # connector_class should be one of 'File' or 'Directory'
            connector_class = arg['class']
            input_key = key
            path = os.path.join(tmp_dir, input_key)
            connector_data = val['connector']
            internal = {URL_SCHEME_IDENTIFIER: path}

            if connector_class == 'File':
                connector_manager.receive_cleanup(connector_data, input_key, internal)
            elif connector_class == 'Directory':
                connector_manager.receive_directory_cleanup(connector_data, input_key, internal)

    try:
        os.rmdir(tmp_dir)
    except (OSError, FileNotFoundError):
        # Maybe, raise a warning here, because not all connectors have cleaned up their contents correctly.
        pass


def send(connector_manager, output_files, red_data, agency_data=None):
    for key, arg in red_data['outputs'].items():
        path = output_files[key][URL_SCHEME_IDENTIFIER]
        internal = {
            URL_SCHEME_IDENTIFIER: path,
            'agencyData': agency_data
        }
        connector_data = arg['connector']
        connector_manager.send(connector_data, key, internal)
