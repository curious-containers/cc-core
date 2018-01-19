from cc_core.commons.schemas.red import red_schema, red_inputs_schema, red_outputs_schema
from cc_core.commons.schemas.cwl import cwl_schema, job_schema
from cc_core.commons.schemas.engines.container import container_engines
from cc_core.commons.schemas.engines.execution import execution_engines
from cc_core.commons.schemas.engines.virtualization import virtualization_engines


schemas = [
    ('cwl', cwl_schema),
    ('cwl-job', job_schema),
    ('red', red_schema),
    ('red-inputs', red_inputs_schema),
    ('red-outputs', red_outputs_schema)
]

for e, s in execution_engines.items():
    schemas.append(('red-execution-{}'.format(e), s))

for e, s in container_engines.items():
    schemas.append(('red-container-{}'.format(e), s))

for e, s in virtualization_engines.items():
    schemas.append(('red-virtualization-{}'.format(e), s))
