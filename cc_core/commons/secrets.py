import jsonschema
from getpass import getpass
from copy import deepcopy

from cc_core.commons.files import wrapped_print
from cc_core.commons.schemas.red import secrets_schema, template_schema
from cc_core.commons.exceptions import RedValidationError, RedVariablesError


def secrets_validation(secrets_data):
    try:
        jsonschema.validate(secrets_data, secrets_schema)
    except Exception:
        raise RedValidationError('secrets file does not comply with jsonschema')


def _find_undeclared_recursively(data, undeclared_template_keys, access):
    if isinstance(data, dict):
        for key, val in data.items():
            if access and key.startswith('_'):
                try:
                    jsonschema.validate(val, template_schema)
                except Exception:
                    raise RedValidationError('protected key {} does not provide valid dictionary'.format(key))

                if 'value' not in val:
                    template = val['template']
                    undeclared_template_keys[template] = val['type']
            elif key == 'access':
                _find_undeclared_recursively(val, undeclared_template_keys, True)
            else:
                _find_undeclared_recursively(val, undeclared_template_keys, access)
    elif isinstance(data, list):
        for val in data:
            _find_undeclared_recursively(val, undeclared_template_keys, access)


def template_values(data, secrets_data, non_interactive=True):
    undeclared_template_keys = {}
    _find_undeclared_recursively(data, undeclared_template_keys, False)

    if not undeclared_template_keys:
        return None

    declared = {}
    undeclared = []

    secrets_data = secrets_data or {}

    for key in undeclared_template_keys:
        if key in secrets_data:
            declared[key] = secrets_data[key]
        else:
            undeclared.append(key)

    if undeclared:
        if non_interactive:
            raise RedVariablesError('RED_FILE contains undeclared template variables: {}'.format(undeclared))

        out = [
            'RED_FILE contains the following undeclared template variables:'
        ]
        out += undeclared
        out += [
            '',
            'Set variables interactively...',
            ''
        ]
        wrapped_print(out)

        for key in undeclared:
            val = getpass('{}: '.format(key))
            if undeclared_template_keys[key] == 'integer':
                try:
                    val = int(val)
                except Exception:
                    raise RedVariablesError('Provided value is not valid integer.')
            declared[key] = val

    return declared


def _fill_recursively(data, secrets_data, access, finalize):
    if isinstance(data, dict):
        result = {}
        for key, val in data.items():
            if access and key.startswith('_'):
                new_val = deepcopy(val)
                if 'value' not in val:
                    template = val['template']
                    new_val['value'] = secrets_data[template]

                if finalize:
                    new_key = key[1:]
                    result[new_key] = new_val['value']
                else:
                    result[key] = new_val
            elif key == 'access':
                result[key] = _fill_recursively(val, secrets_data, True, finalize)
            else:
                result[key] = _fill_recursively(val, secrets_data, access, finalize)

        return result
    elif isinstance(data, list):
        return [_fill_recursively(val, secrets_data, access, finalize) for val in data]
    return data


def fill_template(data, secrets_data, finalize=True):
    return _fill_recursively(data, secrets_data, False, finalize)
