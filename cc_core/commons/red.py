import jsonschema
from jsonschema.exceptions import ValidationError

from cc_core.commons.red_to_blue import InputType
from cc_core.commons.schemas.cwl import cwl_job_listing_schema
from cc_core.version import RED_VERSION
from cc_core.commons.schemas.red import red_schema
from cc_core.commons.exceptions import ArgumentError, RedValidationError
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

    _check_input_types(red_data)


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


def _check_input_type(input_key, input_value, cli_description_type):
    """
    Checks whether the type of the given input value matches the type of the given cli description.
    :param input_key: The corresponding input key
    :param input_value: The input value whose type to check
    :param cli_description_type: The cwl type description of the input key
    :raise RedSpecificationError: If actual input type does not match type of cli description
    """
    input_type = InputType.from_string(cli_description_type)

    if input_type.is_array():
        if not isinstance(input_value, list):
            raise RedSpecificationError('Value of input key "{}" is declared as array, but not given as such.'
                                        .format(input_key))

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

            raise RedSpecificationError('Value of input key "{}" should have type "{}", but found {}.'.format(
                    input_key, input_type.input_category.name, short_repr
            ))

        if not input_type.is_primitive():
            cli_type = input_type.input_category.name
            value_type = sub_input_value.get('class')
            if cli_type != value_type:
                raise RedSpecificationError('Input key "{}" is declared as "{}" but given as "{}"'.format(
                    input_key, cli_type, value_type
                ))


def _check_input_types(red_data):
    """
    Checks whether the types of the given input values match the types specified in the cli description.
    :param red_data: The red data to check
    :type red_data: dict
    :raise RedSpecificationError: If actual input type does not match type of cli description
    """

    input_cli_description = red_data['cli']['inputs']

    batches = red_data.get('batches')
    if batches:
        for batch in batches:
            for input_key, input_value in batch['inputs'].items():
                cli_description = input_cli_description[input_key]
                _check_input_type(input_key, input_value, cli_description['type'])
    else:
        for input_key, input_value in red_data['inputs'].items():
            cli_description = input_cli_description[input_key]
            _check_input_type(input_key, input_value, cli_description['type'])


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
