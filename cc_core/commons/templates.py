import sys

import jsonschema
import keyring

from getpass import getpass
from collections import OrderedDict

from cc_core.commons.files import wrapped_print
from cc_core.commons.parsing import split_into_parts
from cc_core.commons.schemas.red import fill_schema
from cc_core.commons.exceptions import RedValidationError, RedVariablesError, TemplateError, ParsingError


def fill_validation(fill_data):
    try:
        jsonschema.validate(fill_data, fill_schema)
    except Exception:
        raise RedValidationError('FILL_FILE does not comply with jsonschema')


def _find_undeclared_recursively(data, template_key_is_protected, protected_values, allowed_section):
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
                    template_key_is_protected[val[2:-2]] = True
                else:
                    protected_values.update([val])

            elif allowed_section and key == 'password':
                if not isinstance(val, str):
                    raise RedValidationError('dict key password is only valid for string value')

                if val.startswith('{{') and val.endswith('}}'):
                    if len(val) == 4:
                        raise RedValidationError('string template value inside double curly braces must not be empty')
                    template_key_is_protected[val[2:-2]] = True
                else:
                    protected_values.update([val])
            
            elif key in ['access', 'auth']:
                _find_undeclared_recursively(val, template_key_is_protected, protected_values, True)
            
            else:
                _find_undeclared_recursively(val, template_key_is_protected, protected_values, allowed_section)
            
    elif isinstance(data, list):
        for val in data:
            _find_undeclared_recursively(val, template_key_is_protected, protected_values, allowed_section)

    elif isinstance(data, str):
        if data.startswith('{{') and data.endswith('}}'):
            if len(data) == 4:
                raise RedValidationError('string template value inside double curly braces must not be empty')

            template_key = data[2:-2]
            if template_key not in template_key_is_protected:
                template_key_is_protected[template_key] = False


def inspect_templates_and_secrets(data, fill_data, non_interactive):
    template_key_is_protected = OrderedDict()
    protected_values = set()
    _find_undeclared_recursively(data, template_key_is_protected, protected_values, False)

    template_keys_and_values = {}
    undeclared_template_key_is_protected = {}

    fill_data = fill_data or {}

    for key, is_protected in template_key_is_protected.items():
        if key in fill_data:
            value = fill_data[key]
            template_keys_and_values[key] = value
            if is_protected:
                protected_values.update([value])
        else:
            undeclared_template_key_is_protected[key] = is_protected

    incomplete_variables_file = False

    if undeclared_template_key_is_protected:
        if non_interactive:
            raise RedVariablesError('RED_FILE contains undeclared template variables: {}'.format(
                list(undeclared_template_key_is_protected.keys())
            ))

        incomplete_variables_file = True

        out = [
            'RED_FILE contains the following undeclared template variables:'
        ]
        out += [
            '{} (protected)'.format(key) if is_protected else '{}'.format(key)
            for key, is_protected in undeclared_template_key_is_protected.items()
        ]
        out += [
            '',
            'Set variables interactively...',
            ''
        ]
        wrapped_print(out)

        for key, is_protected in undeclared_template_key_is_protected.items():
            if is_protected:
                value = getpass('{} (protected): '.format(key))
                template_keys_and_values[key] = value
                protected_values.update([value])
            else:
                value = input('{}: '.format(key))
                template_keys_and_values[key] = value

    return template_keys_and_values, protected_values, incomplete_variables_file


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


def complete_red_templates(red_data, keyring_service, fail_if_interactive):
    """
    Replaces templates inside the given red data. Requests the template keys of the red data from the keyring using the
    given keyring service.
    :param red_data: The red data to complete template keys for
    :type red_data: dict[str, Any]
    :param keyring_service: The keyring service to use for requests
    :type keyring_service: str
    :param fail_if_interactive: Dont ask the user interactively for key values, but fail with an exception
    """
    template_keys = set()
    _get_template_keys(red_data, template_keys)

    templates = _get_templates(template_keys, keyring_service, fail_if_interactive)
    _complete_templates(red_data, templates)


