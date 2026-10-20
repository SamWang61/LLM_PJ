"""Encrypt an existing private archive; never upload or extract it.

Format v1: authenticated header (magic, 96-bit random nonce, uint64 size,
SHA-256), AES-256-GCM ciphertext, full 128-bit tag. Large archives are streamed.
Use a private output directory and keep the 32-byte key in a separate location.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


MAGIC = b"VCBKUP1\0"
HEADER = struct.Struct(">8s12sQ32s")
TAG_BYTES = 16
BLOCK = 1024 * 1024
MAX_BYTES = (1 << 36) - 32  # GCM per-message bound, checked before encryption.


def regular_file(path):
    path = Path(path)
    if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
        raise ValueError("Input links are not supported")
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError("Input must be a regular file")
    return path


def fingerprint(path):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK), b""):
            digest.update(block)
    if stamp(before) != stamp(path.stat()):
        raise ValueError("Source changed during hashing")
    return {"bytes": before.st_size, "sha256": digest.hexdigest()}


def stamp(stat):
    return stat.st_size, stat.st_mtime_ns, stat.st_ino


def keygen(path):
    # The caller must provision/restrict the directory ACL on Windows first.
    with Path(path).open("xb") as stream:
        if os.name != "nt":
            os.chmod(stream.fileno(), 0o600)
        stream.write(os.urandom(32))
        stream.flush()
        os.fsync(stream.fileno())
    return {"key_created": True}


def paths(source, output, key_file):
    source = regular_file(source)
    key_file = regular_file(key_file)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing output")
    if key_file.is_relative_to(output.parent):
        raise ValueError("Keep the key outside the output directory")
    if source == key_file or output == key_file:
        raise ValueError("Key and archive paths must be separate")
    key = key_file.read_bytes()
    if len(key) != 32:
        raise ValueError("A 32-byte random key file is required")
    return source, output, key


def encrypt(source, output, key_file):
    source, output, key = paths(source, output, key_file)
    before = source.stat()
    if before.st_size > MAX_BYTES:
        raise ValueError("Archive exceeds the format size bound")
    plain = fingerprint(source)
    if stamp(before) != stamp(source.stat()):
        raise ValueError("Source changed before encryption")
    nonce = os.urandom(12)
    header = HEADER.pack(MAGIC, nonce, plain["bytes"], bytes.fromhex(plain["sha256"]))
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    cipher.authenticate_additional_data(header)
    digest = hashlib.sha256()
    created = False
    try:
        with source.open("rb") as src, output.open("xb") as dst:
            created = True
            dst.write(header)
            for block in iter(lambda: src.read(BLOCK), b""):
                digest.update(block)
                dst.write(cipher.update(block))
            dst.write(cipher.finalize())
            dst.write(cipher.tag)
            dst.flush()
            os.fsync(dst.fileno())
        if (stamp(before) != stamp(source.stat())
                or digest.hexdigest() != plain["sha256"]):
            raise ValueError("Source changed during encryption")
        return {"format": 1, "algorithm": "AES-256-GCM", "plaintext": plain,
                "ciphertext": fingerprint(output)}
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise


def decrypt(source, output, key_file):
    source, output, key = paths(source, output, key_file)
    before = source.stat()
    temporary = None
    try:
        with source.open("rb") as src:
            raw = src.read(HEADER.size)
            if len(raw) != HEADER.size:
                raise ValueError("Truncated backup header")
            magic, nonce, size, expected = HEADER.unpack(raw)
            if (magic != MAGIC or size > MAX_BYTES
                    or before.st_size != HEADER.size + size + TAG_BYTES):
                raise ValueError("Invalid backup header or length")
            src.seek(-TAG_BYTES, os.SEEK_END)
            tag = src.read(TAG_BYTES)
            src.seek(HEADER.size)
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
            cipher.authenticate_additional_data(raw)
            digest = hashlib.sha256()
            # Unauthenticated plaintext is private and never published as output.
            fd, temporary = tempfile.mkstemp(prefix=".decrypt-", dir=output.parent)
            with os.fdopen(fd, "wb") as dst:
                remaining = size
                while remaining:
                    block = src.read(min(BLOCK, remaining))
                    if not block:
                        raise ValueError("Truncated backup ciphertext")
                    remaining -= len(block)
                    plain = cipher.update(block)
                    digest.update(plain)
                    dst.write(plain)
                dst.write(cipher.finalize())  # Raises InvalidTag before publication.
                dst.flush()
                os.fsync(dst.fileno())
            if (digest.digest() != expected
                    or stamp(before) != stamp(source.stat())):
                raise ValueError("Backup changed or plaintext hash differs")
            # Hard-link creation is atomic and refuses an existing destination.
            os.link(temporary, output)
        return {"authenticated": True, "plaintext": {
            "bytes": size, "sha256": digest.hexdigest()}}
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("keygen", "encrypt", "decrypt"))
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "keygen":
        if args.source or args.output:
            parser.error("keygen accepts only --key-file")
        report = keygen(args.key_file)
    else:
        if args.source is None or args.output is None:
            parser.error("--source and --output are required")
        report = {"encrypt": encrypt, "decrypt": decrypt}[args.mode](
            args.source, args.output, args.key_file)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
