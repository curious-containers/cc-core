import os
import sys
import types
from subprocess import Popen, PIPE

CC_DIR = 'cc'
MOD_DIR = os.path.join(CC_DIR, 'mod')
PYMOD_DIR = os.path.join(CC_DIR, 'pymod')
LIB_DIR = os.path.join(CC_DIR, 'lib')


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


def ldconfig():
    sp = Popen('ldconfig -p', stdout=PIPE, stderr=PIPE, shell=True, universal_newlines=True)
    std_out, std_err = sp.communicate()
    return_code = sp.returncode

    if return_code != 0:
        raise Exception('External program ldconfig -p returned exit code {}: {}'.format(return_code, std_err))

    result = {}

    for line in std_out.split('\n'):
        line = line.strip()
        if '=>' in line:
            name, path = line.split('=>')
            name = name.strip()
            name = name.split('(')[0].strip()
            path = path.strip()
            result[name] = path

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
        elif line.startswith('/') and 'ld' in line:
            path = line.split('(')[0].strip()
            result['ld.so'] = path

    return result


def interpreter_dependencies():
    ldconfig_result = ldconfig()
    libssl_names = [name for name in ldconfig_result if 'libssl.so' in name]

    d = {'python': (sys.executable, False)}

    for name in libssl_names:
        d[name] = (ldconfig_result[name], False)

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


def module_destinations(dependencies, prefix='/'):
    pymod_dir = os.path.join(prefix, PYMOD_DIR)
    mod_dir = os.path.join(prefix, MOD_DIR)

    stdlib_path = os.path.split(os.__file__)[0]
    result = [[stdlib_path, pymod_dir]]

    for module_name in dependencies:
        module = sys.modules[module_name]
        file_path = module.__file__
        dir_path, file_name = os.path.split(file_path)
        if file_name == '__init__.py':
            last_part = None
            n = len(module_name.split('.'))
            for _ in range(n):
                dir_path, last_part = os.path.split(dir_path)

            if last_part is not None:
                result.append([os.path.join(dir_path, last_part), os.path.join(mod_dir, last_part)])
        else:
            result.append([file_path, os.path.join(mod_dir, file_name)])

    return result


def interpreter_destinations(dependencies, prefix='/'):
    lib_dir = os.path.join(prefix, LIB_DIR)
    result = []

    for name, path in dependencies.items():
        result.append([path, os.path.join(lib_dir, name)])

    return result
