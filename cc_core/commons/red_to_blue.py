"""
This module defines functionality to transform red data into blue data:
- Define a command from a red file
  - Define the base command
  - Define the arguments for the command
- Complete input attributes
- Resolve input references
"""
from copy import deepcopy

from enum import Enum
from functools import total_ordering

import os.path

import uuid

from cc_core.commons.exceptions import JobSpecificationError, InvalidInputReference
from cc_core.commons.input_references import resolve_input_references

DEFAULT_WORKING_DIRECTORY = '/tmp/red/work/'


def convert_red_to_blue(red_data):
    """
    Converts the given red data into a list of blue data dictionary. The blue data is always given as list and each list
    entry represents one batch in the red data.
    :param red_data: The red data to convert
    :return: A list of blue data dictionaries
    """
    blue_batches = []

    batches = extract_batches(red_data)

    cli_description = red_data['cli']
    cli_inputs = cli_description['inputs']
    cli_outputs = cli_description.get('outputs')

    cli_arguments = get_cli_arguments(cli_inputs)
    base_command = produce_base_command(cli_description.get('baseCommand'))

    for batch in batches:
        batch_inputs = batch['inputs']
        complete_batch_inputs(batch_inputs)
        resolved_cli_outputs = complete_input_references_in_outputs(cli_outputs, batch_inputs)
        command = generate_command(base_command, cli_arguments, batch)
        blue_batch = create_blue_batch(command, batch, resolved_cli_outputs)
        blue_batches.append(blue_batch)

    return blue_batches


def create_blue_batch(command, batch, cli_outputs):
    """
    Defines a dictionary containing a blue batch
    :param command: The command of the blue data, given as list of strings
    :param batch: The Job data of the blue data
    :param cli_outputs: The outputs section of cli description
    :return: A dictionary containing the blue data
    """
    blue_data = {
        'command': command,
        'workDir': DEFAULT_WORKING_DIRECTORY,
        'cli': {
            'outputs': cli_outputs
        },
        **batch
    }

    return blue_data


class InputType:
    class InputCategory(Enum):
        File = 0
        Directory = 1
        String = 2
        Int = 3
        Long = 4
        Float = 5
        Double = 6
        Boolean = 7

    def __init__(self, input_category, is_array, is_optional):
        self.input_category = input_category
        self._is_array = is_array
        self._is_optional = is_optional

    @staticmethod
    def from_string(s):
        is_optional = s.endswith('?')
        if is_optional:
            s = s[:-1]

        is_array = s.endswith('[]')
        if is_array:
            s = s[:-2]

        input_category = None
        for ic in InputType.InputCategory:
            if s == ic.name:
                input_category = ic

        assert input_category is not None

        return InputType(input_category, is_array, is_optional)

    def to_string(self):
        return '{}{}{}'.format(self.input_category.name,
                               '[]' if self._is_array else '',
                               '?' if self._is_optional else '')

    def __repr__(self):
        return self.to_string()

    def __eq__(self, other):
        return (self.input_category == other.input_category) and\
               (self._is_array == other.is_array()) and\
               (self._is_optional == other.is_optional())

    def is_file(self):
        return self.input_category == InputType.InputCategory.File

    def is_directory(self):
        return self.input_category == InputType.InputCategory.Directory

    def is_array(self):
        return self._is_array

    def is_optional(self):
        return self._is_optional


def generate_command(base_command, cli_arguments, batch):
    """
    Creates a command from the cli description and a given batch.
    :param base_command: The base command to use
    :param cli_arguments: The arguments of the described tool
    :param batch: The batch to execute
    :return: A list of string representing the created command
    """
    command = base_command.copy()

    for cli_argument in cli_arguments:
        batch_value = batch['inputs'].get(cli_argument.input_key)
        execution_argument = create_execution_argument(cli_argument, batch_value)
        command.extend(execution_argument)

    return command


