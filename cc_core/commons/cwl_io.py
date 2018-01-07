import os
import inspect
import tempfile
import jsonschema
from uuid import uuid4
from copy import deepcopy

from cc_core.commons.schemas.cwl import cwl_schema
from cc_core.commons.schemas.faice import inputs_schema, outputs_schema


class ConnectorManager:
    def __init__(self):
        self._imported_connectors = {}

    @staticmethod
    def _key(py_module, py_class):
        return '{}.{}'.format(py_module, py_class)

    def import_connector(self, py_module, py_class):
        key = ConnectorManager._key(py_module, py_class)

        if key in self._imported_connectors:
            return

        mod = __import__(py_module, fromlist=[py_class])
        connector = getattr(mod, py_class)

        assert inspect.isclass(connector)

        self._imported_connectors[key] = connector

    def receive_validate(self, py_module, py_class, access):
        key = ConnectorManager._key(py_module, py_class)
        connector = self._imported_connectors[key]

        connector.receive_validate(access)

    def send_validate(self, py_module, py_class, access):
        key = ConnectorManager._key(py_module, py_class)
        connector = self._imported_connectors[key]

        assert callable(connector.send)

        connector.send_validate(access)

    def receive(self, py_module, py_class, access, internal):
        key = ConnectorManager._key(py_module, py_class)
        connector = self._imported_connectors[key]

        assert callable(connector.receive)

        connector.receive(access, internal)

    def send(self, py_module, py_class, access, internal):
        key = ConnectorManager._key(py_module, py_class)
        connector = self._imported_connectors[key]

        connector.send(access, internal)


def cwl_io_validation(cwl_data, inputs_data, outputs_data):
    jsonschema.validate(cwl_data, cwl_schema)
    jsonschema.validate(inputs_data, inputs_schema)
    jsonschema.validate(outputs_data, outputs_schema)

    for key, val in outputs_data.items():
        assert key in cwl_data['outputs']

    for key, val in inputs_data.items():
        assert key in cwl_data['inputs']


def import_and_validate_connectors(connector_manager, inputs_data, outputs_data):
    for key, val in inputs_data.items():
        if not isinstance(val, dict):
            continue

        py_module = val['connector']['py_module']
        py_class = val['connector']['py_class']
        access = val['connector']['access']
        connector_manager.import_connector(py_module, py_class)
        connector_manager.send_validate(py_module, py_class, access)

    for key, val in outputs_data.items():
        if not isinstance(val, dict):
            continue

        py_module = val['connector']['py_module']
        py_class = val['connector']['py_class']
        access = val['connector']['access']
        connector_manager.import_connector(py_module, py_class)
        connector_manager.receive_validate(py_module, py_class, access)


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
    for key, val in inputs_data.items():
        if not isinstance(val, dict):
            continue

        path = os.path.join(tmp_dir, key)
        py_module = val['connector']['py_module']
        py_class = val['connector']['py_class']
        access = val['connector']['access']
        internal = {'path': path}

        connector_manager.receive(py_module, py_class, access, internal)


def send(connector_manager, output_files, outputs_data, ids=None):
    for key, val in outputs_data.items():
        path = output_files[key]['path']
        internal = {
            'path': path,
            'ids': ids
        }
        py_module = val['connector']['py_module']
        py_class = val['connector']['py_class']
        access = val['connector']['access']
        connector_manager.send(py_module, py_class, access, internal)
