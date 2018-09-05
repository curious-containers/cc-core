import re
from traceback import format_exc


def exception_format(secrets_data=None):
    exc_text = format_exc()
    if secrets_data:
        exc_text = re.sub('|'.join([val for _, val in secrets_data.items()]), '********', exc_text)
    return [l.replace('"', '').replace("'", '') for l in exc_text.split('\n') if l]


class ArgumentError(Exception):
    pass


class AgentError(Exception):
    pass


class EngineError(Exception):
    pass


class FileError(Exception):
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
