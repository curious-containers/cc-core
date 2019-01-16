import os
import sys
import types
from subprocess import Popen, PIPE


MOD_DIR = '/cc/mod'
LIB_DIR = '/cc/lib'
BIN_DIR = '/cc/bin'


def module_dependencies(modules):
    d = {m.__name__: False for m in modules}
    _module_dependencies(d)
    return _valid_modules(d)


def _module_dependencies(d):
    candidates = []

    for module_name, checked in d.items():

        if not checked:
            d[module_name] = True

            for key, obj in sys.modules[module_name].__dict__.items():
                if not isinstance(obj, types.ModuleType):

                    if not (hasattr(obj, '__module__') and obj.__module__ and obj.__module__ in sys.modules):
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


def ldd(file_path):
    sp = Popen('ldd "{}"'.format(file_path), stdout=PIPE, stderr=PIPE, shell=True, universal_newlines=True)
    std_out, std_err = sp.communicate()
    return_code = sp.returncode

    if return_code != 0:
        raise Exception('External program ldd returned exit code {}: {}'.format(return_code, std_err))

    result = {}

    for line in std_out.split('\n'):
        line = line.strip()
        if '=>' in line:
            name, path = line.split('=>')
            name = name.strip()
            path = path.strip()
            path = path.split('(')[0].strip()
            result[name] = path
        elif line.startswith('/') and 'ld-linux' in line:
            path = line.split('(')[0].strip()
            result['ld-linux.so'] = path

    return result


def interpreter_dependencies():
    d = {'python': (sys.executable, False)}
    _interpreter_dependencies(d)
    return {key: val for key, (val, _) in d.items()}


def _interpreter_dependencies(d):
    candidates = {}

    for name, (path, checked) in d.items():
        if checked:
            continue

        d[name] = (path, True)

        links = ldd(path)

        candidates = {**candidates, **links}

    found_new = False
    for name, path in candidates.items():
        if name not in d:
            d[name] = (path, False)
            found_new = True

    if found_new:
        _interpreter_dependencies(d)


def ccagent_bin(local_path):
    with open(local_path, 'w') as f:
        print(
            'LD_LIBRARY_PATH={lib} PYTHONPATH={mod} {lib}/ld-linux.so {lib}/python -m cc_core.agent $@'.format(
                lib=LIB_DIR, mod=MOD_DIR
            ),
            file=f
        )
