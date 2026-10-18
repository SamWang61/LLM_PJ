"""Split/reassemble ciphertext with ordered SHA-256 checks and no overwrites."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import os

from encrypted_backup import BLOCK, fingerprint, regular_file, stamp


PART_BYTES = 96 * 1024 * 1024  # Below the connector's observed 100 MiB limit.


def split(source, directory):
    source = regular_file(source)
    directory = Path(directory).resolve()
    before = source.stat()
    if before.st_size == 0:
        raise ValueError("Empty archive")
    directory.mkdir()  # A previous/incomplete transfer is never overwritten.
    parts = []
    whole = hashlib.sha256()
    with source.open("rb") as src:
        index = 0
        while True:
            block = src.read(BLOCK)
            if not block:
                break
            index += 1
            name = "archive.vcbak.part" + str(index).zfill(3)
            digest = hashlib.sha256()
            size = 0
            with (directory / name).open("xb") as dst:
                while block:
                    dst.write(block)
                    digest.update(block)
                    whole.update(block)
                    size += len(block)
                    if size == PART_BYTES:
                        break
                    block = src.read(min(BLOCK, PART_BYTES - size))
            parts.append({"name": name, "bytes": size, "sha256": digest.hexdigest()})
    if stamp(before) != stamp(source.stat()):
        raise ValueError("Source changed; incomplete directory must not be uploaded")
    report = {"version": 1, "ciphertext": {"bytes": before.st_size,
              "sha256": whole.hexdigest()}, "parts": parts}
    with (directory / "parts.json").open("x", encoding="utf-8", newline="\n") as out:
        json.dump(report, out, indent=2)
        out.write("\n")
    return report


def join(directory, output):
    directory = Path(directory).resolve(strict=True)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("Output exists")
    manifest = json.loads((directory / "parts.json").read_text(encoding="utf-8"))
    if manifest.get("version") != 1 or not manifest.get("parts"):
        raise ValueError("Incomplete parts manifest")
    names = set()
    for row in manifest["parts"]:
        name = row["name"]
        if (not name or Path(name).name != name or "/" in name or "\\" in name
                or ":" in name or name in {".", ".."} or name.casefold() in names):
            raise ValueError("Unsafe or duplicate part name")
        names.add(name.casefold())
        if fingerprint(regular_file(directory / name)) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            raise ValueError("Part mismatch")
    fd, temporary = tempfile.mkstemp(prefix=".reassemble-", dir=output.parent)
    try:
        with os.fdopen(fd, "wb") as dst:
            for row in manifest["parts"]:
                with regular_file(directory / row["name"]).open("rb") as src:
                    for block in iter(lambda: src.read(BLOCK), b""):
                        dst.write(block)
            dst.flush()
            os.fsync(dst.fileno())
        if fingerprint(Path(temporary)) != manifest["ciphertext"]:
            raise ValueError("Reassembled ciphertext mismatch")
        os.link(temporary, output)  # Atomic, refuses a concurrently created output.
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"verified": True, "parts": len(names), "ciphertext": manifest["ciphertext"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("split", "join"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "split":
        if args.source is None or args.output is not None:
            parser.error("split requires --source only")
        result = split(args.source, args.directory)
    else:
        if args.output is None or args.source is not None:
            parser.error("join requires --output only")
        result = join(args.directory, args.output)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
