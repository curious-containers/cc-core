import os
import sys
import types
from subprocess import Popen, PIPE

CC_DIR = 'cc'
MOD_DIR = os.path.join(CC_DIR, 'mod')
PYMOD_DIR = os.path.join(CC_DIR, 'pymod')
LIB_DIR = os.path.join(CC_DIR, 'lib')


def module_dependencies(modules):
    d = {m.__name__: (m, False) for m in modules}
    _module_dependencies(d)
    file_modules = {module_name: m for module_name, (m, _) in d.items() if hasattr(m, '__file__') and m.__file__ is not None}
    c_modules = {module_name: m for module_name, m in file_modules.items() if m.__file__.endswith('.so')}
    modules = _valid_modules(file_modules)
    return modules, c_modules


def _module_dependencies(d):
    candidates = []

    for module_name, (m, checked) in d.items():
        if checked:
            continue

        d[module_name] = (m, True)

        for key, obj in m.__dict__.items():
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
        d[module_name] = (sys.modules[module_name], False)

    if candidates:
        _module_dependencies(d)


def restore_original_environment():
    for envvar in ['LD_LIBRARY_PATH', 'PYTHONPATH', 'PYTHONHOME']:
        envvar_bak = '{}_BAK'.format(envvar)
        if envvar_bak in os.environ:
            os.environ[envvar] = os.environ[envvar_bak]
            del os.environ[envvar_bak]
            if not os.environ[envvar]:
                del os.environ[envvar]


def interpreter_command():
    return [
        'LD_LIBRARY_PATH_BAK=${LD_LIBRARY_PATH}',
        'PYTHONPATH_BAK=${PYTHONPATH}',
        'PYTHONHOME_BAK=${PYTHONHOME}',
        'LD_LIBRARY_PATH={}'.format(os.path.join('/', LIB_DIR)),
        'PYTHONPATH={}:{}:{}:{}'.format(
            os.path.join('/', PYMOD_DIR),
            os.path.join('/', PYMOD_DIR, 'lib-dynload'),
            os.path.join('/', PYMOD_DIR, 'site-packages'),
            os.path.join('/', MOD_DIR)
        ),
        'PYTHONHOME={}'.format(os.path.join('/', PYMOD_DIR)),
        os.path.join('/', LIB_DIR, 'ld.so'),
        os.path.join('/', LIB_DIR, 'python')
    ]


def _valid_modules(file_modules):
    stdlib_path = os.path.split(os.__file__)[0]
    valid_modules = {}

    for module_name, m in file_modules.items():
        if not m.__file__.startswith(stdlib_path):
            valid_modules[module_name] = m

    result = {}
    for module_name, m in valid_modules.items():
        if '.' in module_name:
            shorter_name = '.'.join(module_name.split('.')[:-1])

            if shorter_name in valid_modules:
                continue

        result[module_name] = m

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


def interpreter_dependencies(c_module_deps):
    candidates = {}

    for _, m in c_module_deps.items():
        links = ldd(m.__file__)

        candidates = {**candidates, **links}

    d = {'python': (sys.executable, False)}

    for name, path in candidates.items():
        if name not in d:
            d[name] = (path, False)

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

    for module_name, m in dependencies.items():
        dir_path, file_name = os.path.split(m.__file__)
        if file_name == '__init__.py':
            last_part = None
            n = len(module_name.split('.'))
            for _ in range(n):
                dir_path, last_part = os.path.split(dir_path)

            if last_part is not None:
                result.append([os.path.join(dir_path, last_part), os.path.join(mod_dir, last_part)])
        else:
            result.append([m.__file__, os.path.join(mod_dir, file_name)])

    return result


def interpreter_destinations(dependencies, prefix='/'):
    lib_dir = os.path.join(prefix, LIB_DIR)
    result = []

    for name, path in dependencies.items():
        result.append([path, os.path.join(lib_dir, name)])

    return result
