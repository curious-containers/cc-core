import os
import inspect
import jsonschema
from jsonschema.exceptions import ValidationError

from cc_core.commons.schemas.cwl import cwl_job_listing_schema
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
SEND_RECEIVE_DIRECTORY_VALIDATE_SPEC_ARGS = ['access', 'listing']
SEND_RECEIVE_DIRECTORY_VALIDATE_SPEC_KWARGS = []


class ConnectorManager:
    def __init__(self):
        self._imported_connectors = {}

    @staticmethod
    def _key(py_module, py_class):
        return '{}.{}'.format(py_module, py_class)

    @staticmethod
    def _cdata(connector_data):
        return connector_data['pyModule'], connector_data['pyClass'], connector_data['access']

    def _check_func(self, connector_key, funcname, spec_args, spec_kwargs):
        connector = self._imported_connectors[connector_key]
        try:
            func = getattr(connector, funcname)
            assert callable(func)
            spec = inspect.getfullargspec(func)
            assert spec.args == spec_args
            assert spec.kwonlyargs == spec_kwargs
        except:
            raise ConnectorError(
                'imported connector "{}" does not support "{}" function'.format(connector_key, funcname)
            )

    def import_connector(self, connector_data):
        py_module, py_class, _ = self._cdata(connector_data)
        key = ConnectorManager._key(py_module, py_class)

        if key in self._imported_connectors:
            return

        try:
            mod = __import__(py_module, fromlist=[py_class])
            connector = getattr(mod, py_class)
            assert inspect.isclass(connector)
        except:
            raise ConnectorError('invalid connector "{}"'.format(key))

        self._imported_connectors[key] = connector

    def receive_validate(self, connector_data, input_key):
        py_module, py_class, access = self._cdata(connector_data)
        c_key = self._key(py_module, py_class)

        try:
            connector = self._imported_connectors[c_key]
        except:
            raise ConnectorError('connector "{}" has not been imported'.format(c_key))

        self._check_func(c_key, 'receive', SEND_RECEIVE_SPEC_ARGS, SEND_RECEIVE_SPEC_KWARGS)
        self._check_func(c_key, 'receive_validate', SEND_RECEIVE_VALIDATE_SPEC_ARGS, SEND_RECEIVE_VALIDATE_SPEC_KWARGS)

        try:
            connector.receive_validate(access)
        except:
            raise AccessValidationError('invalid access data for input file "{}"'.format(input_key))

    def receive_directory_validate(self, connector_data, input_key, listing):
        py_module, py_class, access = self._cdata(connector_data)
        c_key = self._key(py_module, py_class)

        try:
            connector = self._imported_connectors[c_key]
        except:
            raise ConnectorError('connector "{}" has not been imported'.format(c_key))

        self._check_func(c_key,
                         'receive_directory',
                         SEND_RECEIVE_DIRECTORY_SPEC_ARGS,
                         SEND_RECEIVE_DIRECTORY_SPEC_KWARGS)
        self._check_func(c_key,
                         'receive_directory_validate',
                         SEND_RECEIVE_DIRECTORY_VALIDATE_SPEC_ARGS,
                         SEND_RECEIVE_DIRECTORY_VALIDATE_SPEC_KWARGS)

        try:
            connector.receive_directory_validate(access, listing)
        except Exception as e:
            raise AccessValidationError('invalid access data for input file "{}":\n{}'.format(input_key, str(e)))

    def send_validate(self, connector_data, output_key):
        py_module, py_class, access = self._cdata(connector_data)
        c_key = ConnectorManager._key(py_module, py_class)

        try:
            connector = self._imported_connectors[c_key]
        except:
            raise ConnectorError('connector "{}" has not been imported'.format(c_key))

        self._check_func(c_key, 'send', SEND_RECEIVE_SPEC_ARGS, SEND_RECEIVE_SPEC_KWARGS)
        self._check_func(c_key, 'send_validate', SEND_RECEIVE_VALIDATE_SPEC_ARGS, SEND_RECEIVE_VALIDATE_SPEC_KWARGS)

        try:
            connector.send_validate(access)
        except:
            raise AccessValidationError('invalid access data for output file "{}"'.format(output_key))

    def send_directory_validate(self, connector_data, output_key):
        py_module, py_class, access = self._cdata(connector_data)
        c_key = ConnectorManager._key(py_module, py_class)

        try:
            connector = self._imported_connectors[c_key]
        except:
            raise ConnectorError('connector "{}" has not been imported'.format(c_key))

        self._check_func(c_key, 'send_directory', SEND_RECEIVE_SPEC_ARGS, SEND_RECEIVE_SPEC_KWARGS)
        self._check_func(c_key,
                         'send_directory_validate',
                         SEND_RECEIVE_VALIDATE_SPEC_ARGS,
                         SEND_RECEIVE_VALIDATE_SPEC_KWARGS)

        try:
            connector.send_directory_validate(access)
        except:
            raise AccessValidationError('invalid access data for output file "{}"'.format(output_key))

    def receive(self, connector_data, input_key, internal):
        py_module, py_class, access = self._cdata(connector_data)
        key = ConnectorManager._key(py_module, py_class)
        connector = self._imported_connectors[key]

        try:
            connector.receive(access, internal)
        except:
            raise AccessError('could not access input file "{}"'.format(input_key))

    def receive_directory(self, connector_data, input_key, internal, listing=None):
        py_module, py_class, access = self._cdata(connector_data)
        key = ConnectorManager._key(py_module, py_class)
        connector = self._imported_connectors[key]

        try:
            connector.receive_directory(access, internal, listing)
        except:
            raise AccessError('could not access input file "{}"'.format(input_key))

    def send(self, connector_data, output_key, internal):
        py_module, py_class, access = self._cdata(connector_data)
        key = ConnectorManager._key(py_module, py_class)
        connector = self._imported_connectors[key]

        try:
            connector.send(access, internal)
        except:
            raise AccessError('could not access output file "{}"'.format(output_key))


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
            raise RedValidationError('red file listing of input "{}" does not comply with jsonschema: {}'
                                     .format(key, e.context))


