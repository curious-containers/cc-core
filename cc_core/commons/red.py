import os
import inspect
import jsonschema

from cc_core.commons.schemas.cwl import cwl_schema
from cc_core.commons.schemas.red import red_inputs_schema, red_outputs_schema
from cc_core.commons.exceptions import ConnectorError, AccessValidationError, AccessError, CWLSpecificationError
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


def red_validation(cwl_data, inputs_data, outputs_data):
    try:
        jsonschema.validate(cwl_data, cwl_schema)
    except:
        raise CWLSpecificationError('cwl file does not comply with jsonschema')

    try:
        jsonschema.validate(inputs_data, red_inputs_schema)
    except:
        raise RedSpecificationError('red inputs file does not comply with jsonschema')

    if outputs_data:
        try:
            jsonschema.validate(outputs_data, red_outputs_schema)
        except:
            raise RedSpecificationError('red outputs file does not comply with jsonschema')

        for key, val in outputs_data.items():
            if key not in cwl_data['outputs']:
                raise RedSpecificationError('red outputs argument "{}" is not specified in cwl'.format(key))

    for key, val in inputs_data.items():
        if key not in cwl_data['inputs']:
            raise RedSpecificationError('red inputs argument "{}" is not specified in cwl'.format(key))


def import_and_validate_connectors(connector_manager, inputs_data, outputs_data):
    for input_key, val in inputs_data.items():
        if not isinstance(val, dict):
            continue

        connector_data = val['connector']
        connector_manager.import_connector(connector_data)
        connector_manager.receive_validate(connector_data, input_key)

    if outputs_data:
        for output_key, val in outputs_data.items():
            if not isinstance(val, dict):
                continue

            connector_data = val['connector']
            connector_manager.import_connector(connector_data)
            connector_manager.send_validate(connector_data, output_key)


def inputs_to_job(inputs_data, tmp_dir):
    job = {}

    for key, val in inputs_data.items():
        if not isinstance(val, dict):
            job[key] = val
            continue

        path = os.path.join(tmp_dir, key)
        job[key] = {
            'class': 'File',
            'path': path
        }

    return job


def receive(connector_manager, inputs_data, tmp_dir):
    for input_key, val in inputs_data.items():
        if not isinstance(val, dict):
            continue

        path = os.path.join(tmp_dir, input_key)
        connector_data = val['connector']
        internal = {'path': path}

        connector_manager.receive(connector_data, input_key, internal)


def send(connector_manager, output_files, outputs_data, agency_data=None):
    for output_key, val in outputs_data.items():
        path = output_files[output_key]['path']
        internal = {
            'path': path,
            'agencyData': agency_data
        }
        connector_data = val['connector']
        connector_manager.send(connector_data, output_key, internal)
