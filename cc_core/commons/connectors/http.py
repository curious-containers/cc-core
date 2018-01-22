import json
import jsonschema
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from cc_core.commons.schemas.connectors import http_schema


def _http_method_func(access):
    http_method = access['method'].lower()

    if http_method == 'get':
        return requests.get
    if http_method == 'put':
        return requests.put
    if http_method == 'post':
        return requests.post

    raise Exception('Invalid HTTP method: {}'.format(http_method))


def _auth_method_obj(access):
    if not access.get('auth'):
        return None

    auth = access['auth']
    auth_method = auth.get('method', 'basic').lower()

    if auth_method == 'basic':
        return HTTPBasicAuth(
            auth['username'],
            auth['password']
        )
    if auth_method == 'digest':
        return HTTPDigestAuth(
            auth['username'],
            auth['password']
        )

    raise Exception('Invalid auth method: {}'.format(auth_method))


class Http:
    @staticmethod
    def receive(access, internal):
        http_method_func = _http_method_func(access)
        auth_method_obj = _auth_method_obj(access)

        verify = True
        if access.get('disableSSLVerification'):
            verify = False

        r = http_method_func(
            access['url'],
            auth=auth_method_obj,
            verify=verify,
            stream=True
        )
        r.raise_for_status()

        with open(internal['path'], 'wb') as f:
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)

        r.raise_for_status()

    @staticmethod
    def receive_validate(access):
        jsonschema.validate(access, http_schema)

    @staticmethod
    def send(access, internal):
        http_method_func = _http_method_func(access)
        auth_method_obj = _auth_method_obj(access)
        
        verify = True
        if access.get('disableSSLVerification'):
            verify = False

        with open(internal['path'], 'rb') as f:
            r = http_method_func(
                access['url'],
                data=f,
                auth=auth_method_obj,
                verify=verify
            )
            r.raise_for_status()

    @staticmethod
    def send_validate(access):
        jsonschema.validate(access, http_schema)


class HttpJson:
    @staticmethod
    def receive(access, internal):
        http_method_func = _http_method_func(access)
        auth_method_obj = _auth_method_obj(access)

        verify = True
        if access.get('disableSSLVerification'):
            verify = False

        r = http_method_func(
            access['url'],
            auth=auth_method_obj,
            verify=verify
        )
        r.raise_for_status()
        data = r.json()

        with open(internal['path'], 'wb') as f:
            json.dump(data, f)

    @staticmethod
    def receive_validate(access):
        jsonschema.validate(access, http_schema)

    @staticmethod
    def send(access, internal):
        http_method_func = _http_method_func(access)
        auth_method_obj = _auth_method_obj(access)

        with open(internal['path']) as f:
            data = json.load(f)

        if access.get('mergeAgencyData') and internal.get('agencyData'):
            for key, val in internal['agencyData'].items():
                data[key] = val

        verify = True
        if access.get('disableSSLVerification'):
            verify = False

        r = http_method_func(
            access['url'],
            json=data,
            auth=auth_method_obj,
            verify=verify
        )
        r.raise_for_status()

    @staticmethod
    def send_validate(access):
        jsonschema.validate(access, http_schema)
