import docker
# noinspection PyProtectedMember
from docker.models.containers import Container, _create_container_args
from docker.models.images import Image

from cc_core.commons.engines import NVIDIA_DOCKER_RUNTIME

GPU_CAPABILITIES = [['gpu'], ['nvidia'], ['compute'], ['compat32'], ['graphics'], ['utility'], ['video'], ['display']]


def create_container_with_gpus(client, image, command, available_runtimes, gpus=None, environment=None, **kwargs):
    """
    Creates a docker container with optional gpus, accessible by nvidia runtime or nvidia-container-toolkit.

    If gpus are required it first looks for the nvidia runtime. If nvidia runtime is configured, sets this nvidia
    runtime and nvidia environment variables.
    If gpus are required, but no nvidia runtime is configured, a device request for the requested gpus is created.

    :param client: The docker client to use for the creation of the container.
    :type client: docker.DockerClient
    :param image: The image for the docker container
    :type image: str
    :param command: The command to execute inside this container
    :type command: str or list[str]
    :param available_runtimes: A list of available docker runtimes configured inside the given client
    :type available_runtimes: list[str]
    :param gpus: One of the following options:
                 - The string 'all' to use all available gpus
                 - An int representing the number of gpus to use
                 - a list of device ids or uuids
                 - None to not use gpus
    :type gpus: str or int or List[str or int]
    :param environment: The environment of this docker container
    :type environment: dict
    :param kwargs: The same arguments as in docker.DockerClient.containers.create(kwargs)
    :return: A newly created docker container
    :rtype: Container
    """
    if gpus:
        if environment is None:
            environment = {}
        environment['NVIDIA_VISIBLE_DEVICES'] = _get_nvidia_visible_devices_from_gpus(gpus)
        kwargs['environment'] = environment

        if NVIDIA_DOCKER_RUNTIME in available_runtimes:
            kwargs['runtime'] = NVIDIA_DOCKER_RUNTIME
            container = client.containers.create(image, command, **kwargs)
        else:
            # if nvidia runtime is not installed on this docker daemon, but gpus are required:
            # try creation with device request
            container = _create_with_nvidia_container_toolkit(client, image, command, gpus, kwargs)
    else:
        container = client.containers.create(image, command, **kwargs)
    return container


def _create_with_nvidia_container_toolkit(client, image, command, gpus, kwargs):
    """
    This function adds the gpu option to the normal client.containers.create(...) function and adds a device request.
    This function does not modify the environment variable.

    :param client: The docker client to use for this create
    :type client: docker.DockerClient
    :param image: The image for this docker container
    :type image: str
    :param command: The command for this docker container
    :type command: str or list[str]
    :param gpus: One of the following options:
                 - The string 'all' to use all available gpus
                 - An int representing the number of gpus to use
                 - a list of device ids or uuids
    :type gpus: str or int or List[str or int]
    :param kwargs: The kwargs of the docker.DockerClient.containers.create() function
    """
    # start addition
    device_request = _get_gpu_device_request(gpus)
    # end addition

    if isinstance(image, docker.models.images.Image):
        image = image.id
    kwargs['image'] = image
    kwargs['command'] = command
    # noinspection PyProtectedMember
    kwargs['version'] = client.api._version
    create_kwargs = _create_container_args(kwargs)

    # addition to the original create function
    create_kwargs['host_config']['DeviceRequests'] = [device_request]
    # end addition

    resp = client.api.create_container(**create_kwargs)
    return client.containers.get(resp['Id'])


def _get_gpu_device_request(gpus):
    """
    :param gpus: The string 'all', an int representing the number of gpus to use or a list of device ids
    :type gpus: str or int or List[str]
    """
    if gpus == 'all':
        return {
            'Driver': 'nvidia',
            'Capabilities': GPU_CAPABILITIES,
            'Count': -1,  # enable all gpus
        }

    elif isinstance(gpus, int):
        if gpus <= 0:
            raise ValueError('gpus is not a positive number: {}'.format(gpus))
        return {
            'Driver': 'nvidia',
            'Capabilities': GPU_CAPABILITIES,
            'Count': gpus,
        }

    elif isinstance(gpus, list):
        return {
            'Driver': 'nvidia',
            'Capabilities': GPU_CAPABILITIES,
            'DeviceIDs': [str(gpu) for gpu in gpus],
        }

    raise TypeError('gpus should be the string "all" an int or a list, but found "{}"'.format(gpus))


def _get_nvidia_visible_devices_from_gpus(gpus):
    """
    Returns the value for the NVIDIA_VISIBLE_DEVICES environment variable.

    :param gpus: The string 'all', an int representing the number of gpus to use or a list of device ids
    :type gpus: str or int or List[str]
    :return: The value for the NVIDIA_VISIBLE_DEVICES environment variable
    :rtype: str

    :raise ValueError: If gpus is an negative int
    :raise TypeError: If gpus is not one of the specified types
    """
    if gpus == 'all':
        return 'all'

    elif isinstance(gpus, int):
        if gpus <= 0:
            raise ValueError('gpus is not a positive number: {}'.format(gpus))
        return ','.join(map(str, range(gpus)))

    elif isinstance(gpus, list):
        return ','.join([str(gpu_id) for gpu_id in gpus])

    raise TypeError('gpus should be the string "all" an int or a list, but found "{}"'.format(gpus))