INPUT_CATEGORY_REPRESENTATION_MAPPER = {
    InputType.InputCategory.File: lambda batch_value: batch_value['path'],
    InputType.InputCategory.Directory: lambda batch_value: batch_value['path'],
    InputType.InputCategory.String: lambda batch_value: batch_value,
    InputType.InputCategory.Int: lambda batch_value: str(batch_value),
    InputType.InputCategory.Long: lambda batch_value: str(batch_value),
    InputType.InputCategory.Float: lambda batch_value: str(batch_value),
    InputType.InputCategory.Double: lambda batch_value: str(batch_value),
    InputType.InputCategory.Boolean: lambda batch_value: str(batch_value)
}


def create_execution_argument(cli_argument, batch_value):
    """
    Creates a list of strings representing an execution argument. Like ['--outdir=', '/path/to/file']
    :param cli_argument: The cli argument
    :param batch_value: The batch value corresponding to the cli argument. Can be None
    :return: A list of strings, that can be used to extend the command. Returns an empty list if (cli_argument is
    optional and batch_value is None) or (cli argument is array and len(batch_value) is 0)
    :raise JobSpecificationError: If cli argument is mandatory, but batch value is None
    If Cli Description defines an array, but job does not define a list
    """
    # handle optional arguments
    if batch_value is None:
        if cli_argument.is_optional():
            return []
        else:
            raise JobSpecificationError('required argument "{}" is missing'.format(cli_argument.input_key))

    # handle arrays (create argument list)
    argument_list = []
    if cli_argument.is_array():
        if not isinstance(batch_value, list):
            raise JobSpecificationError('For input key "{}":\nDescription defines an array, '
                                        'but job is not given as list'.format(cli_argument.input_key))

        for sub_batch_value in batch_value:
            r = INPUT_CATEGORY_REPRESENTATION_MAPPER[cli_argument.get_type_category()](sub_batch_value)
            argument_list.append(r)

        if not argument_list:
            return []
    else:
        argument_list.append(INPUT_CATEGORY_REPRESENTATION_MAPPER[cli_argument.get_type_category()](batch_value))

    # join argument list
    if cli_argument.item_separator:
        argument_list = [cli_argument.item_separator.join(argument_list)]

    # add prefix
    if cli_argument.prefix:
        do_separate = cli_argument.separate
        # do not separate, if the cli argument is an array and the item separator is not given
        if cli_argument.is_array() and not cli_argument.item_separator:
            do_separate = False

        if do_separate:
            argument_list.insert(0, cli_argument.prefix)
        else:
            assert len(argument_list) == 1
            argument_list = ['{}{}'.format(cli_argument.prefix, argument_list[0])]

    return argument_list


@total_ordering
class CliArgumentPosition:
    class CliArgumentPositionType(Enum):
        Positional = 0
        Named = 1

    def __init__(self, argument_position_type, binding_position):
        """
        Creates a new CliArgumentPosition.
        :param argument_position_type: The position type of this argument position
        """
        self.argument_position_type = argument_position_type
        self.binding_position = binding_position

    @staticmethod
    def new_positional_argument(binding_position):
        """
        Creates a new positional argument position.
        :param binding_position: The input position of the argument
        :return: A new CliArgumentPosition with position_type Positional
        """
        return CliArgumentPosition(CliArgumentPosition.CliArgumentPositionType.Positional, binding_position)

    @staticmethod
    def new_named_argument():
        """
        Creates a new named argument position.
        :return: A new CliArgumentPosition with position_type Named.
        """
        return CliArgumentPosition(CliArgumentPosition.CliArgumentPositionType.Named, 0)

    def is_positional(self):
        return self.argument_position_type is CliArgumentPosition.CliArgumentPositionType.Positional

    def is_named(self):
        return self.argument_position_type is CliArgumentPosition.CliArgumentPositionType.Named

    def __eq__(self, other):
        return (self.argument_position_type is other.argument_position_type) \
               and (self.binding_position == other.binding_position)

    def __lt__(self, other):
        if self.argument_position_type is CliArgumentPosition.CliArgumentPositionType.Positional:
            if other.argument_position_type is CliArgumentPosition.CliArgumentPositionType.Positional:
                return self.binding_position < other.binding_position
            else:
                return True
        else:
            return False

    def __repr__(self):
        return 'CliArgumentPosition(argument_position_type={}, binding_position={})'\
               .format(self.argument_position_type, self.binding_position)