def _complete_templates(data, templates, key_string=None):
    """
    Fills the given templates into the given data.
    :param data: The data to complete
    :param templates: The templates to use
    :param key_string: A string representing the keys above the current data element.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            sub_key_string = _get_dict_sub_key_string(key, key_string)

            if isinstance(value, str):
                completed_template_string = _resolve_template_string(value, templates, sub_key_string)
                data[key] = completed_template_string
            else:
                _complete_templates(value, templates, sub_key_string)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            sub_key_string = _get_list_sub_key_string(index, key_string)

            if isinstance(value, str):
                completed_template_string = _resolve_template_string(value, templates, sub_key_string)
                data[index] = completed_template_string
            else:
                _complete_templates(value, templates, sub_key_string)


def _get_dict_sub_key_string(key, key_string):
    if key_string is None:
        sub_key_string = key
    else:
        sub_key_string = '{}.{}'.format(key_string, key)
    return sub_key_string


def _get_list_sub_key_string(index, key_string):
    if key_string is None:
        sub_key_string = '[{}]'.format(index)
    else:
        sub_key_string = '{}[{}]'.format(key_string, index)
    return sub_key_string


def _get_templates(template_keys, keyring_service, fail_if_interactive):
    """
    Returns a dictionary containing template keys and values.
    To fill in the template keys, first the keyring service is requested for each key,
    afterwards the user is asked interactively.
    :param template_keys: A set of template keys to query the keyring or ask the user
    :type template_keys: set[TemplateKey]
    :param keyring_service: The keyring service to query
    :param fail_if_interactive: Dont ask the user interactively for key values, but fail with an exception
    :return: A dictionary containing a mapping of template keys and values
    :rtype: dict
    :raise TemplateError: If not all TemplateKeys could be resolved and fail_if_interactive is set
    """

    templates = {}
    keys_that_could_not_be_fulfilled = []

    first_interactive_key = True

    for template_key in template_keys:
        # try keyring
        template_value = keyring.get_password(keyring_service, template_key.key)
        if template_value is not None:
            templates[template_key.key] = template_value
        else:  # ask user
            if fail_if_interactive:
                keys_that_could_not_be_fulfilled.append(template_key.key)
                continue

            if first_interactive_key:
                print('Asking for template values:')
                sys.stdout.flush()
                first_interactive_key = False

            template_value = _ask_for_template_value(template_key)
            templates[template_key.key] = template_value

    if keys_that_could_not_be_fulfilled:
        raise TemplateError('Could not resolve the following template keys: "{}".'
                            .format(keys_that_could_not_be_fulfilled))

    return templates


def _is_protected_key(key):
    """
    Returns whether the given key is a protected key. ('password' or starts with underscore).
    :param key: The key to check
    :return: True, if the given key is a protected key, otherwise False
    """
    return (key == 'password') or (key.startswith('_'))


def _ask_for_template_value(template_key):
    """
    Asks the user interactively for the given key
    :param template_key: The key to ask for
    :return: The users input
    """
    if template_key.protected:
        value = getpass('{} (protected): '.format(template_key.key))
    else:
        value = input('{}: '.format(template_key.key))
    return value


PRIVATE_KEYS = {'access', 'auth'}


def _get_template_keys(data, template_keys, key_string=None, template_keys_allowed=False, protected=False):
    """
    Iterates recursively over data values and appends template keys to the template keys list.
    A template key is a string that starts with '{{' and ends with '}}'.

    :param data: The data to analyse.
    :param template_keys: A set of template keys to append template keys to.
    :type template_keys: set
    :param key_string: A string representing the keys above the current data element.
    :param template_keys_allowed: A boolean that specifies whether template keys are allowed in the current dict
    position. If a template key is found but it is not allowed an exception is thrown.
    :param protected: Indicates that the sub keys should be treated as protected keys
    :raise TemplateError: If a template key is found, but is not allowed.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            sub_key_string = _get_dict_sub_key_string(key, key_string)

            sub_template_keys_allowed = template_keys_allowed or (key in PRIVATE_KEYS)
            sub_protected = protected or _is_protected_key(key)

            if sub_protected and not sub_template_keys_allowed:
                raise TemplateError('Found protected key "{}", but protected keys are only allowed under one of {}'
                                    .format(sub_key_string, str(PRIVATE_KEYS)))
            _get_template_keys(data=value,
                               template_keys=template_keys,
                               key_string=sub_key_string,
                               template_keys_allowed=sub_template_keys_allowed,
                               protected=sub_protected)
    elif isinstance(data, list):
        for index, sub_data in enumerate(data):
            sub_key_string = _get_list_sub_key_string(index, key_string)

            _get_template_keys(data=sub_data,
                               template_keys=template_keys,
                               key_string=sub_key_string,
                               template_keys_allowed=template_keys_allowed,
                               protected=protected)
    elif isinstance(data, str):
        if template_keys_allowed:
            new_template_keys = _extract_template_keys(data, key_string, protected)
            if new_template_keys:
                template_keys.update(new_template_keys)
        elif ('{' in data) or ('}' in data):
            raise TemplateError('Found invalid bracket in "{}" under "{}" in red data. Template keys are only '
                                'allowed as sub element of an auth or access key.'.format(data, key_string))


