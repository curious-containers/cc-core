from os import urandom
from binascii import hexlify
from hmac import compare_digest


def generate_secret():
    return hexlify(urandom(24)).decode('utf-8')


def compare_secrets(a, b):
    return compare_digest(a, b)