class CliArgument:
    def __init__(self, input_key, argument_position, input_type, prefix, separate, item_separator):
        """
        Creates a new CliArgument.
        :param input_key: The input key of the cli argument
        :param argument_position: The type of the cli argument (Positional, Named)
        :param input_type: The type of the input key
        :param prefix: The prefix to prepend to the value
        :param separate: Separate prefix and value
        :param item_separator: The string to join the elements of an array
        """
        self.input_key = input_key
        self.argument_position: CliArgumentPosition = argument_position
        self.input_type: InputType = input_type
        self.prefix = prefix
        self.separate = separate
        self.item_separator = item_separator

    def __repr__(self):
        return 'CliArgument(\n\t{}\n)'.format('\n\t'.join(['input_key={}'.format(self.input_key),
                                                           'argument_position={}'.format(self.argument_position),
                                                           'input_type={}'.format(self.input_type),
                                                           'prefix={}'.format(self.prefix),
                                                           'separate={}'.format(self.separate),
                                                           'item_separator={}'.format(self.item_separator)]))

    @staticmethod
    def new_positional_argument(input_key, input_type, input_binding_position, item_separator):
        return CliArgument(input_key=input_key,
                           argument_position=CliArgumentPosition.new_positional_argument(input_binding_position),
                           input_type=input_type,
                           prefix=None,
                           separate=False,
                           item_separator=item_separator)

    @staticmethod
    def new_named_argument(input_key, input_type, prefix, separate, item_separator):
        return CliArgument(input_key=input_key,
                           argument_position=CliArgumentPosition.new_named_argument(),
                           input_type=input_type,
                           prefix=prefix,
                           separate=separate,
                           item_separator=item_separator)

    def is_array(self):
        return self.input_type.is_array()

    def is_optional(self):
        return self.input_type.is_optional()

    def is_positional(self):
        return self.argument_position.is_positional()

    def is_named(self):
        return self.argument_position.is_named()

    def get_type_category(self):
        return self.input_type.input_category

    @staticmethod
    def from_cli_input_description(input_key, cli_input_description):
        """
        Creates a new CliArgument depending of the information given in the cli input description.
        inputBinding keys = 'prefix' 'separate' 'position' 'itemSeparator'
        :param input_key: The input key of the cli input description
        :param cli_input_description: red_data['cli']['inputs'][input_key]
        :return: A new CliArgument
        """
        input_binding = cli_input_description['inputBinding']
        input_binding_position = input_binding.get('position', 0)
        prefix = input_binding.get('prefix')
        separate = input_binding.get('separate', True)
        item_separator = input_binding.get('itemSeparator')

        input_type = InputType.from_string(cli_input_description['type'])

        if prefix:
            arg = CliArgument.new_named_argument(input_key, input_type, prefix, separate, item_separator)
        else:
            arg = CliArgument.new_positional_argument(input_key, input_type, input_binding_position, item_separator)
        return arg


def get_cli_arguments(cli_inputs):
    """
    Returns a sorted list of cli arguments.
    :param cli_inputs: The cli inputs description
    :return: A list of CliArguments
    """
    cli_arguments = []
    for input_key, cli_input_description in cli_inputs.items():
        cli_arguments.append(CliArgument.from_cli_input_description(input_key, cli_input_description))
    return sorted(cli_arguments, key=lambda cli_argument: cli_argument.argument_position)


