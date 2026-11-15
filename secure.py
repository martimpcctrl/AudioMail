"""Guarda segredos com a criptografia do proprio Windows (DPAPI), sem biblioteca extra.

Os dados so podem ser abertos pela mesma conta de usuario, no mesmo computador.
"""
import ctypes


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _make_blob(data):
    buf = ctypes.create_string_buffer(data, len(data))
    return _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def _call(function, data):
    windll = ctypes.windll  # so existe no Windows; em outros sistemas levanta erro
    blob_in, _keep = _make_blob(data)
    blob_out = _Blob()
    ok = function(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out))
    if not ok:
        raise OSError("Falha na criptografia do Windows.")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        windll.kernel32.LocalFree(blob_out.pbData)


def encrypt(data):
    return _call(ctypes.windll.crypt32.CryptProtectData, data)


def decrypt(data):
    return _call(ctypes.windll.crypt32.CryptUnprotectData, data)
