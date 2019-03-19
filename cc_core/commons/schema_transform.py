from copy import deepcopy


def transform(schema):
    """
    Transform a jsonschema by recursively adding optional doc keys and allowing null for optional keys
    :param schema: jsonschema dict, will not be transformed inplace
    :return: transformed jsonschema dict
    """
    schema = deepcopy(schema)
    _transform(schema)
    return schema


def _transform(schema):
    if 'anyOf' in schema:
        for subschema in schema['anyOf']:
            _transform(subschema)

    elif 'oneOf' in schema:
        for subschema in schema['oneOf']:
            _transform(subschema)

    elif 'type' in schema:
        if schema['type'] == 'array':
            subschema = schema.get('items')
            if subschema:
                _transform(subschema)

        elif schema['type'] == 'object':
            if 'patternProperties' in schema:
                for _, subschema in schema['patternProperties'].items():
                    _transform(subschema)

            elif 'properties' in schema:
                properties = schema['properties']

                # insert doc key
                properties['doc'] = {'type': 'string'}

                # insert null for optional keys
                required = schema.get('required', [])
                for key, subschema in properties.items():
                    if key not in required:
                        if 'oneOf' in subschema:
                            subschema['oneOf'].append({'type': 'null'})

                        elif 'type' in subschema or 'enum' in subschema:
                            properties[key] = {
                                'oneOf': [
                                    subschema,
                                    {'type': 'null'}
                                ]
                            }

                # recursion
                for _, subschema in properties.items():
                    _transform(subschema)
