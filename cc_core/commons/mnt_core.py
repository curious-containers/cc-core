import os
import sys
import inspect
import pkgutil
from subprocess import Popen, PIPE

CC_DIR = 'cc'
MOD_DIR = os.path.join(CC_DIR, 'mod')
LIB_DIR = os.path.join(CC_DIR, 'lib')


def module_dependencies(modules):
    # additional modules
    modules = modules[:]
    try:
        import runpy
        modules.append(runpy)
    except ImportError:
        pass
    try:
        import keyword
        modules.append(keyword)
    except ImportError:
        pass
    try:
        import opcode
        modules.append(opcode)
    except ImportError:
        pass
    try:
        import sysconfig
        modules.append(sysconfig)
    except ImportError:
        pass
    try:
        import _sysconfigdata
        modules.append(_sysconfigdata)
    except ImportError:
        pass
    try:
        import _sysconfigdata_m
        modules.append(_sysconfigdata_m)
    except ImportError:
        pass

    # find modules recursively
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
    source_paths = [source_path for _, (_, source_path) in d.items() if source_path is not None]

    # get packages of found modules
    all_packages = set([module_name for _, module_name, is_pkg in pkgutil.walk_packages(sys.path) if is_pkg])
    required_packages = [m.__package__ for m in d if hasattr(m, '__package__') and m.__package__ in all_packages]

    # guess more package names
    for m in d:
        if hasattr(m, '__name__') and isinstance(m.__name__, str):
            split_name = m.__name__.split('.')

            for i in range(len(split_name) + 1):
                part = '.'.join(split_name[:i])
                if part in all_packages:
                    required_packages.append(part)

    required_packages = list(set(required_packages))

    # get additional files (data or hidden modules) from packages
    site_source_dir = None

    for sys_path in sys.path:
        for loader, module_name, is_pkg in pkgutil.walk_packages([sys_path]):
            found_module = loader.find_module(module_name)
            try:
                source_path = inspect.getabsfile(found_module)
            except TypeError:
                module_dir = os.path.join(*module_name.split('.'))
                source_path = os.path.join(sys_path, module_dir)

            if os.path.isdir(source_path):
                source_dir = source_path
            else:
                source_dir, _ = os.path.split(source_path)

            if module_name == 'site':
                site_source_dir = source_dir

            if not (is_pkg and module_name in required_packages):
                continue

            for dir_path, _, file_names in os.walk(source_dir):
                is_pycache = False
                front = dir_path
                while True:
                    front, back = os.path.split(front)
                    if back == '__pycache__':
                        is_pycache = True
                        break
                    elif not back:
                        break

                if is_pycache:
                    continue

                for file_name in file_names:
                    source_paths.append(os.path.join(dir_path, file_name))

    if site_source_dir is not None:
        source_paths += _site_files(site_source_dir)

    source_paths = list(set(source_paths))

    # get C dependencies by filename
    c_source_paths = [source_path for source_path in source_paths if source_path.endswith('.so')]
    return source_paths, c_source_paths


def _module_dependencies(d):
    candidates = {}

    for m, (checked, sp) in d.items():
        if checked:
            continue

        d[m] = (True, sp)

        for key, obj in m.__dict__.items():
            if not inspect.ismodule(obj):
                obj = inspect.getmodule(obj)

                if obj is None:
                    continue

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


def _site_files(site_source_dir):
    file_names = ['orig-prefix.txt', 'no-global-site-packages.txt']

    result = []

    for file_name in file_names:
        file_path = os.path.join(site_source_dir, file_name)
        if os.path.exists(file_path):
            result.append(file_path)

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
            if os.path.isabs(name):
                continue
            path = path.strip()
            path = path.split('(')[0].strip()
            result[name] = path
        elif line.startswith('/') and 'ld' in line:
            path = line.split('(')[0].strip()
            result['ld.so'] = path

    return result


def interpreter_dependencies(c_source_paths):
    candidates = {}

    for source_path in c_source_paths:
        links = ldd(source_path)

        candidates = {**candidates, **links}

    d = {'python': (sys.executable, False)}

    for name, path in candidates.items():
        if name not in d:
            d[name] = (path, False)

    _interpreter_dependencies(d)
    deps = {name: path for name, (path, _) in d.items()}

    libc_dir = _libc_dir(deps)
    if libc_dir is not None:
        additional_dependencies = _additional_dependencies_from(libc_dir)
        deps = {**deps, **additional_dependencies}

    return deps


def _libc_dir(deps):
    for name, path in deps.items():
        file_dir, file_name = os.path.split(path)
        if file_name.startswith('libc.so'):
            return file_dir


def _additional_dependencies_from(libc_dir):
    file_patterns = ['libnss_dns.so', 'libresolv.so']
    result = {}

    for file_name in os.listdir(libc_dir):
        file_path = os.path.join(libc_dir, file_name)
        if not os.path.isfile(file_path):
            continue
        for file_pattern in file_patterns:
            if file_name.startswith(file_pattern):
                result[file_name] = file_path

    return result


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


def module_destinations(source_paths, prefix='/'):
    sys_paths = [os.path.abspath(p) for p in sys.path if os.path.isdir(p)]
    mod_dir = os.path.join(prefix, MOD_DIR)

    result = []

    for source_path in source_paths:
        common_path_size = -1
        common_path = None

        for sys_path in sys_paths:
            cp = os.path.commonpath([source_path, sys_path])
            cp_size = _dir_path_len(cp)
            if cp_size > common_path_size:
                common_path_size = cp_size
                common_path = cp

        rel_source_path = source_path[len(common_path):].lstrip('/')

        result.append([
            os.path.realpath(source_path),
            os.path.join(mod_dir, rel_source_path)
        ])

    return result


def interpreter_destinations(dependencies, prefix='/'):
    lib_dir = os.path.join(prefix, LIB_DIR)
    result = []

    for name, path in dependencies.items():
        result.append([
            os.path.realpath(path),
            os.path.join(lib_dir, name)
        ])

    return result
