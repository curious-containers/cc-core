from collections import OrderedDict

from cc_core.commons.schemas.red import red_schema, red_jinja_schema
from cc_core.commons.schemas.cwl import cwl_schema, cwl_job_schema
from cc_core.commons.schemas.engines.container import container_engines
from cc_core.commons.schemas.engines.execution import execution_engines
from cc_core.commons.schemas.connectors import connectors


schemas = OrderedDict([
    ('cwl', cwl_schema),
    ('cwl-job', cwl_job_schema),
    ('red', red_schema),
    ('red-jinja', red_jinja_schema)
])

for e, s in connectors.items():
    schemas['red-connector-{}'.format(e)] = s

for e, s in container_engines.items():
    schemas['red-engine-container-{}'.format(e)] = s

for e, s in execution_engines.items():
    schemas['red-engine-execution-{}'.format(e)] = s
