import os

import jsonschema
from jsonschema.exceptions import ValidationError

from cc_core.commons.red_to_blue import InputType
from cc_core.commons.schemas.cwl import cwl_job_listing_schema
from cc_core.version import RED_VERSION
from cc_core.commons.schemas.red import red_schema
from cc_core.commons.exceptions import ArgumentError, RedValidationError, CWLSpecificationError
from cc_core.commons.exceptions import RedSpecificationError

SEND_RECEIVE_SPEC_ARGS = ['access', 'internal']
SEND_RECEIVE_SPEC_KWARGS = []
SEND_RECEIVE_VALIDATE_SPEC_ARGS = ['access']
SEND_RECEIVE_VALIDATE_SPEC_KWARGS = []

SEND_RECEIVE_DIRECTORY_SPEC_ARGS = ['access', 'internal', 'listing']
SEND_RECEIVE_DIRECTORY_SPEC_KWARGS = []
SEND_RECEIVE_DIRECTORY_VALIDATE_SPEC_ARGS = ['access']
SEND_RECEIVE_DIRECTORY_VALIDATE_SPEC_KWARGS = []


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
            where = '.'.join([str(s) for s in e.absolute_path]) if e.absolute_path else '/'
            raise RedValidationError(
                'REDFILE listing of input key "{}" does not comply with jsonschema:\n\tkey: {}\n\treason: {}'
                .format(key, where, e.message)
            )


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


def red_validation(red_data, ignore_outputs, container_requirement=False):
    check_keys_are_strings(red_data)

    try:
        jsonschema.validate(red_data, red_schema)
    except ValidationError as e:
        where = '/'.join([str(s) for s in e.absolute_path]) if e.absolute_path else '/'
        raise RedValidationError(
            'REDFILE does not comply with jsonschema:\n\tkey in red file: {}\n\treason: {}'.format(where, e.message)
        )

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

    _check_input_output_types(red_data)
    _check_output_glob(red_data)


def _check_output_glob(red_data):
    """
    Raises an CwlSpecificationError, if a glob is given as absolute path.
    :param red_data: The red data to analyse
    """
    cli_outputs = red_data['cli'].get('outputs')
    if cli_outputs:
        for output_key, output_value in cli_outputs.items():
            glob = output_value['outputBinding']['glob']
            if os.path.isabs(glob):
                raise CWLSpecificationError(
                    'Glob of output key "{}" starts with "/", which is illegal'.format(output_key)
                )


CWL_TYPE_TO_PYTHON_TYPE = {
    InputType.InputCategory.File: {dict},
    InputType.InputCategory.Directory: {dict},
    InputType.InputCategory.string: {str},
    InputType.InputCategory.int: {int},
    InputType.InputCategory.long: {int},
    InputType.InputCategory.float: {float, int},
    InputType.InputCategory.double: {float, int},
    InputType.InputCategory.boolean: {bool}
}


def _check_input_output_type(input_value, cli_description_type):
    """
    Checks whether the type of the given value matches the type of the given cli description.
    :param input_value: The input value whose type to check
    :param cli_description_type: The cwl type description of the input key
    :raise RedSpecificationError: If actual input type does not match type of cli description
    """
    input_type = InputType.from_string(cli_description_type)

    if input_type.is_array():
        if not isinstance(input_value, list):
            raise RedSpecificationError('cli is declared as array, but value is not given as such')

    else:
        input_value = [input_value]

    for sub_input_value in input_value:
        set_of_possible_value_types = CWL_TYPE_TO_PYTHON_TYPE[input_type.input_category]
        if type(sub_input_value) not in set_of_possible_value_types:
            if isinstance(sub_input_value, dict):
                short_repr = 'dictionary'
            elif isinstance(sub_input_value, list):
                short_repr = 'list'
            else:
                short_repr = 'value "{}" of type "{}"'.format(sub_input_value, type(sub_input_value).__name__)

            raise RedSpecificationError('Value should have type "{}", but found {}.'.format(
                    input_type.input_category.name, short_repr
            ))

        if not input_type.is_primitive():
            cli_type = input_type.input_category.name
            value_type = sub_input_value.get('class')
            if cli_type != value_type:
                raise RedSpecificationError('Is declared as "{}" but given as "{}"'.format(
                    cli_type, value_type
                ))


def _check_input_output_types(red_data):
    """
    Checks whether the types of the given red data match the types specified in the cli description.
    :param red_data: The red data to check
    :type red_data: dict
    :raise RedSpecificationError: If types in batch does not match type of cli description
    """

    input_cli_description = red_data['cli']['inputs']
    output_cli_description = red_data['cli'].get('outputs')

    batches = red_data.get('batches')

    # check inputs
    if batches:
        for batch_index, batch in enumerate(batches):
            for input_key, input_value in batch['inputs'].items():
                cli_description = input_cli_description[input_key]
                try:
                    _check_input_output_type(input_value, cli_description['type'])
                except RedSpecificationError as e:
                    raise RedSpecificationError(
                        'Type of input key "{}" in batch {} does not match given values:\n{}'
                        .format(input_key, batch_index, str(e))
                    )
    else:
        for input_key, input_value in red_data['inputs'].items():
            cli_description = input_cli_description[input_key]
            try:
                _check_input_output_type(input_value, cli_description['type'])
            except RedSpecificationError as e:
                raise RedSpecificationError(
                    'Type of input key "{}" does not match given values:\n{}'.format(input_key, str(e))
                )

    if batches:
        for batch_index, batch in enumerate(batches):
            outputs = batch.get('outputs')
            if outputs:
                for output_key, output_value in outputs.items():
                    cli_description = output_cli_description[output_key]
                    try:
                        _check_input_output_type(output_value, cli_description['type'])
                    except Exception as e:
                        raise RedSpecificationError(
                            'Type of output key "{}" in batch {} does not match given values:\n{}'
                            .format(output_key, batch_index, str(e))
                        )
    else:
        for output_key, output_value in red_data['outputs'].items():
            cli_description = output_cli_description[output_key]
            try:
                _check_input_output_type(output_value, cli_description['type'])
            except Exception as e:
                raise RedSpecificationError(
                    'Type of output key "{}" does not match given values:\n{}'.format(output_key, str(e))
                )


def _check_key_is_string(key, path):
    """
    Raises an RedSpecificationError, if the given key is not of type string.
    :param key: The key to check the type
    :param path: The path to this key
    :raise RedSpecificationError: If the given key has a type different from str
    """
    if not isinstance(key, str):
        if path:
            where = 'under "{}" '.format('.'.join(path))
        else:
            where = ''
        raise RedSpecificationError(
            'The key "{}" ({}) in REDFILE {}is not of type string'.format(key, type(key).__name__, where)
        )


def check_keys_are_strings(data, path=None):
    """
    Raises an RedSpecificationError, if a key is not of type string
    :param data: The data to check
    :param path: The path of keys as list of strings leading to data
    :raise RedSpecificationError: If a key is found, that has a type different from str
    """
    if path is None:
        path = []

    if isinstance(data, dict):
        for key, value in data.items():
            _check_key_is_string(key, path)
            check_keys_are_strings(value, path + [key])
    elif isinstance(data, list):
        for index, value in enumerate(data):
            check_keys_are_strings(value, path + [str(index)])


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
