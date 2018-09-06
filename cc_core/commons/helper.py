from os import urandom
from binascii import hexlify


def generate_secret():
    return hexlify(urandom(24)).decode('utf-8')
