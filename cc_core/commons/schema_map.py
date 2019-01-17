from collections import OrderedDict

from cc_core.commons.schemas.red import red_schema, fill_schema
from cc_core.commons.schemas.cwl import cwl_schema, cwl_job_schema, cwl_job_listing_schema
from cc_core.commons.schemas.engines.container import container_engines
from cc_core.commons.schemas.engines.execution import execution_engines


schemas = OrderedDict([
    ('cwl', cwl_schema),
    ('cwl-job', cwl_job_schema),
    ('red', red_schema),
    ('fill', fill_schema),
    ('listing', cwl_job_listing_schema)
])

for e, s in container_engines.items():
    schemas['red-engine-container-{}'.format(e)] = s

for e, s in execution_engines.items():
    schemas['red-engine-execution-{}'.format(e)] = s
