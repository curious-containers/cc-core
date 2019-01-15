import os
import sys
import types

import requests
import jsonschema
import psutil
import ruamel.yaml
import cc_core


START_MODULES = [requests, jsonschema, psutil, ruamel.yaml, cc_core]


def module_dependencies():
    d = {module.__name__: False for module in START_MODULES}
    _module_dependencies(d)
    return _valid_modules(d)


def _module_dependencies(d):
    candidates = []

    for module_name, checked in d.items():

        if not checked:
            d[module_name] = True

            for key, obj in sys.modules[module_name].__dict__.items():
                if not isinstance(obj, types.ModuleType):
                    if not isinstance(obj, types.FunctionType):
                        continue

                    if not (obj.__module__ and obj.__module__ in sys.modules):
                        continue

                    obj = sys.modules[obj.__module__]

                all_names = [obj.__name__]

                if '.' in obj.__name__:
                    split = obj.__name__.split('.')
                    for i in range(1, len(split)):
                        all_names.append('.'.join(split[:i]))

                for name in all_names:
                    if name in d:
                        continue

                    if name not in sys.modules:
                        continue

                    candidates.append(name)

    for module_name in candidates:
        d[module_name] = False

    if candidates:
        _module_dependencies(d)


def _valid_modules(d):
    stdlib_path = os.path.split(os.__file__)[0]
    valid_modules = []

    for module_name in d:
        module = sys.modules[module_name]
        if hasattr(module, '__file__') and module.__file__ and not module.__file__.startswith(stdlib_path):
            valid_modules.append(module_name)

    result = []
    for module_name in valid_modules:
        if '.' in module_name:
            shorter_name = '.'.join(module_name.split('.')[:-1])

            if shorter_name in valid_modules:
                continue

        result.append(module_name)

    return result
