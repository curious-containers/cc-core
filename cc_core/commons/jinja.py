import jsonschema
from getpass import getpass
from jinja2 import Template, Environment, meta

from cc_core.commons.files import wrapped_print
from cc_core.commons.schemas.red import red_jinja_schema
from cc_core.commons.exceptions import RedValidationError, RedVariablesError


def jinja_validation(jinja_data):
    try:
        jsonschema.validate(jinja_data, red_jinja_schema)
    except:
        raise RedValidationError('jinja file does not comply with jsonschema')


def fill_template(template, template_vals):
    filled_template = template
    template_vars = template_variables(template)

    if template_vars:
        t = Template(template)
        filled_template = t.render(template_vals)

    return filled_template


def template_values(template, jinja_data, non_interactive=True):
    template_vars = template_variables(template)

    if not template_vars:
        return None

    template_vals = {}
    undeclared_vars = []

    jinja_data = jinja_data or {}

    for var in template_vars:
        if var in jinja_data:
            template_vals[var] = jinja_data[var]
        else:
            undeclared_vars.append(var)

    if undeclared_vars:
        if non_interactive:
            raise RedVariablesError('RED_FILE contains undeclared variables: {}'.format(undeclared_vars))

        out = [
            'RED_FILE contains the following undeclared variables:'
        ]
        out += undeclared_vars
        out += [
            '',
            'Set variables interactively...',
            ''
        ]
        wrapped_print(out)

        for var in undeclared_vars:
            template_vals[var] = getpass('{}: '.format(var))

    return template_vals


def template_variables(template):
    environment = Environment()
    ast = environment.parse(template)
    variables = list(meta.find_undeclared_variables(ast))
    variables.sort(reverse=True)
    return variables
