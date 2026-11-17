"""Arhiva ZIP cu parolă (criptarea clasică PKWARE, „ZipCrypto”) pentru fluturașii trimiși pe e-mail.

Am ales criptarea clasică, nu AES: pe ea o deschid fără programe în plus Windows (Explorer), macOS și aplicațiile de pe
telefon. Python citește asemenea arhive (zipfile, cu `pwd`), dar nu le scrie — de aceea formatul e scris aici, după
APPNOTE.TXT (PKWARE): antetul local, datele (12 octeți de antet criptat + datele comprimate deflate, criptate),
directorul central și sfârșitul lui.
"""
import secrets
import struct
import zlib
from datetime import datetime

_TABLE = []
for _n in range(256):
    _c = _n
    for _ in range(8):
        _c = (_c >> 1) ^ 0xEDB88320 if _c & 1 else _c >> 1
    _TABLE.append(_c)


def _crc_byte(crc: int, b: int) -> int:
    return (crc >> 8) ^ _TABLE[(crc ^ b) & 0xFF]


class _Keys:
    def __init__(self, password: bytes):
        self.k0, self.k1, self.k2 = 0x12345678, 0x23456789, 0x34567890
        for b in password:
            self.update(b)

    def update(self, b: int):
        self.k0 = _crc_byte(self.k0, b)
        self.k1 = (self.k1 + (self.k0 & 0xFF)) & 0xFFFFFFFF
        self.k1 = (self.k1 * 134775813 + 1) & 0xFFFFFFFF
        self.k2 = _crc_byte(self.k2, (self.k1 >> 24) & 0xFF)

    def encrypt(self, data: bytes) -> bytes:
        out = bytearray(len(data))
        for i, b in enumerate(data):
            t = (self.k2 | 2) & 0xFFFF
            out[i] = b ^ (((t * (t ^ 1)) >> 8) & 0xFF)
            self.update(b)
        return bytes(out)


def _dos_time(when: datetime) -> tuple:
    return ((when.hour << 11) | (when.minute << 5) | (when.second // 2),
            ((max(when.year, 1980) - 1980) << 9) | (when.month << 5) | when.day)


def make_zip(files: list, password: str, when: datetime | None = None) -> bytes:
    """files = [(numele în arhivă, conținutul)] → arhiva ZIP, fiecare fișier criptat cu parola dată."""
    when = when or datetime.now()
    dos_time, dos_date = _dos_time(when)
    flags = 0x0001 | 0x0800  # criptat; numele în UTF-8
    out, central = bytearray(), bytearray()
    for name, content in files:
        raw_name = name.encode("utf-8")
        crc = zlib.crc32(content) & 0xFFFFFFFF
        packer = zlib.compressobj(9, zlib.DEFLATED, -15)
        packed = packer.compress(content) + packer.flush()
        keys = _Keys(password.encode("utf-8"))
        header = bytearray(secrets.token_bytes(11)) + bytes([(crc >> 24) & 0xFF])  # ultimul octet — verificarea parolei
        data = keys.encrypt(bytes(header)) + keys.encrypt(packed)
        offset = len(out)
        out += struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, flags, 8, dos_time, dos_date, crc, len(data), len(content),
                           len(raw_name), 0) + raw_name + data
        central += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, flags, 8, dos_time, dos_date, crc, len(data),
                               len(content), len(raw_name), 0, 0, 0, 0, 0, offset) + raw_name
    start = len(out)
    out += central
    out += struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(files), len(files), len(central), start, 0)
    return bytes(out)
