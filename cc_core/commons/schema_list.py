from cc_core.commons.schemas.faice import faice_schema, inputs_schema, outputs_schema
from cc_core.commons.schemas.cwl import cwl_schema, job_schema
from cc_core.commons.engines import execution_engines, container_engines, virtualization_engines
from cc_core.commons.engines import source_engines, build_engines


schemas = [
    ('faice', faice_schema),
    ('faice-inputs', inputs_schema),
    ('faice-outputs', outputs_schema),
    ('cwl', cwl_schema),
    ('cwl-job', job_schema)
]

for e, s in execution_engines.items():
    schemas.append(('engine-execution-{}'.format(e), s))

for e, s in container_engines.items():
    schemas.append(('engine-container-{}'.format(e), s))

for e, s in virtualization_engines.items():
    schemas.append(('engine-virtualization-{}'.format(e), s))

for e, s in source_engines.items():
    schemas.append(('engine-source-{}'.format(e), s))

for e, s in build_engines.items():
    schemas.append(('engine-build-{}'.format(e), s))
