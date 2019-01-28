import os
import sys
import types
import inspect
from pprint import pprint
from subprocess import Popen, PIPE

CC_DIR = 'cc'
MOD_DIR = os.path.join(CC_DIR, 'mod')
PYMOD_DIR = os.path.join(CC_DIR, 'pymod')
LIB_DIR = os.path.join(CC_DIR, 'lib')


def module_dependencies(modules):
    d = {}
    for m in modules:
        if not inspect.ismodule(m):
            raise Exception('Not a module: {}'.format(m))
        try:
            source_path = inspect.getabsfile(m)
        except Exception:
            source_path = None

        d[m] = (False, source_path)

    _module_dependencies(d)
    file_modules = {m: source_path for m, (_, source_path) in d.items() if source_path is not None}
    c_modules = {m: source_path for m, source_path in file_modules.items() if source_path.endswith('.so')}
    return file_modules, c_modules


def _module_dependencies(d):
    candidates = {}

    for m, (checked, sp) in d.items():
        if checked:
            continue

        d[m] = (True, sp)

        for key, obj in m.__dict__.items():
            if not inspect.ismodule(obj):
                if not (hasattr(obj, '__module__') and obj.__module__ and obj.__module__ in sys.modules):
                    continue

                obj = sys.modules[obj.__module__]

            if obj in d:
                continue

            try:
                source_path = inspect.getabsfile(obj)
            except Exception:
                source_path = None

            candidates[obj] = (False, source_path)

    for m, t in candidates.items():
        d[m] = t

    for m, (checked, sp) in d.items():
        if not checked:
            _module_dependencies(d)
            break


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
        'PYTHONPATH={}'.format(
            os.path.join('/', MOD_DIR)
        ),
        'PYTHONHOME={}'.format(os.path.join('/', MOD_DIR)),
        os.path.join('/', LIB_DIR, 'ld.so'),
        os.path.join('/', LIB_DIR, 'python')
    ]


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
            if os.path.isabs(name):
                continue
            path = path.strip()
            path = path.split('(')[0].strip()
            result[name] = path
        elif line.startswith('/') and 'ld' in line:
            path = line.split('(')[0].strip()
            result['ld.so'] = path

    return result


def interpreter_dependencies(c_module_deps):
    candidates = {}

    for m, _ in c_module_deps.items():
        links = ldd(inspect.getabsfile(m))

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


def _dir_path_len(dir_path):
    i = 0
    while True:
        front, back = os.path.split(dir_path)
        dir_path = front
        if not back:
            break
        i += 1
    return i


def module_destinations(file_modules, prefix='/'):
    sys_paths = [os.path.abspath(p) for p in sys.path if os.path.isdir(p)]
    mod_dir = os.path.join(prefix, MOD_DIR)

    result = []

    for _, source_path in file_modules.items():
        common_path_size = -1
        common_path = None

        for sys_path in sys_paths:
            cp = os.path.commonpath([source_path, sys_path])
            cp_size = _dir_path_len(cp)
            if cp_size > common_path_size:
                common_path_size = cp_size
                common_path = cp

        rel_source_path = source_path[len(common_path):].lstrip('/')

        result.append((source_path, os.path.join(mod_dir, rel_source_path)))

    return result


def interpreter_destinations(dependencies, prefix='/'):
    lib_dir = os.path.join(prefix, LIB_DIR)
    result = []

    for name, path in dependencies.items():
        result.append([path, os.path.join(lib_dir, name)])

    return result
