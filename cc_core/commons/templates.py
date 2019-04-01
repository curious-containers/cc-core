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


def complete_red_data(red_data, keyring_service, fail_if_interactive):
    """
    Replaces templates inside the given red data. Requests the missing keys of the red data from the keyring using the
    given keyring service.
    :param red_data: The red data to complete missing keys for
    :type red_data: dict[str, Any]
    :param keyring_service: The keyring service to use for requests
    :type keyring_service: str
    :param fail_if_interactive: Dont ask the user interactively for key values, but fail with an exception
    """
    missing_keys = set()
    _get_missing_keys(red_data, missing_keys)

    templates = _get_templates(missing_keys, keyring_service, fail_if_interactive)
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


def _get_templates(missing_keys, keyring_service, fail_if_interactive):
    """
    Returns a dictionary containing template keys and values.
    To fill in the missing values, first the keyring service is requested for each key,
    afterwards the user is asked interactively.
    :param missing_keys: A set of missing keys to query the keyring or ask the user
    :param keyring_service: The keyring service to query
    :param fail_if_interactive: Dont ask the user interactively for key values, but fail with an exception
    :return: A dictionary containing a mapping of template keys and values
    :rtype: dict
    """

    templates = {}

    first_interactive_key = True

    for missing_key in missing_keys:
        template_value = keyring.get_password(keyring_service, missing_key)
        if template_value is not None:
            templates[missing_key] = template_value
        else:
            if fail_if_interactive:
                raise TemplateError('Could not resolve template key "{}".'.format(missing_key))

            if first_interactive_key:
                print('Asking for template values:')
                first_interactive_key = False

            template_value = _ask_for_template_value(missing_key)
            templates[missing_key] = template_value

    return templates


def _ask_for_template_value(template_key):
    """
    Asks the user interactively for the given key
    :param template_key: The key to ask for
    :return: The users input
    """
    value = input('{}: '.format(template_key))
    return value


PRIVATE_KEYS = {'access', 'auth'}


def _get_missing_keys(data, missing_keys, key_string=None, missing_keys_allowed=False):
    """
    Iterates recursively over data values and appends template keys to the missing keys list.
    A template key is a string that starts with '{{' and ends with '}}'.

    :param data: The data to analyse.
    :param missing_keys: A set of missing keys to append missing keys to.
    :type missing_keys: set
    :param key_string: A string representing the keys above the current data element.
    :param missing_keys_allowed: A boolean that specifies whether missing keys are allowed.
    If a missing key is found but it is not allowed an exception is thrown.
    :raise TemplateError: If a missing key is found, but is not allowed.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            sub_key_string = _get_dict_sub_key_string(key, key_string)

            sub_missing_keys_allowed = missing_keys_allowed or (key in PRIVATE_KEYS)
            _get_missing_keys(value, missing_keys, sub_key_string, sub_missing_keys_allowed)
    elif isinstance(data, list):
        for index, sub_data in enumerate(data):
            sub_key_string = _get_list_sub_key_string(index, key_string)

            _get_missing_keys(sub_data, missing_keys, sub_key_string, missing_keys_allowed)
    elif isinstance(data, str):
        if missing_keys_allowed:
            new_missing_keys = _extract_missing_keys(data, key_string)
            if new_missing_keys:
                missing_keys.update(new_missing_keys)
        elif ('{' in data) or ('}' in data):
            raise TemplateError('Found invalid bracket in "{}" under "{}" in red data. Template keys are only '
                                'allowed as sub element of an auth or access key.'.format(data, key_string))


TEMPLATE_SEPARATOR_START = '{{'
TEMPLATE_SEPARATOR_END = '}}'


def _is_missing_key(s):
    """
    Returns True if s is a template string.
    :param s: The string to analyse
    :return: True, if s is a starts with TEMPLATE_SEPARATOR_START and ends with TEMPLATE_SEPARATOR_END
    """
    return s.startswith(TEMPLATE_SEPARATOR_START) and s.endswith(TEMPLATE_SEPARATOR_END)


def _extract_missing_keys(template_string, key_string):
    """
    Returns a set of missing keys, found inside s.
    :param template_string: The string to analyse
    :type template_string: str
    :param key_string: The keys of the given missing_key
    :return: If s is a missing key, the inner value of the given string, otherwise None
    :raise RedSpecificationError: If the missing key equals '{{}}'
    """
    try:
        parts = split_into_parts(template_string, TEMPLATE_SEPARATOR_START, TEMPLATE_SEPARATOR_END)
    except ParsingError as e:
        raise TemplateError('Could not parse template string "{}" in "{}". Do not use "{{" or "}}" in strings except '
                            'for template values. Failed with the following message:\n{}'
                            .format(template_string, key_string, str(e)))

    missing_keys = set()

    for part in parts:
        if _is_missing_key(part):
            template_key = part[2:-2]
            if ('{' in template_key) or ('}' in template_key):
                raise TemplateError('Could not parse template string "{}" in "{}". Too many brackets.'
                                    .format(template_string, key_string))
            if template_key == '':
                raise TemplateError('Could not parse template string "{}" in "{}". Template keys should not be empty.'
                                    .format(template_string, key_string))
            missing_keys.add(template_key)
        elif ('{' in part) or ('}' in part):
            raise TemplateError('Could not parse template string "{}" in "{}". Too many brackets.'
                                .format(template_string, key_string))

    return missing_keys


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
        if _is_missing_key(p):
            resolved = templates[p[2:-2]]
            result.append(resolved)
        else:
            result.append(p)

    return ''.join(result)