def produce_base_command(cwl_base_command):
    """
    Returns a list of strings describing the base command
    :param cwl_base_command: The cwl base command as written in the red file.
    :return: A stripped list of strings representing the base command
    """
    if isinstance(cwl_base_command, list):
        base_command = [w.strip() for w in cwl_base_command]
    elif isinstance(cwl_base_command, str):
        base_command = [cwl_base_command.strip()]
    else:
        base_command = []

    return base_command


def complete_input_references_in_outputs(cli_outputs, inputs_to_reference):
    """
    Takes the cli outputs and inputs to reference and returns the cli outputs, but with resolved input references
    :param cli_outputs: The cli outputs to resolve input references for
    :param inputs_to_reference: The inputs to reference
    """
    resolved_outputs = deepcopy(cli_outputs)

    for output_key, output_value in resolved_outputs.items():
        output_binding = output_value['outputBinding']

        try:
            resolved_glob = resolve_input_references(output_binding['glob'], inputs_to_reference)
        except InvalidInputReference as e:
            raise InvalidInputReference('Invalid Input Reference for output key "{}":\n{}'.format(output_key, str(e)))

        output_binding['glob'] = resolved_glob

    return resolved_outputs


def complete_batch_inputs(batch_inputs):
    """
    Completes the input attributes of the input files/directories, by adding the attributes:
    path, basename, dirname, nameroot, nameext
    :param batch_inputs: a dictionary containing job input information
    """
    for input_key, batch_value in batch_inputs.items():
        input_type = InputType.from_string(batch_value['class'])

        # complete files
        if input_type.is_file():
            if input_type.is_array():
                for file_element in batch_value:
                    complete_file_input_values(input_key, file_element)
            else:
                complete_file_input_values(input_key, batch_value)

        # complete directories
        elif input_type.is_directory():
            if input_type.is_array():
                for directory_element in batch_value:
                    complete_directory_input_values(input_key, directory_element)
            else:
                complete_directory_input_values(input_key, batch_value)


def default_inputs_dirname():
    """
    Returns the default dirname for an input file.
    :return: The default dirname for an input file.
    """
    return os.path.join('/tmp/red/inputs', str(uuid.uuid4()))


def complete_file_input_values(input_key, input_value, ):
    """
    Completes the information inside a given file input value. Will alter the given input_value.
    Creates the following keys (if not already present): path, basename, dirname, nameroot, nameext
    :param input_key: An input key as string
    :param input_value: An input value with class 'File'
    """
    # define basename
    if 'basename' in input_value:
        basename = input_value['basename']
    else:
        basename = input_key
        input_value['basename'] = basename

    # define dirname
    if 'dirname' in input_value:
        dirname = input_value['dirname']
    else:
        dirname = default_inputs_dirname()
        input_value['dirname'] = dirname

    # define nameroot, nameext
    nameroot, nameext = os.path.splitext(basename)
    input_value['nameroot'] = nameroot
    input_value['nameext'] = nameext

    # define path
    input_value['path'] = os.path.join(dirname, basename)


def complete_directory_input_values(input_key, input_value):
    """
    Completes the information inside a given directory input value. Will alter the given input_value.
    Creates the following keys (if not already present): path, basename
    :param input_key: An input key as string
    :param input_value: An input value with class 'File'
    """
    # define basename
    if 'basename' in input_value:
        basename = input_value['basename']
    else:
        basename = input_key
        input_value['basename'] = basename

    # define path
    dirname = default_inputs_dirname()
    input_value['path'] = os.path.join(dirname, basename)


def extract_batches(red_data):
    """
    Extracts a list of batches from the given red data
    :param red_data: The red data to extract batches from
    :return: A list of Batches
    """

    # in case of batches given
    red_batches = red_data.get('batches')
    if red_batches:
        batches = []
        for batch in red_batches:
            batches.append(batch)

        return batches
    else:
        batch = {'inputs': red_data['inputs'],
                 'outputs': red_data.get('outputs')}
        return [batch]