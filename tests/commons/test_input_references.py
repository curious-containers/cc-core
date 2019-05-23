import pytest

from cc_core.commons.exceptions import InvalidInputReference
from cc_core.commons.input_references import resolve_input_references

INPUT_LIST_TO_REFERENCE = {
    'a_file': [
        {
            'basename': 'a_file',
            'class': 'File',
            'connector': {
                'access': {
                    'method': 'GET',
                    'url': 'https://raw.githubusercontent.com/curious-containers/vagrant-quickstart/master/in.txt'
                },
                'command': 'red-connector-http'
            },
            'dirname': '/tmp/red/inputs/146dbc18-940d-4384-aaa7-073eb4402b51',
            'nameext': '',
            'nameroot': 'a_file',
            'path': '/tmp/red/inputs/146dbc18-940d-4384-aaa7-073eb4402b51/a_file'
        }
    ]
}

INPUT_TO_REFERENCE = {
    'a_file': {
        'basename': 'a_file',
        'class': 'File',
        'connector': {
            'access': {
                'method': 'GET',
                'url': 'https://raw.githubusercontent.com/curious-containers/vagrant-quickstart/master/in.txt'
            },
            'command': 'red-connector-http'
        },
        'dirname': '/tmp/red/inputs/146dbc18-940d-4384-aaa7-073eb4402b51',
        'nameext': '',
        'nameroot': 'a_file',
        'path': '/tmp/red/inputs/146dbc18-940d-4384-aaa7-073eb4402b51/a_file'
    }
}


def test_bracket_double_quote():
    glob = 'PRE-$(inputs["a_file"]["basename"])-POST'
    result = resolve_input_references(glob, INPUT_TO_REFERENCE)

    assert result == 'PRE-a_file-POST'


def test_bracket_single_quote():
    glob = 'PRE-$(inputs[\'a_file\'][\'basename\'])-POST'
    result = resolve_input_references(glob, INPUT_TO_REFERENCE)

    assert result == 'PRE-a_file-POST'


def test_bracket_dots():
    glob = 'PRE-$(inputs.a_file.basename)-POST'
    result = resolve_input_references(glob, INPUT_TO_REFERENCE)

    assert result == 'PRE-a_file-POST'


def test_file_list():
    glob = 'PRE-$(inputs.a_file[0].basename)-POST'
    result = resolve_input_references(glob, INPUT_LIST_TO_REFERENCE)

    assert result == 'PRE-a_file-POST'


def test_could_not_resolve():
    glob = '$(inputs.a_file.invalid)'
    with pytest.raises(InvalidInputReference):
        _ = resolve_input_references(glob, INPUT_TO_REFERENCE)
