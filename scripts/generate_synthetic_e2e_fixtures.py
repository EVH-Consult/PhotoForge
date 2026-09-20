from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = REPOSITORY_ROOT / "tests" / "e2e" / "fixtures" / "demo" / "input"

IMAGE_NAMES = (
    *(
        f"IMAG{number:04d}.jpg"
        for number in range(166, 205)
        if number not in {175, 192}
    ),
    "IMAG0202_1.jpg",
    "JPEG_20180316_195505_111704202.jpg",
    "JPEG_20180318_134422_1026864567.jpg",
    "JPEG_20180318_143915_1770235956.jpg",
    "JPEG_20180319_123935_715986013.jpg",
)

DUPLICATE_PATHS = (
    ("IMAG0166.jpg", "duplicates/IMAG0166.jpg"),
    ("IMAG0167.jpg", "duplicates/IMAG0167.jpg"),
    ("IMAG0168.jpg", "duplicates/IMAG0168.jpg"),
    ("IMAG0169.jpg", "nested/level1/IMAG0169.jpg"),
    ("IMAG0170.jpg", "nested/level1/IMAG0170.jpg"),
    ("IMAG0171.jpg", "nested/level1/IMAG0171.jpg"),
)


def _gps_coordinate(
    value: float,
    positive: str,
    negative: str,
) -> tuple[str, tuple[float, float, float]]:
    reference = positive if value >= 0 else negative
    absolute = abs(value)
    degrees = int(absolute)
    minutes_float = (absolute - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    return reference, (float(degrees), float(minutes), seconds)


def _synthetic_exif(index: int) -> Image.Exif:
    timestamp = datetime(2024, 1, 1, 12, 0, 0) + timedelta(minutes=index * 7)
    latitude = 12.345 + index / 1000
    longitude = 34.567 + index / 1000
    latitude_ref, latitude_dms = _gps_coordinate(latitude, "N", "S")
    longitude_ref, longitude_dms = _gps_coordinate(longitude, "E", "W")

    exif = Image.Exif()
    exif[271] = "PhotoForge"
    exif[272] = "Synthetic E2E Camera"
    exif[36867] = timestamp.strftime("%Y:%m:%d %H:%M:%S")
    exif[36881] = "+00:00"
    exif[40094] = "synthetic;photoforge".encode("utf-16-le") + b"\x00\x00"
    exif[34853] = {
        1: latitude_ref,
        2: latitude_dms,
        3: longitude_ref,
        4: longitude_dms,
    }
    return exif


def _create_image(path: Path, index: int) -> None:
    digest = hashlib.sha256(f"photoforge-synthetic-{index}".encode()).digest()
    background = tuple(48 + component % 160 for component in digest[:3])
    foreground = tuple(48 + component % 160 for component in digest[3:6])

    image = Image.new("RGB", (96, 64), background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 87, 55), outline=foreground, width=3)
    draw.line((8, 55, 48, 16, 87, 55), fill=foreground, width=3)
    draw.ellipse((38, 22, 58, 42), fill=foreground)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        path,
        format="JPEG",
        quality=90,
        optimize=False,
        progressive=False,
        exif=_synthetic_exif(index),
    )


def main() -> None:
    for index, name in enumerate(IMAGE_NAMES):
        _create_image(DEMO_ROOT / name, index)

    for source, destination in DUPLICATE_PATHS:
        destination_path = DEMO_ROOT / destination
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DEMO_ROOT / source, destination_path)

    (DEMO_ROOT / "corrupt.jpg").write_bytes(b"not a jpeg file")
    (DEMO_ROOT / "note.txt").write_text("note\n", encoding="utf-8")


if __name__ == "__main__":
    main()
