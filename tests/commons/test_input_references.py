from cc_core.commons.input_references import resolve_input_references

INPUT_LIST_TO_REFERENCE = {
    'ifile': [
        {
            'basename': 'ifile',
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
            'nameroot': 'ifile',
            'path': '/tmp/red/inputs/146dbc18-940d-4384-aaa7-073eb4402b51/ifile'
        }
    ]
}

INPUT_TO_REFERENCE = {
    'ifile': {
        'basename': 'ifile',
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
        'nameroot': 'ifile',
        'path': '/tmp/red/inputs/146dbc18-940d-4384-aaa7-073eb4402b51/ifile'
    }
}


def test_bracket_double_quote():
    glob = 'PRE-$(inputs["ifile"]["basename"])-POST'
    result = resolve_input_references(glob, INPUT_TO_REFERENCE)

    assert result == 'PRE-ifile-POST'


def test_bracket_single_quote():
    glob = 'PRE-$(inputs[\'ifile\'][\'basename\'])-POST'
    result = resolve_input_references(glob, INPUT_TO_REFERENCE)

    assert result == 'PRE-ifile-POST'


def test_bracket_dots():
    glob = 'PRE-$(inputs.ifile.basename])-POST'
    result = resolve_input_references(glob, INPUT_TO_REFERENCE)
    assert False

    assert result == 'PRE-ifile-POST'


def test_file_list():
    glob = '$(inputs.ifile[0].basename)'
