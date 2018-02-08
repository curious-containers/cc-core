import os
import inspect
import jsonschema

from cc_core.version import RED_VERSION
from cc_core.commons.schemas.red import red_schema
from cc_core.commons.exceptions import ConnectorError, AccessValidationError, AccessError
from cc_core.commons.exceptions import RedSpecificationError

SEND_RECEIVE_SPEC_ARGS = ['access', 'internal']
SEND_RECEIVE_SPEC_KWARGS = []
SEND_RECEIVE_VALIDATE_SPEC_ARGS = ['access']
SEND_RECEIVE_VALIDATE_SPEC_KWARGS = []


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

    def receive(self, connector_data, input_key, internal):
        py_module, py_class, access = self._cdata(connector_data)
        key = ConnectorManager._key(py_module, py_class)
        connector = self._imported_connectors[key]

        try:
            connector.receive(access, internal)
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


def red_validation(red_data, ignore_outputs, container_requirement=False):
    try:
        jsonschema.validate(red_data, red_schema)
    except:
        raise RedSpecificationError('red file does not comply with jsonschema')

    if not red_data['redVersion'] == RED_VERSION:
        raise RedSpecificationError(
            'red version "{}" specified in RED_FILE is not compatible with red version "{}" of cc-faice'.format(
                red_data['redVersion'], RED_VERSION
            )
        )

    for key, val in red_data['inputs'].items():
        if key not in red_data['cli']['inputs']:
            raise RedSpecificationError('red inputs argument "{}" is not specified in cwl'.format(key))

    if not ignore_outputs and red_data.get('outputs'):
        for key, val in red_data['outputs'].items():
            if key not in red_data['cli']['outputs']:
                raise RedSpecificationError('red outputs argument "{}" is not specified in cwl'.format(key))

    if container_requirement:
        if not red_data.get('container'):
            raise RedSpecificationError('container engine description is missing in red file')


def import_and_validate_connectors(connector_manager, red_data, ignore_outputs):
    for input_key, val in red_data['inputs'].items():
        if not isinstance(val, dict):
            continue

        connector_data = val['connector']
        connector_manager.import_connector(connector_data)
        connector_manager.receive_validate(connector_data, input_key)

    if not ignore_outputs and red_data.get('outputs'):
        for output_key, val in red_data['outputs'].items():
            if not isinstance(val, dict):
                continue

            connector_data = val['connector']
            connector_manager.import_connector(connector_data)
            connector_manager.send_validate(connector_data, output_key)


def inputs_to_job(red_data, tmp_dir):
    job = {}

    for key, val in red_data['inputs'].items():
        if not isinstance(val, dict):
            job[key] = val
            continue

        path = os.path.join(tmp_dir, key)
        job[key] = {
            'class': 'File',
            'path': path
        }

    return job


def receive(connector_manager, red_data, tmp_dir):
    for input_key, val in red_data['inputs'].items():
        if not isinstance(val, dict):
            continue

        path = os.path.join(tmp_dir, input_key)
        connector_data = val['connector']
        internal = {'path': path}

        connector_manager.receive(connector_data, input_key, internal)


def send(connector_manager, output_files, red_data, agency_data=None):
    for output_key, val in red_data['outputs'].items():
        path = output_files[output_key]['path']
        internal = {
            'path': path,
            'agencyData': agency_data
        }
        connector_data = val['connector']
        connector_manager.send(connector_data, output_key, internal)
