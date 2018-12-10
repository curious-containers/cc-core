import sys

import re
from traceback import format_exc


def _lstrip_quarter(s):
    len_s = len(s)
    s = s.lstrip()
    len_s_strip = len(s)
    quarter = (len_s - len_s_strip) // 4
    return ' ' * quarter + s


def exception_format(secret_values=None):
    exc_text = format_exc()
    if secret_values:
        exc_text = re.sub('|'.join(secret_values), '********', exc_text)
    return [_lstrip_quarter(l.replace('"', '').replace("'", '').rstrip()) for l in exc_text.split('\n') if l]


def print_exception(exception):
    """
    Prints the exception message and the name of the exception class.

    :param exception: The exception to print
    """

    print("[{}]".format(type(exception).__name__), file=sys.stderr)
    print(str(exception), file=sys.stderr)


class ArgumentError(Exception):
    pass


class AgentError(Exception):
    pass


class EngineError(Exception):
    pass


class FileError(Exception):
    pass


class DirectoryError(Exception):
    pass


class JobExecutionError(Exception):
    pass


class CWLSpecificationError(Exception):
    pass


class JobSpecificationError(Exception):
    pass


class RedSpecificationError(Exception):
    pass


class RedValidationError(Exception):
    pass


class RedVariablesError(Exception):
    pass


class ConnectorError(Exception):
    pass


class AccessValidationError(Exception):
    pass


class AccessError(Exception):
    pass
