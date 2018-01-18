from cc_core.commons.schemas.faice import faice_schema, inputs_schema, outputs_schema
from cc_core.commons.schemas.cwl import cwl_schema, job_schema
from cc_core.commons.schemas.engines.build import build_engines
from cc_core.commons.schemas.engines.container import container_engines
from cc_core.commons.schemas.engines.execution import execution_engines
from cc_core.commons.schemas.engines.hardware import hardware_engines
from cc_core.commons.schemas.engines.os import os_engines
from cc_core.commons.schemas.engines.source import source_engines
from cc_core.commons.schemas.engines.virtualization import virtualization_engines


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

for e, s in build_engines.items():
    schemas.append(('engine-build-{}'.format(e), s))

for e, s in source_engines.items():
    schemas.append(('engine-source-{}'.format(e), s))

for e, s in os_engines.items():
    schemas.append(('engine-os-{}'.format(e), s))

for e, s in virtualization_engines.items():
    schemas.append(('engine-virtualization-{}'.format(e), s))

for e, s in hardware_engines.items():
    schemas.append(('engine-hardware-{}'.format(e), s))