def red_validation(red_data, ignore_outputs, container_requirement=False):
    try:
        jsonschema.validate(red_data, red_schema)
    except ValidationError as e:
        raise RedValidationError('red file does not comply with jsonschema: {}'.format(e.context))

    if not red_data['redVersion'] == RED_VERSION:
        raise RedSpecificationError(
            'red version "{}" specified in RED_FILE is not compatible with red version "{}" of cc-faice'.format(
                red_data['redVersion'], RED_VERSION
            )
        )

    if 'batches' in red_data:
        for batch in red_data['batches']:
            for key, val in batch['inputs'].items():
                if key not in red_data['cli']['inputs']:
                    raise RedSpecificationError('red inputs argument "{}" is not specified in cwl'.format(key))

                _red_listing_validation(key, val.get('listing'))

            if not ignore_outputs and batch.get('outputs'):
                for key, val in batch['outputs'].items():
                    if key not in red_data['cli']['outputs']:
                        raise RedSpecificationError('red outputs argument "{}" is not specified in cwl'.format(key))
    else:
        for key, val in red_data['inputs'].items():
            if key not in red_data['cli']['inputs']:
                raise RedSpecificationError('red inputs argument "{}" is not specified in cwl'.format(key))

            _red_listing_validation(key, val.get('listing'))

        if not ignore_outputs and red_data.get('outputs'):
            for key, val in red_data['outputs'].items():
                if key not in red_data['cli']['outputs']:
                    raise RedSpecificationError('red outputs argument "{}" is not specified in cwl'.format(key))

    if container_requirement:
        if not red_data.get('container'):
            raise RedSpecificationError('container engine description is missing in red file')


def convert_batch_experiment(red_data, batch):
    if 'batches' not in red_data:
        return red_data

    if batch is None:
        raise ArgumentError('batches are specified in RED_FILE, but --batch argument is missing')

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
            connector_manager.import_connector(connector_data)

            if connector_class == 'File':
                connector_manager.receive_validate(connector_data, input_key)
            elif connector_class == 'Directory':
                connector_manager.receive_directory_validate(connector_data, input_key, listing=i.get('listing'))
            else:
                raise ConnectorError('Unsupported class for connector object: "{}"'.format(connector_class))

    if not ignore_outputs and red_data.get('outputs'):
        for output_key, arg in red_data['outputs'].items():
            if not isinstance(arg, dict):
                continue

            connector_data = arg['connector']
            connector_manager.import_connector(connector_data)
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
                        'class': 'File',
                        URL_SCHEME_IDENTIFIER: path
                    })
                else:
                    val.append(i)
        elif isinstance(arg, dict):
            path = os.path.join(tmp_dir, key)
            val = {
                'class': 'File',
                URL_SCHEME_IDENTIFIER: path
            }

        job[key] = val

    return job


def receive(connector_manager, red_data, tmp_dir):
    for key, arg in red_data['inputs'].items():
        val = arg

        # connector_class should be one of 'File' or 'Directory'
        connector_class = arg['class']

        if isinstance(arg, list):
            for index, i in enumerate(arg):
                if not isinstance(i, dict):
                    continue

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
            path = os.path.join(tmp_dir, key)
            connector_data = val['connector']
            internal = {URL_SCHEME_IDENTIFIER: path}

            if connector_class == 'File':
                connector_manager.receive(connector_data, key, internal)
            elif connector_class == 'Directory':
                listing = arg.get('listing')
                connector_manager.receive_directory(connector_data, key, internal, listing)


def send(connector_manager, output_files, red_data, agency_data=None):
    for key, arg in red_data['outputs'].items():
        path = output_files[key][URL_SCHEME_IDENTIFIER]
        internal = {
            URL_SCHEME_IDENTIFIER: path,
            'agencyData': agency_data
        }
        connector_data = arg['connector']
        connector_manager.send(connector_data, key, internal)
