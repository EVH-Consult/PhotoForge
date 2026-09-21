from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

FORMAT_BY_EXTENSION: dict[str, str] = {
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
    ".png": "png",
    ".heic": "heic",
    ".heif": "heif",
    ".tif": "tiff",
    ".tiff": "tiff",
    ".cr2": "cr2",
    ".nef": "nef",
    ".arw": "arw",
    ".mp4": "mp4",
    ".mov": "mov",
}

CANONICAL_EXTENSION: dict[str, str] = {
    "jpeg": ".jpg",
    "png": ".png",
    "heic": ".heic",
    "heif": ".heif",
    "tiff": ".tif",
    "cr2": ".cr2",
    "nef": ".nef",
    "arw": ".arw",
    "mp4": ".mp4",
    "mov": ".mov",
}

LIVE_PHOTO_STILL_FORMATS = frozenset({"jpeg", "heic", "heif"})

_PIL_FORMATS = {
    "png": frozenset({"PNG"}),
    "tiff": frozenset({"TIFF"}),
}
_HEIF_BRANDS = frozenset(
    {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}
)
_MP4_BRANDS = frozenset(
    {
        b"avc1",
        b"dash",
        b"iso2",
        b"iso3",
        b"iso4",
        b"iso5",
        b"iso6",
        b"isom",
        b"m4v ",
        b"mp41",
        b"mp42",
    }
)
_MOV_BRANDS = frozenset({b"qt  "})


def media_format_for(path: Path) -> str | None:
    return FORMAT_BY_EXTENSION.get(path.suffix.lower())


def validate_media_file(path: Path, media_format: str) -> None:
    """Apply the deterministic structural validation contract for a media format."""
    if media_format in _PIL_FORMATS:
        _validate_with_pillow(path, _PIL_FORMATS[media_format])
        return

    header = _read_header(path, 32)
    if media_format in {"heic", "heif"}:
        _validate_iso_base_media(header, _HEIF_BRANDS, "HEIC/HEIF")
    elif media_format == "cr2":
        if len(header) < 10 or header[:4] != b"II*\x00" or header[8:10] != b"CR":
            raise ValueError("invalid CR2 signature")
    elif media_format in {"nef", "arw"}:
        if header[:4] not in {b"II*\x00", b"MM\x00*"}:
            raise ValueError(f"invalid {media_format.upper()} TIFF signature")
    elif media_format == "mp4":
        _validate_iso_base_media(header, _MP4_BRANDS, "MP4")
    elif media_format == "mov":
        _validate_iso_base_media(header, _MOV_BRANDS, "MOV")
    else:
        raise ValueError(f"unsupported media format: {media_format}")


def _validate_with_pillow(path: Path, expected_formats: frozenset[str]) -> None:
    try:
        with Image.open(path) as image:
            if image.format not in expected_formats:
                raise ValueError(
                    f"content format {image.format!r} does not match {sorted(expected_formats)!r}"
                )
            image.verify()
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError("image content is unreadable") from exc


def _read_header(path: Path, size: int) -> bytes:
    try:
        with path.open("rb") as stream:
            return stream.read(size)
    except OSError as exc:
        raise ValueError("media header is unreadable") from exc


def _validate_iso_base_media(
    header: bytes,
    accepted_brands: frozenset[bytes],
    label: str,
) -> None:
    if len(header) < 12 or header[4:8] != b"ftyp":
        raise ValueError(f"invalid {label} ftyp box")
    box_size = int.from_bytes(header[:4], "big")
    if box_size < 12:
        raise ValueError(f"invalid {label} ftyp box size")
    brands = {header[8:12]}
    brands.update(
        header[index : index + 4]
        for index in range(16, min(len(header), box_size), 4)
    )
    if not brands.intersection(accepted_brands):
        raise ValueError(f"unsupported {label} brand")
