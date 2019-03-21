from enum import Enum
from typing import List, Any, Union

import os.path

import uuid
from pprint import pprint


def convert_red_to_blue(red_data):
    """
    Converts the given red data into blue data.
    The red data should not contain unresolved input references.
    :param red_data: The red data to convert
    :return: A dictionary containing the blue data
    """
    batches = extract_batches(red_data)
    complete_inputs(batches)
    print('completed inputs:')
    pprint(batches)
    return {}


class CliArgument:
    class CliArgumentType(Enum):
        Positional = 0
        Named = 1

    def __init__(self, input_key, argument_type, input_type):
        """
        Creates a new CliArgument.
        :param input_key: The input key of the cli argument
        :param argument_type: The type of the cli argument (Positional, Named)
        :param input_type: The type of the input key
        """
        self._input_key = input_key
        self._argument_type = argument_type
        self._input_type = input_type


def generate_command(cli_description, batch):
    """
    Creates a command from the cli description and a given batch.
    :param cli_description: The cli description of the executed command
    :param batch: The batch to execute
    :return: A list of string representing the created command
    """
    command = produce_base_command(cli_description.get('baseCommand'))

    arguments = get_arguments(cli_description['inputs'])


def get_arguments(cli_inputs):
    """
    Returns a list of arguments
    :param cli_inputs:
    :return:
    """
    raise NotImplementedError()


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



def complete_inputs(batches):
    """
    Completes the input attributes of the input files, by adding the attributes:
    path, basename, dirname, nameroot, nameext
    :param batches: list of batches
    """
    for batch in batches:
        for input_key, input_value in batch['inputs'].items():
            if input_value['class'] == 'File':
                complete_file_input_values(input_key, input_value)
            elif input_value['class'] == 'Directory':
                complete_directory_input_values(input_key, input_value)


def default_inputs_dirname():
    """
    Returns the default dirname for an input file.
    :return: The default dirname for an input file.
    """
    return os.path.join('/tmp', 'red', 'inputs', str(uuid.uuid4()))


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
                 'outputs': red_data['outputs']}
        return [batch]