TEMPLATE_SEPARATOR_START = '{{'
TEMPLATE_SEPARATOR_END = '}}'


def _is_template_key(s):
    """
    Returns True if s is a template string.
    :param s: The string to analyse
    :return: True, if s is a starts with TEMPLATE_SEPARATOR_START and ends with TEMPLATE_SEPARATOR_END
    """
    return s.startswith(TEMPLATE_SEPARATOR_START) and s.endswith(TEMPLATE_SEPARATOR_END)


class TemplateKey:
    def __init__(self, key, protected):
        """
        Creates a new TemplateKey
        :param key: The key string of this TemplateKey
        :param protected: Indicates if this TemplateKey is protected or not
        """
        self.key = key
        self.protected = protected


def _extract_template_keys(template_string, key_string, protected):
    """
    Returns a set of template keys, found inside template_string.
    :param template_string: The string to analyse
    :type template_string: str
    :param key_string: The keys of the given template_string
    :param protected: Indicates whether the extracted keys are protected
    :return: A set of template keys found inside template_string
    :raise Parsing: If the template_string is malformed
    """
    try:
        parts = split_into_parts(template_string, TEMPLATE_SEPARATOR_START, TEMPLATE_SEPARATOR_END)
    except ParsingError as e:
        raise TemplateError('Could not parse template string "{}" in "{}". Do not use "{{" or "}}" in strings except '
                            'for template values. Failed with the following message:\n{}'
                            .format(template_string, key_string, str(e)))

    template_keys = set()

    for part in parts:
        if _is_template_key(part):
            template_key_string = part[2:-2]
            if ('{' in template_key_string) or ('}' in template_key_string):
                raise TemplateError('Could not parse template string "{}" in "{}". Too many brackets.'
                                    .format(template_string, key_string))
            if template_key_string == '':
                raise TemplateError('Could not parse template string "{}" in "{}". Template keys should not be empty.'
                                    .format(template_string, key_string))
            template_keys.add(TemplateKey(template_key_string, protected))
        elif ('{' in part) or ('}' in part):
            raise TemplateError('Could not parse template string "{}" in "{}". Too many brackets.'
                                .format(template_string, key_string))

    return template_keys


def _resolve_template_string(template_string, templates, key_string):
    """
    Replaces the template keys inside the given template string.
    :param template_string: The string in which templates are to be replaced.
    :param templates: The templates to use
    :param key_string: The key string describing where the template string is found in the red file.
    :return: The template string with template keys resolved
    """
    try:
        parts = split_into_parts(template_string, TEMPLATE_SEPARATOR_START, TEMPLATE_SEPARATOR_END)
    except ParsingError as e:
        raise TemplateError('Could not parse template "{}" in "{}". Failed with the following message:\n{}'
                            .format(template_string, key_string, str(e)))
    result = []
    for p in parts:
        if _is_template_key(p):
            resolved = templates[p[2:-2]]
            result.append(resolved)
        else:
            result.append(p)

    return ''.join(result)


def get_secret_values(red_data):
    """
    Returns a list of secret values found in the given red data.
    A secret value is a value found under a protected key
    :param red_data: A dictionary containing the red data
    :return: A list of secret values found in the given red data
    """
    secret_values = []
    _append_secret_values(red_data, secret_values)
    return secret_values


def _append_secret_values(data, secret_values, protected=False):
    """
    Appends secret values found in data to secret_values
    :param data: The data to search in for secret values
    :param secret_values: The list of secret values
    :param protected: Indicates if the given value is protected or not
    """
    if isinstance(data, dict):
        for key, value in data.items():
            sub_protected = protected or _is_protected_key(key)
            _append_secret_values(value, secret_values, sub_protected)
    elif isinstance(data, list):
        for value in data:
            _append_secret_values(value, secret_values, protected)
    else:
        if protected:
            secret_values.append(data)


def normalize_keys(data):
    """
    Removes starting underscores from the keys in data
    :param data: The data in which keys with underscores should be replaced without underscore
    """
    if isinstance(data, dict):
        keys = list(data.keys())
        for key in keys:
            value = data[key]
            if key.startswith('_'):
                normalized_key = key[1:]
                data[normalized_key] = value
                del data[key]
            normalize_keys(value)
    elif isinstance(data, list):
        for value in data:
            normalize_keys(value)
