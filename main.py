#!/usr/bin/env python3
"""Write the entry image to $MAKEFUN_OUTPUT_DIR/entry.png.

The image (a colossal whale breaching beside a tiny red sailboat at
golden sunset) lives next to this program as entry.png. This program
copies it to the output directory after checking it against the
competition's limits: PNG or JPEG magic bytes, at most 1 MiB, at most
1024 by 1024 pixels, and a whole, well-formed image.
"""

import os
import struct
import sys

MAX_BYTES = 1_048_576
MAX_DIMENSION = 1024

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


def read_png_dimensions(data):
    """Return (width, height) from a PNG's IHDR chunk."""
    if len(data) < 33 or data[12:16] != b"IHDR":
        raise ValueError("PNG is missing its IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def read_jpeg_dimensions(data):
    """Return (width, height) from a JPEG's first SOF marker."""
    pos = 2
    while pos + 9 < len(data):
        if data[pos] != 0xFF:
            raise ValueError("JPEG marker stream is corrupt")
        marker = data[pos + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if pos + 4 > len(data):
            raise ValueError("JPEG segment is truncated")
        length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if length < 2 or pos + 2 + length > len(data):
            raise ValueError("JPEG segment is truncated")
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
            return width, height
        pos += 2 + length
    raise ValueError("JPEG has no SOF marker")


def validate(data):
    """Check magic bytes, size cap, dimensions and completeness."""
    if len(data) > MAX_BYTES:
        raise ValueError(
            "image is %d bytes, over the %d byte cap" % (len(data), MAX_BYTES)
        )
    if data[:8] == PNG_MAGIC:
        width, height = read_png_dimensions(data)
        if not _check_png_complete(data):
            raise ValueError("PNG is truncated: no IEND chunk")
    elif data[:3] == JPEG_MAGIC:
        width, height = read_jpeg_dimensions(data)
        if data[-2:] != b"\xff\xd9":
            raise ValueError("JPEG is truncated: no EOI marker")
    else:
        raise ValueError("image is neither PNG nor JPEG")
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise ValueError(
            "image is %dx%d, over the %d pixel cap"
            % (width, height, MAX_DIMENSION)
        )
    return width, height


def _check_png_complete(data):
    """True when a full IEND chunk (length 0, type IEND, CRC) is present."""
    pos = 8
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        if chunk_type == b"IEND":
            return pos + 12 == len(data)
        pos += 12 + length
    return False


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, "entry.png")
    with open(source, "rb") as handle:
        data = handle.read()
    width, height = validate(data)

    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not output_dir:
        print("MAKEFUN_OUTPUT_DIR is not set", file=sys.stderr)
        return 1
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, "entry.png")
    with open(target, "wb") as handle:
        handle.write(data)
    with open(target, "rb") as handle:
        written = handle.read()
    if written != data:
        print("output read-back does not match the source image",
              file=sys.stderr)
        return 1
    print("wrote %s (%d bytes, %dx%d)" % (target, len(data), width, height))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
