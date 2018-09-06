import jsonschema
from getpass import getpass
from collections import OrderedDict

from cc_core.commons.files import wrapped_print
from cc_core.commons.schemas.red import fill_schema
from cc_core.commons.exceptions import RedValidationError, RedVariablesError


def fill_validation(fill_data):
    try:
        jsonschema.validate(fill_data, fill_schema)
    except Exception:
        raise RedValidationError('FILL_FILE does not comply with jsonschema')


def _find_undeclared_recursively(data, template_key_is_secret, secret_values, allowed_section):
    if isinstance(data, dict):
        for key, val in data.items():
            if allowed_section and key.startswith('_'):
                if len(key) == 1:
                    raise RedValidationError('dict key _ is invalid')
                
                if key[1:] in data:
                    raise RedValidationError('key {} and key {} cannot be in one dict'.format(key, key[1:]))

                if not isinstance(val, str):
                    raise RedValidationError('protecting dict keys with _ is only valid for string values')

                if val.startswith('{{') and val.endswith('}}'):
                    if len(val) == 4:
                        raise RedValidationError('string template value inside double curly braces must not be empty')
                    template_key_is_secret[val[2:-2]] = True
                else:
                    secret_values.update([val])

            elif allowed_section and key == 'password':
                if not isinstance(val, str):
                    raise RedValidationError('dict key password is only valid for string value')

                if val.startswith('{{') and val.endswith('}}'):
                    if len(val) == 4:
                        raise RedValidationError('string template value inside double curly braces must not be empty')
                    template_key_is_secret[val[2:-2]] = True
                else:
                    secret_values.update([val])
            
            elif key in ['access', 'auth']:
                _find_undeclared_recursively(val, template_key_is_secret, secret_values, True)
            
            else:
                _find_undeclared_recursively(val, template_key_is_secret, secret_values, allowed_section)
            
    elif isinstance(data, list):
        for val in data:
            _find_undeclared_recursively(val, template_key_is_secret, secret_values, allowed_section)

    elif isinstance(data, str):
        if data.startswith('{{') and data.endswith('}}'):
            if len(data) == 4:
                raise RedValidationError('string template value inside double curly braces must not be empty')

            template_key_is_secret[data[2:-2]] = False


def inspect_templates_and_secrets(data, fill_data, non_interactive):
    template_key_is_secret = OrderedDict()
    secret_values = set()
    _find_undeclared_recursively(data, template_key_is_secret, secret_values, False)

    template_keys_and_values = {}
    undeclared_template_key_is_secret = {}

    fill_data = fill_data or {}

    for key, is_secret in template_key_is_secret.items():
        if key in fill_data:
            value = fill_data[key]
            template_keys_and_values[key] = value
            if is_secret:
                secret_values.update([value])
        else:
            undeclared_template_key_is_secret[key] = is_secret

    if undeclared_template_key_is_secret:
        if non_interactive:
            raise RedVariablesError('RED_FILE contains undeclared template variables: {}'.format(
                list(undeclared_template_key_is_secret.keys())
            ))

        out = [
            'RED_FILE contains the following undeclared template variables:'
        ]
        out += list(undeclared_template_key_is_secret.keys())
        out += [
            '',
            'Set variables interactively...',
            ''
        ]
        wrapped_print(out)

        for key, is_secret in undeclared_template_key_is_secret.items():
            if is_secret:
                value = getpass('{}: '.format(key))
                template_keys_and_values[key] = value
                secret_values.update([value])
            else:
                value = input('{}: '.format(key))
                template_keys_and_values[key] = value

    return template_keys_and_values, secret_values


def _fill_recursively(data, template_keys_and_values, allowed_section, remove_underscores):
    if isinstance(data, dict):
        result = {}
        for key, val in data.items():
            if allowed_section and remove_underscores and key.startswith('_'):
                result[key[1:]] = _fill_recursively(val, template_keys_and_values, allowed_section, remove_underscores)

            elif key in ['access', 'auth']:
                result[key] = _fill_recursively(val, template_keys_and_values, True, remove_underscores)
            
            else:
                result[key] = _fill_recursively(val, template_keys_and_values, allowed_section, remove_underscores)

        return result
    
    elif isinstance(data, list):
        return [_fill_recursively(val, template_keys_and_values, allowed_section, remove_underscores) for val in data]

    elif isinstance(data, str):
        if data.startswith('{{') and data.endswith('}}'):
            return template_keys_and_values[data[2:-2]]
    
    return data


def fill_template(data, template_keys_and_values, allowed_section, remove_underscores):
    return _fill_recursively(data, template_keys_and_values, allowed_section, remove_underscores)
