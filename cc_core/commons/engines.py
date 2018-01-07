from cc_core.commons.schemas.engines.execution import ccagency_schema as ee_ccagency_schema
from cc_core.commons.schemas.engines.container import docker_schema as ce_docker_schema
from cc_core.commons.schemas.engines.virtualization import vagrant_schema as ve_vagrant_schema
from cc_core.commons.schemas.engines.source import git_schema as se_git_schema
from cc_core.commons.schemas.engines.build import docker_schema as be_docker_schema

execution_engines = {
    'ccagency': ee_ccagency_schema
}

container_engines = {
    'docker': ce_docker_schema
}

virtualization_engines = {
    'vagrant': ve_vagrant_schema
}

source_engines = {
    'git': se_git_schema
}

build_engines = {
    'docker': be_docker_schema
}
